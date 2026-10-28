"""Path-confinement tests: unit coverage for ``utils.path_guard`` plus the
download / personalized-delivery / raster integration paths that used to open
caller-influenced files anywhere on the server.

Tests here are marked ``strict_path_roots``: the suite-wide fixture that injects
pytest's temp tree into ``allowed_roots()`` is disabled, so a ``tmp_path`` file
is genuinely outside the application's data roots, exactly like an attacker's
``C:/Windows/win.ini``.
"""

import base64
import os
import subprocess
import uuid
import zipfile

import pytest
from PIL import Image

from model.Application import Application
from model.Raster_Data import RasterData
from model.Shp_Data import Shp
from utils.path_guard import allowed_roots, is_within, resolve_within_roots

pytestmark = pytest.mark.strict_path_roots


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _norm(path):
    return os.path.normcase(os.path.realpath(str(path)))


@pytest.fixture
def inside_file(app):
    """Factory for files inside a configured storage root (cleaned up after)."""
    created = []

    def _make(folder_key, payload, suffix=".bin"):
        folder = app.config[folder_key]
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"pg_{uuid.uuid4().hex}{suffix}")
        with open(path, "wb") as fh:
            fh.write(payload)
        created.append(path)
        return path

    yield _make

    for path in created:
        try:
            os.remove(path)
        except OSError:
            pass


def _write_outside(tmp_path, name="server_secret.bin", payload=b"SERVER-SECRET"):
    path = tmp_path / name
    path.write_bytes(payload)
    return path


def _seed_shp(db, alias, url):
    record = Shp(
        name=f"{alias}_{uuid.uuid4().hex[:8]}",
        alias=alias,
        geomtype="LineString",
        introduction="path-guard fixture",
        shp_file_path=url or "/data/missing.shp",
        url=url,
    )
    db.session.add(record)
    db.session.commit()
    return record


def _submit(client, headers, data_id, data_type, alias, data_url="", data_name="client supplied"):
    return client.post(
        "/api/submit_application",
        json={
            "data_id": data_id,
            "data_name": data_name,
            "data_alias": alias,
            "data_url": data_url,
            "data_type": data_type,
            "applicant_name": "员工1",
            "applicant_user_number": "E001",
            "reason": "path guard test",
        },
        headers=headers,
    )


def _approve(client, app_id, auth_headers, adm2_headers):
    first = client.post("/api/adm1_pass", json={"id": app_id}, headers=auth_headers)
    assert first.status_code == 200, first.get_json()
    second = client.post("/api/adm2_pass", json={"id": app_id}, headers=adm2_headers)
    assert second.status_code == 200, second.get_json()


def _make_junction(link, target):
    """Create a directory junction/symlink; False when the OS refuses."""
    if os.name == "nt":
        proc = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0
    try:
        os.symlink(str(target), str(link), target_is_directory=True)
        return True
    except OSError:
        return False


def _remove_link(link):
    if not os.path.lexists(link):
        return
    if os.name == "nt":
        os.rmdir(link)
    else:
        os.unlink(link)


# --------------------------------------------------------------------------- #
# unit: allowed_roots / is_within / resolve_within_roots
# --------------------------------------------------------------------------- #


class TestAllowedRoots:
    def test_roots_are_config_driven_and_exclude_instance(self, app):
        with app.app_context():
            roots = {_norm(root) for root in allowed_roots()}
        for key in ("UPLOAD_FOLDER", "WATERMARK_FOLDER", "EXTRACTED_FOLDER", "DELIVERY_FOLDER"):
            assert _norm(app.config[key]) in roots, f"{key} must be an allowed root"
        assert _norm(os.path.join(app.root_path, "runtime")) in roots
        # instance/ holds signing keys (e.g. instance/keys/evm_sepolia.key)
        assert _norm(app.instance_path) not in roots


