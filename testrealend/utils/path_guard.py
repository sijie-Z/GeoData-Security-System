"""Central filesystem-path confinement guard.

Every path that reaches the download, personalized-delivery or raster reading
layer can originate from client input (an application's ``data_url``) or from
database rows that were written when the same path was caller-controlled.
This module is the single place that decides whether such a path may be opened
at all: it must resolve inside one of the application's own data roots.

Security properties:
  * roots come from server-side configuration only (never from a request);
  * comparison uses ``realpath`` + ``normcase`` so symlinks, junctions, Windows
    short names and case variants cannot escape a root;
  * ``commonpath`` (not a string prefix) prevents the ``dest_evil`` sibling
    bypass of ``startswith(dest)``;
  * out-of-root and non-existent paths both answer ``None`` — callers cannot
    use the guard as an existence oracle.
"""

import os

from flask import current_app

# Config keys holding the storage folders the data layer writes to. Read from
# config (not hard-coded) so deployments that relocate them stay correct.
_ROOT_CONFIG_KEYS = (
    "UPLOAD_FOLDER",
    "WATERMARK_FOLDER",
    "EXTRACTED_FOLDER",
    "DELIVERY_FOLDER",
)


def _normalized(path):
    """Absolute, symlink-resolved, case-folded form used for comparisons."""
    return os.path.normcase(os.path.realpath(str(path)))


def allowed_roots():
    """Server-owned roots file reads may resolve into.

    Configured storage folders plus the backend's own ``runtime/`` scratch tree
    (download cache, CRMark artifacts). ``instance/`` — which holds signing keys
    — is deliberately *not* a root.
    """
    roots = []
    for key in _ROOT_CONFIG_KEYS:
        value = current_app.config.get(key)
        if value:
            roots.append(os.path.realpath(str(value)))
    roots.append(os.path.realpath(os.path.join(current_app.root_path, "runtime")))

    unique = []
    seen = set()
    for root in roots:
        marker = os.path.normcase(root)
        if marker not in seen:
            seen.add(marker)
            unique.append(root)
    return unique


def is_within(path, root):
    """True when *path* resolves to *root* itself or somewhere beneath it.

    Works for paths that do not exist yet (zip-slip targets): ``realpath``
    normalizes ``..`` lexically for the missing part. Any malformed input
    (embedded NUL, different Windows drive/UNC share) is simply "not within".
    """
    try:
        if path is None or root is None:
            return False
        if not str(path).strip() or not str(root).strip():
            return False
        candidate = _normalized(path)
        normalized_root = _normalized(root)
        if not candidate or not normalized_root:
            return False
        return os.path.commonpath([candidate, normalized_root]) == normalized_root
    except (TypeError, ValueError, OSError):
        return False


def _candidate_paths(path_value):
    """Yield the legacy resolution candidates for *path_value*, in order.

    Mirrors the pre-guard helpers:
      1. the value as given (``file://`` stripped, backslashes normalized);
      2. for a leading ``/``, an app-root-sibling interpretation (legacy
         ``/data/x`` -> ``<project>/data/x``);
      3. an app-root-relative interpretation (``data/x`` -> ``<app>/data/x``).
    """
    candidate = str(path_value).replace("\\", "/").strip()
    if candidate.startswith("file://"):
        candidate = candidate[7:]
    yield candidate
    if candidate.startswith("/"):
        yield os.path.join(os.path.dirname(current_app.root_path), candidate.lstrip("/"))
    yield os.path.join(current_app.root_path, candidate.lstrip("/"))


def resolve_within_roots(path_value, roots=None):
    """Resolve *path_value* to a real path inside *roots* (default: allowed roots).

    Returns ``None`` for anything that is not an existing file/directory inside
    a root — including absolute escapes, ``file://`` URIs, ``..`` traversal,
    UNC/device paths and paths that simply do not exist. The two rejection cases
    are intentionally indistinguishable.
    """
    if not path_value:
        return None
    if roots is None:
        roots = allowed_roots()
    for candidate in _candidate_paths(path_value):
        if not candidate:
            continue
        if not any(is_within(candidate, root) for root in roots):
            continue
        if os.path.exists(candidate):
            return os.path.realpath(candidate)
    return None
