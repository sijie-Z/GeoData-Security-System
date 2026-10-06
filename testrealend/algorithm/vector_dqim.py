"""D-QIM v1: translation-invariant vector watermark (edge-difference QIM).

The legacy scheme (``algorithm/embed.py``) hides the QR payload in the absolute
x coordinate: every vertex is moved inside its own 1e-7-degree grid cell and the
seed hashes that cell's *value*. A whole-map translation changes those values
(anchor_value -> anchor_value + K*R), so seeds and votes scatter and extraction
fails as soon as the map is shifted. D-QIM keeps the same architecture (QR pixel
grid payload, n bits per chunk, seed-selected chunks, per-chunk majority voting)
but moves the carrier to the *difference domain*:

  * the carrier is the x-difference of an edge, ``dx = x2 - x1``. Translating the
    map adds the same constant to x1 and x2, whose float roundings cancel
    exactly within one binade, so dx is bit-stable and the R-grid cell of dx
    (``dx_base``) is an embedding-invariant, translation-invariant anchor;
  * only *eligible* edges are embedded: ``abs(dx_base) >= 2R``, i.e. the QIM
    moves dx by less than R, at most half of the original edge length;
  * the chunk seed hashes ``(dx_base of this edge, R-grid cell of the NEXT
    edge's dy)`` — no absolute coordinate enters, hence the name
    (difference-domain QIM). dy is never touched by embedding and is
    float-stable under translation, including the closure edge of a ring;
  * the last edge of every coordinate group stays uncontrolled (its end vertex
    is kept for the ring-closure patch), mirroring the legacy scheme which never
    embeds the last vertex of a group.

Structural isomorphism: function pairs mirror ``algorithm/embed.py`` /
``algorithm/extract.py`` one-to-one, with ``_embed_`` / ``_extract_`` prefixes
instead of module separation (``_embed_coor_group_process`` <->
``embed.coor_group_process`` etc.). Voting reconstruction
(``calculate_watermark_and_nc``) is carrier-agnostic and shared verbatim.

Scheme marker: new artifacts carry ``vr_data["scheme"] == "dqim1"``; legacy
artifacts have no such key. Extraction dispatch (delivery verification,
forensics candidate scan) selects ``extract_dqim`` for "dqim1" and the legacy
``algorithm.extract.extract`` otherwise. The legacy embed/extract modules are
not modified — not even semantically.

Not in scope (documented limits): scale invariance. The legacy scheme rescales
by ``vr`` before reading; D-QIM deliberately does not, because an absolute
mean-based rescale would break translation invariance. Rotation is unsupported
in both schemes.
"""

import hashlib
import logging
import math
import os
import random
import zipfile
from collections import Counter
from decimal import Decimal

import numpy as np
from PIL import Image

from algorithm.embed import CapacityError, _floor_to_grid
from algorithm.get_coor import get_coor_array, get_coor_nested
from algorithm.quality_metrics import capacity_report
from algorithm.to_geodataframe import to_geodataframe

SCHEME = "dqim1"

# An edge is eligible when abs(dx_base) >= ELIGIBLE_MIN_STEPS * R. Expressed on
# the R-grid cell (not on raw dx) so embedding and extraction apply the exact
# same predicate: QIM keeps dx inside its original cell.
ELIGIBLE_MIN_STEPS = 2


def _compute_seed(dx_base, dy_next, R):
    """Compute the deterministic chunk seed for one edge (D-QIM variant).

    Mirrors ``algorithm.embed._compute_seed`` (canonicalized anchors, md5[:8]),
    with the same N2 discipline: only embedding-invariant values may enter the
    hash, and — since extraction must also survive tiny independent coordinate
    noise (E2) — both slots are R-grid cells, never raw floats:

      * the x-slot is ``dx_base``, the R-grid cell of the edge's x-difference.
        QIM rewrites dx strictly inside that cell, so the anchor recomputed from
        the watermarked coordinates is identical — and translation-invariant,
        because dx itself is.
      * the y-slot is the R-grid cell of the NEXT edge's raw dy (taskbook §0.3).
        y coordinates are never modified by embedding, and a map translation
        adds the same double constant to both endpoints whose float roundings
        cancel exactly within a binade. The taskbook sketch hashed the raw dy
        string (``float(dy):.15f``); E2 showed that quantum (1e-15) collapses
        under +/-1e-9 jitter, because independent noise changes dy itself while
        translation does not — anchoring dy to the same R grid as dx (flip
        probability ~2e-9/R per edge) keeps the invariant-only discipline.

    No absolute coordinate enters the hash — that is what makes the scheme
    survive translations that break the legacy one.
    """
    raw = f"{format(dx_base.normalize(), 'f')},{format(_floor_to_grid(dy_next, R).normalize(), 'f')}"
    return int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)