class TestResolveWithinRoots:
    def test_inside_root_returns_realpath(self, app, inside_file):
        path = inside_file("UPLOAD_FOLDER", b"inside")
        with app.app_context():
            assert resolve_within_roots(path) == os.path.realpath(path)
            assert resolve_within_roots(f"file://{path}") == os.path.realpath(path)

    def test_outside_existing_and_missing_are_both_none(self, app, tmp_path):
        outside = _write_outside(tmp_path)
        with app.app_context():
            # absolute escape (the "C:/Windows/win.ini" class): file exists, still refused
            assert resolve_within_roots(str(outside)) is None
            # non-existent path must be indistinguishable from the escape
            assert resolve_within_roots(str(tmp_path / "does_not_exist.bin")) is None
            # file:// URI and slash-normalised variant of the same escape
            assert resolve_within_roots(f"file://{outside}") is None
            assert resolve_within_roots(str(outside).replace("\\", "/")) is None

    def test_dotdot_traversal_escape_is_rejected(self, app):
        root = app.config["UPLOAD_FOLDER"]
        os.makedirs(root, exist_ok=True)
        outside = os.path.join(os.path.dirname(root), f"pg_escape_{uuid.uuid4().hex}.bin")
        with open(outside, "wb") as fh:
            fh.write(b"ESCAPED")
        try:
            traversal = os.path.join(root, "..", os.path.basename(outside))
            with app.app_context():
                assert os.path.exists(traversal)
                assert resolve_within_roots(traversal) is None
        finally:
            os.remove(outside)

    def test_leading_slash_legacy_mapping_stays_confined(self, app):
        # The legacy resolver mapped "/x" onto the app-root sibling; the guard
        # keeps the mapping but only accepts results inside a root.
        outside = "C:/Windows/win.ini" if os.name == "nt" else "/etc/passwd"
        assert os.path.exists(outside), "expected a stable OS file for the escape case"
        with app.app_context():
            assert resolve_within_roots(outside) is None

    def test_relative_app_root_candidate_cannot_escape(self, app):
        with app.app_context():
            assert resolve_within_roots("../../../Windows/win.ini") is None
            assert resolve_within_roots("/../../etc/passwd") is None

    @pytest.mark.skipif(os.name != "nt", reason="case-insensitive filesystem is Windows-only")
    def test_case_variant_inside_root_is_accepted(self, app, inside_file):
        path = inside_file("UPLOAD_FOLDER", b"case")
        with app.app_context():
            resolved = resolve_within_roots(path.upper())
        assert resolved is not None
        assert _norm(resolved) == _norm(path)

    def test_junction_or_symlink_escape_is_rejected(self, app, tmp_path):
        outside_dir = tmp_path / "outside_target"
        outside_dir.mkdir()
        (outside_dir / "loot.bin").write_bytes(b"LOOT")
        root = app.config["UPLOAD_FOLDER"]
        os.makedirs(root, exist_ok=True)
        link = os.path.join(root, f"pg_link_{uuid.uuid4().hex}")
        if not _make_junction(link, outside_dir):
            pytest.skip("OS refused to create a junction/symlink for the escape test")
        try:
            with app.app_context():
                assert resolve_within_roots(os.path.join(link, "loot.bin")) is None
        finally:
            _remove_link(link)

    def test_unc_path_is_not_within_a_local_root(self, app):
        with app.app_context():
            assert is_within(r"\\server\share\evil.txt", app.config["UPLOAD_FOLDER"]) is False
            assert resolve_within_roots(r"\\server\share\evil.txt") is None


class TestIsWithin:
    def test_sibling_prefix_is_not_within(self, tmp_path):
        dest = tmp_path / "dest"
        dest_evil = tmp_path / "dest_evil"
        assert is_within(dest_evil / "pwn.txt", dest) is False
        assert is_within(dest / "nested" / "ok.txt", dest) is True
        assert is_within(dest, dest) is True

    def test_traversal_target_is_not_within(self, tmp_path):
        assert is_within(tmp_path / "dest" / ".." / "dest_evil" / "x", tmp_path / "dest") is False


