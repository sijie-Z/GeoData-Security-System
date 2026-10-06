"""Artifact hashing for deliveries (canonical-CBOR manifests + domain separation).

Both roots commit to file bytes via sha256 under the GDS-ARTIFACT-V1 domain tag
(``evidence.constants.DOMAIN_ARTIFACT``):

  shp_component_root: sha256(DOMAIN_ARTIFACT || canonical_cbor([{"name","sha256"}, ...]))
  file_root:          sha256(DOMAIN_ARTIFACT || sha256(file bytes))
"""

import base64
import hashlib
import os
import zipfile

from crypto import canonical
from evidence.constants import DOMAIN_ARTIFACT

SHP_COMPONENT_EXTS = (".shp", ".shx", ".dbf", ".prj", ".cpg")

# Known-good vector from the multiformats/IPFS docs: CIDv1 raw sha2-256 of the
# empty byte string, base32-lower multibase. Used by tests to pin the encoder.
CIDV1_RAW_EMPTY = "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku"


def cidv1_raw(data: bytes) -> str:
    """CIDv1 (raw codec, sha2-256) for ``data``, as multibase base32-lower.

    Layout (multiformats): multibase prefix ``b`` (base32-lower, RFC 4648, no
    padding) + version ``0x01`` + codec ``raw 0x55`` + multihash header
    ``0x12 0x20`` (sha2-256, 32-byte digest) + sha256(data). Pure stdlib
    (hashlib + base64), no third-party dependency.

    This is a content-addressing *integrity commitment*: recomputing the CID
    from the bytes validates them, but the identifier itself promises nothing
    about retrievability — nothing here is published to any IPFS network.
    """
    digest = hashlib.sha256(data).digest()
    return "b" + base64.b32encode(b"\x01\x55\x12\x20" + digest).decode("ascii").lower().rstrip("=")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_root(path) -> str:
    """Root over a single file: sha256(DOMAIN_ARTIFACT || sha256(contents))."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return _sha256_hex(DOMAIN_ARTIFACT + digest.digest())


def _components_from_zip(zip_path):
    """(name, sha256) pairs for shp components inside a zip, named by basename."""
    pairs = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = os.path.basename(info.filename.replace("\\", "/"))
            ext = os.path.splitext(name)[1].lower()
            if ext in SHP_COMPONENT_EXTS:
                pairs.append((name, _sha256_hex(zf.read(info))))
    return pairs


def _components_from_paths(paths):
    """(name, sha256) pairs for explicit component file paths."""
    pairs = []
    for path in paths:
        name = os.path.basename(str(path))
        if os.path.splitext(name)[1].lower() not in SHP_COMPONENT_EXTS:
            continue
        with open(path, "rb") as fh:
            pairs.append((name, _sha256_hex(fh.read())))
    return pairs


def _components_from_shp(shp_path):
    """(name, sha256) pairs for every existing companion of ``shp_path``."""
    stem = os.path.splitext(str(shp_path))[0]
    pairs = []
    for ext in SHP_COMPONENT_EXTS:
        companion = f"{stem}{ext}"
        if os.path.isfile(companion):
            with open(companion, "rb") as fh:
                pairs.append((os.path.basename(companion), _sha256_hex(fh.read())))
    return pairs


def shp_component_root(paths_or_zip) -> str:
    """Root over the {.shp,.shx,.dbf,.prj,.cpg} components of a shapefile.

    Accepts a .zip path (components read from the archive), a directory (first
    .shp found), a single .shp path (companions taken from its directory), or an
    explicit list/tuple of component paths. Components are ordered by name
    bytes; missing files are simply absent from the manifest.
    """
    if isinstance(paths_or_zip, (list, tuple)):
        pairs = _components_from_paths(paths_or_zip)
    else:
        path = str(paths_or_zip)
        if os.path.isdir(path):
            shp_path = None
            for name in sorted(os.listdir(path)):
                if name.lower().endswith(".shp"):
                    shp_path = os.path.join(path, name)
                    break
            if shp_path is None:
                raise ValueError(f"目录中没有 .shp 文件: {path}")
            pairs = _components_from_shp(shp_path)
        elif path.lower().endswith(".zip"):
            pairs = _components_from_zip(path)
        else:
            pairs = _components_from_shp(path)

    if not pairs:
        raise ValueError(f"未找到 shapefile 组件: {paths_or_zip}")

    manifest = [{"name": name, "sha256": digest} for name, digest in sorted(pairs, key=lambda p: p[0].encode("utf-8"))]
    return _sha256_hex(DOMAIN_ARTIFACT + canonical.dumps(manifest))