def _is_eligible(dx_base, R):
    """True when an edge may carry a QIM symbol: the cell must be at least 2R away from 0.

    At most R of movement is applied to dx, so an eligible edge keeps its sign
    and at least half of its length. The predicate is evaluated on ``dx_base``
    (the R-grid cell), which embedding does not change, so both ends agree even
    for edges near the threshold.
    """
    return abs(dx_base) >= ELIGIBLE_MIN_STEPS * R


def watermark_embed(dx, dx_base, w, n, R):
    """QIM-embed the n-bit symbol ``w`` into the x-difference ``dx``.

    Same formula as the legacy per-vertex embed, with ``dx`` in the role of the
    coordinate and ``dx_base`` in the role of its grid anchor; the result stays
    inside ``[dx_base, dx_base + R)`` so the anchor is preserved.
    """
    return dx_base + w * (R / 2**n) + (dx - dx_base) / 2**n


def watermark_extract(dx, dx_base, R, n):
    """Read the n-bit symbol back from the x-difference and undo the QIM.

    Mirrors ``algorithm.extract.watermark_extract`` (symmetric
    ``// (R / 2**n)`` read plus inverse QIM for the reconstructed shapefile).
    """
    w = (dx - dx_base) // (R / 2**n)
    original_dx = dx_base + 2**n * (dx - dx_base) - w * R
    return original_dx, int(w)


def _group_to_decimals(coor_group):
    """Convert one (2, m) coordinate group into per-axis Decimal lists."""
    xs = [Decimal(str(float(v))) for v in coor_group[0, :]]
    ys = [Decimal(str(float(v))) for v in coor_group[1, :]]
    return xs, ys


def _group_from_decimals(xs, ys):
    """Rebuild a (2, m) object coordinate group from Decimal lists."""
    coor_group = np.empty((2, len(xs)), dtype=object)
    for i, value in enumerate(xs):
        coor_group[0, i] = value
    for i, value in enumerate(ys):
        coor_group[1, i] = value
    return coor_group


# --------------------------------------------------------------------------- #
# embed side (mirrors algorithm/embed.py)                                      #
# --------------------------------------------------------------------------- #


def _embed_coor_group_process(coor_group, argument):
    """Embed the per-edge QIM into one coordinate group (a ring or part).

    Mirrors ``algorithm.embed.coor_group_process``. Edges ``i`` in
    ``range(m - 2)`` are controlled; the closing edge of every group is left
    alone and the final vertex keeps its original value (the ring closure patch
    in ``_embed_traversal`` then re-closes polygons exactly as the legacy scheme
    does). Modified x coordinates accumulate sequentially
    (``x'[i+1] = x'[i] + dx'[i]``), the standard edge-watermarking drift; y is
    never touched.
    """
    n, R, W = argument["n"], argument["R"], argument["W"]
    xs, ys = _group_to_decimals(coor_group)
    m = len(xs)

    processed_x = list(xs)
    for i in range(m - 2):
        dx = xs[i + 1] - xs[i]
        dx_base = _floor_to_grid(dx, R)
        if _is_eligible(dx_base, R):
            dy_next = ys[i + 2] - ys[i + 1]
            seed = _compute_seed(dx_base, dy_next, R)
            random.seed(seed)
            index = random.randint(0, len(W) - 1)
            w = int("".join(map(str, W[index])), 2)
            dx = watermark_embed(dx, dx_base, w, n, R)
        processed_x[i + 1] = processed_x[i] + dx
    return _group_from_decimals(processed_x, ys)