# --------------------------------------------------------------------------- #
# integration: application creation + download chain
# --------------------------------------------------------------------------- #


class TestApplicationCreationHardening:
    def test_client_data_url_ignored_and_normal_download_still_works(
        self, client, db, employee_headers, auth_headers, adm2_headers, inside_file, tmp_path
    ):
        payload = b"PATH-GUARD-NORMAL-PAYLOAD"
        safe = inside_file("UPLOAD_FOLDER", payload)
        alias = f"pg_alias_{uuid.uuid4().hex[:8]}"
        record = _seed_shp(db, alias, url=safe)
        evil = _write_outside(tmp_path)

        resp = _submit(client, employee_headers, record.id, "vector", f"  {alias}  ", data_url=str(evil))
        assert resp.status_code == 201, resp.get_json()
        assert resp.get_json()["status"] is True  # response contract unchanged

        row = Application.query.filter_by(data_alias=alias).first()
        assert row is not None
        # Server-authoritative values won, client-supplied ones were dropped.
        assert _norm(row.data_url) == _norm(safe)
        assert _norm(row.data_url) != _norm(evil)
        assert row.data_name == alias
        assert row.data_alias == alias  # trimmed, <=100

        _approve(client, row.id, auth_headers, adm2_headers)
        dl = client.post("/api/emp_download_zip", json={"application_id": row.id}, headers=employee_headers)
        assert dl.status_code == 200, dl.get_data(as_text=True)
        assert dl.data == payload

    def test_raster_submission_uses_server_record(self, client, db, employee_headers, inside_file, tmp_path):
        host = inside_file("UPLOAD_FOLDER", b"raster-bytes", suffix=".tif")
        alias = f"pg_raster_{uuid.uuid4().hex[:8]}"
        record = RasterData(
            name=f"{alias}_name", alias=alias, raster_file_path=host, url="", layer="", introduction="pg"
        )
        db.session.add(record)
        db.session.commit()

        resp = _submit(
            client,
            employee_headers,
            record.id,
            "raster",
            alias,
            data_url=str(_write_outside(tmp_path)),
            data_name="client raster name",
        )
        assert resp.status_code == 201, resp.get_json()
        row = Application.query.filter_by(data_alias=alias).first()
        assert row.data_type == "raster"
        assert row.data_name == alias
        assert row.data_url in (None, "")

    def test_unknown_data_id_is_rejected(self, client, db, employee_headers):
        resp = _submit(client, employee_headers, 999_000_001, "vector", "pg_missing", data_url="C:/Windows/win.ini")
        assert resp.status_code == 400
        assert resp.get_json()["msg"] == "数据不存在"
        assert Application.query.filter_by(data_alias="pg_missing").first() is None

    def test_invalid_data_type_is_rejected(self, client, db, employee_headers):
        resp = _submit(client, employee_headers, 999_000_002, "shapefile", "pg_bad_type")
        assert resp.status_code == 400