def _embed_traversal_nested(coor_nested, feature_type, argument):
    """Embed side: multi-part geometries, per part (mirrors ``embed.traversal_nested_coor_group``)."""
    processed_x_nested = []
    processed_y_nested = []
    for feature_index in range(coor_nested.shape[1]):
        coor_group = np.vstack(coor_nested[:, feature_index])
        processed_coor_group = _embed_coor_group_process(coor_group, argument)
        # MultiPolygon parts must stay explicitly closed
        if (
            feature_type == "MultiPolygon"
            and np.size(processed_coor_group) not in [0, 2]
            and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])
        ):
            processed_coor_group[:, -1] = processed_coor_group[:, 0]
        processed_x_nested.append(processed_coor_group[0, :])
        processed_y_nested.append(processed_coor_group[1, :])
    return np.array([processed_x_nested, processed_y_nested], dtype=object)


def _embed_traversal(coor_nested, shp_type, processed_shpfile, argument):
    """Embed side: walk every feature (mirrors ``embed.traversal_coor_group``)."""
    for feature_index in range(coor_nested.shape[1]):
        x_col = coor_nested[0, feature_index]
        y_col = coor_nested[1, feature_index]
        feature_type = shp_type[feature_index]
        if isinstance(x_col, list):
            n_parts = len(x_col)
            coor_group = np.empty((2, n_parts), dtype=object)
            for j in range(n_parts):
                coor_group[0, j] = x_col[j]
                coor_group[1, j] = y_col[j]
        else:
            coor_group = np.vstack([x_col, y_col])

        if isinstance(coor_group[0, 0], np.ndarray):
            processed_coor_group = _embed_traversal_nested(coor_group, feature_type, argument)
        else:
            processed_coor_group = _embed_coor_group_process(coor_group, argument)
            # Polygons must stay explicitly closed (same rule as the legacy embed)
            if (
                feature_type == "Polygon"
                and np.size(processed_coor_group) not in [0, 2]
                and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])
            ):
                processed_coor_group[:, -1] = processed_coor_group[:, 0]
        processed_shpfile = to_geodataframe(
            processed_shpfile, feature_index, processed_coor_group, shp_type[feature_index]
        )
    return processed_shpfile


def _iter_coor_groups(coor_nested, shp_type):
    """Yield one ``(feature_type, coor_group)`` pair per embedded part.

    Same unpacking rules as ``_embed_traversal``: multi-part features (list
    columns) yield each part as its own (2, m) numeric group.
    """
    for feature_index in range(coor_nested.shape[1]):
        x_col = coor_nested[0, feature_index]
        y_col = coor_nested[1, feature_index]
        feature_type = shp_type[feature_index]
        if isinstance(x_col, list):
            n_parts = len(x_col)
            for j in range(n_parts):
                yield feature_type, np.vstack([x_col[j], y_col[j]])
        else:
            yield feature_type, np.vstack([x_col, y_col])


def _count_eligible_edges(coor_nested, shp_type, R):
    """Count the edges the embedding pass will actually QIM (same predicate).

    Returns ``(eligible_edges, total_vertices)`` for the capacity report.
    """
    eligible_edges = 0
    total_vertices = 0
    for _feature_type, coor_group in _iter_coor_groups(coor_nested, shp_type):
        xs, _ys = _group_to_decimals(coor_group)
        m = len(xs)
        total_vertices += m
        for i in range(m - 2):
            dx_base = _floor_to_grid(xs[i + 1] - xs[i], R)
            if _is_eligible(dx_base, R):
                eligible_edges += 1
    return eligible_edges, total_vertices


def embed_dqim(shp_path, qr_image_path, n=4, R=Decimal("1e-7"), output_dir=None):
    """Embed the QR watermark via the difference-domain QIM (scheme "dqim1").

    Structure mirrors ``algorithm.embed.embed`` (read shp -> nested coordinates
    -> QR pixel array -> per-edge pass -> zipped products). Capacity is judged
    on eligible edges instead of raw vertex count; the returned
    ``capacity_report`` keeps the legacy field names so the delivery lambda
    gate works unchanged, plus ``eligible_edges`` for diagnostics.
    """
    import geopandas as gpd

    if output_dir is None:
        from flask import current_app

        output_dir = current_app.config["WATERMARK_FOLDER"]
    output_filename = f"watermarked_{os.path.basename(shp_path)}"

    # -------------------------数据读取--------------------------------
    original_shpfile = gpd.read_file(shp_path)
    coor_nested, feature_type = get_coor_nested(original_shpfile)
    watermark = np.array(Image.open(qr_image_path)).astype(int)
    side_length = int(watermark.shape[0])

    # -------------------------容量检查（按合格边）--------------------------------
    watermark_proc = watermark.copy()
    replace_matrix_check = np.full((8, 8), -1)
    watermark_proc[:8, :8] = watermark_proc[:8, -8:] = watermark_proc[-8:, :8] = replace_matrix_check
    watermark_proc = watermark_proc.flatten()
    watermark_proc = list(filter(lambda x: x != -1, watermark_proc))
    n_bits_needed = len(watermark_proc)
    eligible_edges, total_vertices = _count_eligible_edges(coor_nested, feature_type, R)
    cap_report = capacity_report(eligible_edges, n_bits_needed, n)
    cap_report["total_vertices"] = total_vertices
    cap_report["eligible_edges"] = eligible_edges
    if not cap_report["sufficient"]:
        raise CapacityError(
            f"数据容量不足：水印需要 {cap_report['needed_chunks']} 个嵌入区块，"
            f"当前数据最多可提供 {cap_report['available_chunks']} 个"
            f"（共 {total_vertices} 个顶点，其中 {eligible_edges} 条合格边）"
        )
    logging.info("D-QIM capacity report: %s", cap_report)

    # -------------------------数据预处理--------------------------------
    replace_matrix = np.full((8, 8), -1)
    watermark[:8, :8] = watermark[:8, -8:] = watermark[-8:, :8] = replace_matrix
    watermark = watermark.flatten()
    watermark = list(filter(lambda x: x != -1, watermark))
    watermark += [0] * ((n - len(watermark) % n) % n)
    W = np.array_split(watermark, len(watermark) // n)
    argument = {"n": n, "R": R, "W": W}

    # -------------------------水印嵌入--------------------------------
    watermarked_shpfile = original_shpfile.copy()
    watermarked_shpfile = _embed_traversal(coor_nested, feature_type, watermarked_shpfile, argument)

    coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
    coor_array = get_coor_array(coor_nested, feature_type)
    vr = np.mean(coor_array, axis=1)
    vr = [float(format(coor, ".15f")) for coor in vr]
    logging.info("vr: %s", vr)

    # -------------------------数据输出--------------------------------
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    shapefile_path = os.path.join(output_dir, output_filename)
    # Fix pandas 3.x StringDtype / ArrowDtype incompatibility with geopandas to_file
    for col in watermarked_shpfile.columns:
        if col != watermarked_shpfile.geometry.name:
            col_dtype = watermarked_shpfile[col].dtype
            if hasattr(col_dtype, "storage") or "StringDtype" in str(col_dtype) or "ArrowDtype" in str(col_dtype):
                watermarked_shpfile[col] = watermarked_shpfile[col].astype(object)
    watermarked_shpfile.to_file(shapefile_path)

    shapefile_extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg"]
    zip_filename = f"{output_filename.replace('.shp', '.zip')}"
    zip_file_path = os.path.join(output_dir, zip_filename)

    with zipfile.ZipFile(zip_file_path, "w") as zipf:
        for ext in shapefile_extensions:
            filepath = shapefile_path.replace(".shp", ext)
            if os.path.exists(filepath):
                zipf.write(filepath, os.path.basename(filepath))

    logging.info("ZIP文件创建完成，已保存为 %s", zip_file_path)

    # -------------------------删除原始文件--------------------------------
    try:
        for ext in shapefile_extensions:
            filepath = shapefile_path.replace(".shp", ext)
            if os.path.exists(filepath):
                os.remove(filepath)
        logging.info("原始文件已删除。")
    except Exception as e:
        logging.error("删除文件时出错: %s", e)

    return {
        "zip_path": zip_file_path,
        "vr": vr,
        "capacity_report": cap_report,
        "side_length": side_length,
        "scheme": SCHEME,
    }


# --------------------------------------------------------------------------- #
# extract side (mirrors algorithm/extract.py)                                  #
# --------------------------------------------------------------------------- #


def _extract_coor_group_process(coor_group, W, argument):
    """Read the QIM votes from one coordinate group.

    Mirrors ``algorithm.extract.coor_group_process`` minus the ``vr``-based
    rescale (see module docstring). Votes are appended to the seed-selected
    chunk and the inverse QIM reconstructs an approximate original shapefile.
    """
    n, R = argument["n"], argument["R"]
    xs, ys = _group_to_decimals(coor_group)
    m = len(xs)

    original_x = list(xs)
    for i in range(m - 2):
        dx = xs[i + 1] - xs[i]
        dx_base = _floor_to_grid(dx, R)
        if _is_eligible(dx_base, R):
            dy_next = ys[i + 2] - ys[i + 1]
            seed = _compute_seed(dx_base, dy_next, R)
            random.seed(seed)
            index = random.randint(0, len(W) - 1)
            original_dx, w = watermark_extract(dx, dx_base, R, n)
            W[index].append(w)
        else:
            original_dx = dx
        original_x[i + 1] = original_x[i] + original_dx
    return _group_from_decimals(original_x, ys), W


def _extract_traversal_nested(coor_nested, feature_type, W, argument):
    """Extract side: multi-part geometries (mirrors ``extract.traversal_nested_coor_group``)."""
    processed_x_nested = []
    processed_y_nested = []
    for feature_index in range(coor_nested.shape[1]):
        coor_group = np.vstack(coor_nested[:, feature_index])
        processed_coor_group, W = _extract_coor_group_process(coor_group, W, argument)
        if (
            feature_type == "MultiPolygon"
            and np.size(processed_coor_group) not in [0, 2]
            and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])
        ):
            processed_coor_group[:, -1] = processed_coor_group[:, 0]
        processed_x_nested.append(processed_coor_group[0, :])
        processed_y_nested.append(processed_coor_group[1, :])
    return np.array([processed_x_nested, processed_y_nested], dtype=object), W