class TestDownloadPathConfinement:
    def test_legacy_application_with_outside_data_url_is_not_served(self, client, db, employee_headers, tmp_path):
        """Pre-hardening rows may still carry a client-supplied arbitrary path."""
        payload = b"SERVER-SECRET-BYTES"
        evil = _write_outside(tmp_path, payload=payload)
        item = Application(
            data_id=999_000_101,
            data_name="legacy",
            data_alias=f"pg_legacy_{uuid.uuid4().hex[:8]}",
            data_url=str(evil),
            data_type="vector",
            applicant_name="员工1",
            applicant_user_number="E001",
            reason="legacy row",
            adm1_statu=True,
            adm2_statu=True,
        )
        db.session.add(item)
        db.session.commit()

        resp = client.post("/api/emp_download_zip", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 404
        assert payload not in resp.data
        assert resp.get_json()["msg"] == "文件不存在"

    def test_legacy_outside_path_cannot_seed_personalized_delivery(self, client, db, employee_headers, tmp_path):
        from model.download_delivery import DownloadDelivery

        evil = _write_outside(tmp_path, payload=b"PERSONALIZED-LEAK")
        item = Application(
            data_id=999_000_102,
            data_name="legacy2",
            data_alias=f"pg_legacy2_{uuid.uuid4().hex[:8]}",
            data_url=str(evil),
            watermark_path=str(evil),
            data_type="vector",
            applicant_name="员工1",
            applicant_user_number="E001",
            reason="legacy row",
            adm1_statu=True,
            adm2_statu=True,
        )
        db.session.add(item)
        db.session.commit()

        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code != 200
        assert "token" not in resp.get_json()
        delivery = (
            DownloadDelivery.query.filter_by(application_id=item.id)
            .order_by(DownloadDelivery.delivery_id.desc())
            .first()
        )
        assert delivery is not None
        assert delivery.status == "FAILED"

    def test_authoritative_url_flows_through_personalized_delivery(
        self, client, db, employee_headers, auth_headers, adm2_headers, inside_file
    ):
        payload = b"DELIVERY-PASSTHROUGH-PAYLOAD"
        safe = inside_file("UPLOAD_FOLDER", payload)
        alias = f"pg_delivery_{uuid.uuid4().hex[:8]}"
        record = _seed_shp(db, alias, url=safe)

        resp = _submit(client, employee_headers, record.id, "vector", alias, data_url="C:/Windows/win.ini")
        assert resp.status_code == 201, resp.get_json()
        row = Application.query.filter_by(data_alias=alias).first()
        _approve(client, row.id, auth_headers, adm2_headers)

        token_resp = client.post(
            "/api/request_download_token", json={"application_id": row.id}, headers=employee_headers
        )
        assert token_resp.status_code == 200, token_resp.get_json()
        assert token_resp.get_json()["delivery"]["status"] == "READY"

        dl = client.get(f"/api/download/{token_resp.get_json()['token']}")
        assert dl.status_code == 200
        assert dl.data == payload


class TestDeliveryServiceConfinement:
    def test_resolve_base_file_rejects_outside_root(self, db, inside_file, tmp_path):
        from delivery.service import resolve_base_file

        outside = _write_outside(tmp_path)
        legacy = Application(
            data_id=999_000_201,
            data_name="delivery-legacy",
            data_alias=f"pg_delivery_legacy_{uuid.uuid4().hex[:8]}",
            data_url=str(outside),
            watermark_path=str(outside),
            data_type="vector",
            applicant_name="员工1",
            applicant_user_number="E001",
            reason="test",
        )
        db.session.add(legacy)
        db.session.commit()
        assert resolve_base_file(legacy) is None

        inside = inside_file("WATERMARK_FOLDER", b"INSIDE-BASE")
        legacy.watermark_path = inside
        legacy.data_url = None
        db.session.commit()
        assert resolve_base_file(legacy) == os.path.realpath(inside)


# --------------------------------------------------------------------------- #
# zip-slip (sibling-prefix bypass)
# --------------------------------------------------------------------------- #


def _upload_safe_extract(zip_ref, dest):
    from resource.upload_data_resource import _safe_extract_zip

    return _safe_extract_zip(zip_ref, dest)


def _watermark_safe_extract(zip_ref, dest):
    from resource.watermark_utils import safe_extract_zip

    return safe_extract_zip(zip_ref, dest)


ZIP_EXTRACTORS = pytest.mark.parametrize(
    "extractor", [_upload_safe_extract, _watermark_safe_extract], ids=["upload", "watermark"]
)


class TestZipSlip:
    @ZIP_EXTRACTORS
    def test_sibling_prefix_member_is_rejected(self, extractor, tmp_path):
        dest = tmp_path / "dest"
        dest.mkdir()
        evil_zip = tmp_path / "evil.zip"
        with zipfile.ZipFile(evil_zip, "w") as zf:
            zf.writestr("../dest_evil/pwn.txt", b"pwn")
        with zipfile.ZipFile(evil_zip) as zf, pytest.raises(ValueError, match="非法文件路径"):
            extractor(zf, str(dest))
        assert not (tmp_path / "dest_evil").exists()

    @ZIP_EXTRACTORS
    def test_absolute_member_is_rejected(self, extractor, tmp_path):
        dest = tmp_path / "dest_abs"
        dest.mkdir()
        evil_zip = tmp_path / "evil_abs.zip"
        with zipfile.ZipFile(evil_zip, "w") as zf:
            zf.writestr(str(tmp_path / "absolute_pwn.txt"), b"pwn")
        with zipfile.ZipFile(evil_zip) as zf, pytest.raises(ValueError, match="非法文件路径"):
            extractor(zf, str(dest))
        assert not (tmp_path / "absolute_pwn.txt").exists()

    @ZIP_EXTRACTORS
    def test_normal_member_still_extracts(self, extractor, tmp_path):
        dest = tmp_path / "dest_ok"
        dest.mkdir()
        good_zip = tmp_path / "good.zip"
        with zipfile.ZipFile(good_zip, "w") as zf:
            zf.writestr("nested/ok.txt", b"ok")
        with zipfile.ZipFile(good_zip) as zf:
            extractor(zf, str(dest))
        assert (dest / "nested" / "ok.txt").read_bytes() == b"ok"


# --------------------------------------------------------------------------- #
# raster: preview / embed / tiles
# --------------------------------------------------------------------------- #


def _seed_raster_application(db, raster_file_path, alias):
    raster = RasterData(
        name=f"{alias}_name",
        alias=alias,
        raster_file_path=str(raster_file_path),
        url="",
        layer="",
        introduction="path-guard fixture",
    )
    db.session.add(raster)
    db.session.commit()
    item = Application(
        data_id=raster.id,
        data_name=alias,
        data_alias=alias,
        data_type="raster",
        applicant_name="员工1",
        applicant_user_number="E001",
        reason="path guard raster",
        adm1_statu=True,
        adm2_statu=True,
    )
    db.session.add(item)
    db.session.commit()
    return raster, item


class TestRasterConfinement:
    def test_preview_outside_404_and_inside_200(self, client, app, employee_headers, tmp_path):
        outside_png = tmp_path / "outside_preview.png"
        Image.new("RGB", (8, 8), (1, 2, 3)).save(outside_png)
        bad = client.post("/api/raster/preview", json={"file_path": str(outside_png)}, headers=employee_headers)
        assert bad.status_code == 404

        inside_dir = os.path.join(app.root_path, "runtime", "path_guard_tests", uuid.uuid4().hex)
        os.makedirs(inside_dir, exist_ok=True)
        try:
            inside_png = os.path.join(inside_dir, "inside.png")
            Image.new("RGB", (8, 8), (200, 30, 30)).save(inside_png)
            good = client.post("/api/raster/preview", json={"file_path": inside_png}, headers=employee_headers)
            assert good.status_code == 200, good.get_data(as_text=True)
            assert base64.b64decode(good.get_json()["base64"])[:8] == b"\x89PNG\r\n\x1a\n"
        finally:
            import shutil

            shutil.rmtree(inside_dir, ignore_errors=True)

    def test_embed_and_tiles_reject_outside_source(self, client, db, adm2_headers, auth_headers, tmp_path):
        outside = _write_outside(tmp_path, "outside_host.tif", b"not-a-real-tiff")
        alias = f"pg_raster_out_{uuid.uuid4().hex[:8]}"
        raster, item = _seed_raster_application(db, outside, alias)

        embed = client.post("/api/admin/embed_dispatch", json={"application_id": item.id}, headers=adm2_headers)
        assert embed.status_code == 404
        assert "未找到可用的栅格原始文件路径" in embed.get_json()["message"]

        tile = client.get(f"/api/raster_tiles/{raster.id}/0/0/0.png", headers=auth_headers)
        assert tile.status_code == 404