def _extract_traversal(coor_nested, shp_type, processed_shpfile, l, argument):
    """Extract side: walk every feature (mirrors ``extract.traversal_coor_group``)."""
    W = [[] for _ in range(l)]

    for feature_index in range(coor_nested.shape[1]):
        x_col = coor_nested[0, feature_index]
        y_col = coor_nested[1, feature_index]
        feature_type = shp_type[feature_index]
        if isinstance(x_col, list):
            n_parts = len(x_col)
            coor_group = np.empty((2, n_parts), dtype=object)
            for j in range(n_parts):
                coor_group[0, j] = x_col[j]
                coor_group[1, j] = y_col[j]
        else:
            coor_group = np.vstack([x_col, y_col])

        if isinstance(coor_group[0, 0], np.ndarray):
            processed_coor_group, W = _extract_traversal_nested(coor_group, feature_type, W, argument)
        else:
            processed_coor_group, W = _extract_coor_group_process(coor_group, W, argument)
            if (
                feature_type == "Polygon"
                and np.size(processed_coor_group) not in [0, 2]
                and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])
            ):
                processed_coor_group[:, -1] = processed_coor_group[:, 0]
        processed_shpfile = to_geodataframe(
            processed_shpfile, feature_index, processed_coor_group, shp_type[feature_index]
        )
    return processed_shpfile, W


def calculate_watermark_and_nc(watermarked_shpfile, l, argument):
    """Rebuild the QR bitmap from the per-chunk majority votes (carrier-agnostic).

    Byte-for-byte the legacy reconstruction (``algorithm.extract.calculate_watermark_and_nc``):
    majority vote per chunk, empty chunks padded with zeros, three 7x7 finder
    patterns placed back, payload bits arranged around the excluded 8x8 corner
    blocks.
    """
    watermarked_coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
    n, R, side_length = argument["n"], argument["R"], argument["side_length"]

    original_shpfile = watermarked_shpfile.copy()
    original_shpfile, W = _extract_traversal(watermarked_coor_nested, feature_type, original_shpfile, l, argument)

    empty_array_flag = False
    for i in range(len(W)):
        counter = Counter(W[i])
        if counter:
            w = counter.most_common(1)[0][0]
            w = 0 if w < 0 else w
            W[i] = [int(digit) for digit in format(w, f"0{n}b")]
        else:
            empty_array_flag = True
            W[i] = [0] * n
    if empty_array_flag:
        logging.warning("存在空数组，补零")
    W = [item for w in W for item in w]

    W = W[: side_length**2 - 192]
    watermark = np.full((side_length, side_length), 1)
    detection_pattern = np.full((7, 7), 0)
    detection_pattern[1:6, 1:6] = np.full((5, 5), 1)
    detection_pattern[2:5, 2:5] = np.full((3, 3), 0)
    watermark[:7, :7] = watermark[:7, -7:] = watermark[-7:, :7] = detection_pattern
    watermark[0:8, 8:-8] = np.reshape(W[0 : (side_length - 16) * 8], (8, side_length - 16))
    watermark[8:-8, :] = np.reshape(W[(side_length - 16) * 8 : -(side_length - 8) * 8], (side_length - 16, side_length))
    watermark[-8:, 8:] = np.reshape(W[-(side_length - 8) * 8 :], (8, side_length - 8))

    return original_shpfile, watermark


def extract_dqim(watermarked_shpfile_path, vr, n=4, R=Decimal("1e-7"), side_length=130, output_dir=None):
    """Extract the D-QIM watermark (scheme "dqim1"); returns ``(shp_out, watermark_img_path)``.

    ``vr`` is accepted for signature compatibility with the legacy extract but
    intentionally unused for decoding: D-QIM is translation-invariant and must
    not apply an absolute mean-based rescale (that would reintroduce the
    absolute-coordinate dependency the scheme removes).
    """
    import geopandas as gpd

    l = math.ceil((side_length**2 - 192) / n)

    watermarked_shpfile = gpd.read_file(watermarked_shpfile_path)

    logging.debug("D-QIM extract: vr=%s (unused for decoding)", vr)
    argument = {
        "n": n,
        "R": R,
        "side_length": side_length,
    }
    original_shpfile, watermark = calculate_watermark_and_nc(watermarked_shpfile, l, argument)

    if output_dir is None:
        from flask import current_app

        output_dir = current_app.config["EXTRACTED_FOLDER"]
    shp_output_folder = os.path.join(output_dir, "shp")
    watermark_output_folder = os.path.join(output_dir, "watermark")

    os.makedirs(shp_output_folder, exist_ok=True)
    os.makedirs(watermark_output_folder, exist_ok=True)

    # Fix pandas 3.x StringDtype / ArrowDtype incompatibility with geopandas to_file
    for col in original_shpfile.columns:
        if col != original_shpfile.geometry.name:
            col_dtype = original_shpfile[col].dtype
            if hasattr(col_dtype, "storage") or "StringDtype" in str(col_dtype) or "ArrowDtype" in str(col_dtype):
                original_shpfile[col] = original_shpfile[col].astype(object)

    output_shapefile_path = os.path.join(shp_output_folder, os.path.basename(watermarked_shpfile_path))
    original_shpfile.to_file(output_shapefile_path)
    logging.info("Shapefile创建完成，已保存为 %s", output_shapefile_path)

    output_watermark_path = os.path.join(
        watermark_output_folder, f"{os.path.splitext(os.path.basename(watermarked_shpfile_path))[0]}.png"
    )
    Image.fromarray(watermark.astype(bool)).save(output_watermark_path)
    logging.info("水印创建完成，已保存为 %s", output_watermark_path)

    return output_shapefile_path, output_watermark_path
