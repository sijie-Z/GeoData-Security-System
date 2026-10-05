"""Tests for data upload endpoints."""

import os
import zipfile

# A custom (non-EPSG) WKT with > 100 characters — mirrors the real-world
# "szbj54" projection of the demo datasets, which previously overflowed the
# varchar(100) coordinate_system column via CRS.to_string() full WKT.
CUSTOM_PRJ_WKT = (
    'PROJCS["Custom_Test_CRS",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
    'SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],'
    'PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],'
    'PARAMETER["Central_Meridian",117.0],PARAMETER["Scale_Factor",1.0],'
    'PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
)


class TestUpload:
    def test_shp_upload_requires_auth(self, client):
        resp = client.post("/api/upload_shp_data")
        assert resp.status_code in (401, 422)

    def test_raster_upload_requires_auth(self, client):
        resp = client.post("/api/upload_raster_data")
        assert resp.status_code in (401, 422)

    def test_shp_upload_no_file(self, client, auth_headers):
        resp = client.post("/api/upload_shp_data", headers=auth_headers)
        assert resp.status_code in (400, 422)

    def test_raster_upload_no_file(self, client, auth_headers):
        resp = client.post("/api/upload_raster_data", headers=auth_headers)
        assert resp.status_code in (400, 422)


def _write_shp_zip(tmp_path, name, crs, prj_wkt=None, n_shp=1):
    """Build a zip containing n_shp shapefiles (plus .shx/.dbf/.prj/.cpg).

    When prj_wkt is given it replaces the generated .prj content.
    """
    import geopandas as gpd
    from shapely.geometry import LineString

    d = tmp_path / f"{name}_dir"
    d.mkdir(exist_ok=True)
    for i in range(n_shp):
        shp_path = d / f"{name}{i}.shp"
        gdf = gpd.GeoDataFrame(
            {"id": [1]},
            geometry=[LineString([(0.0, 0.0), (1.0, 1.0)])],
            crs=crs,
        )
        gdf.to_file(shp_path)
        if prj_wkt:
            # Keep the file size consistent with the original .prj, then swap content
            (d / f"{name}{i}.prj").write_text(prj_wkt, encoding="utf-8")
    zip_path = tmp_path / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in sorted(d.iterdir()):
            zf.write(f, f.name)
    return zip_path


def _post_shp_zip(client, auth_headers, zip_path, alias):
    with open(zip_path, "rb") as fh:
        return client.post(
            "/api/upload_shp_data",
            headers=auth_headers,
            data={"data_alias": alias, "file": (fh, os.path.basename(zip_path))},
            content_type="multipart/form-data",
        )


class TestShpUploadWithPrj:
    """Regression (N1): zips containing a readable .prj used to 500 because the
    full WKT (from CRS.to_string()) overflowed the coordinate_system varchar(100)
    column — reproduced by the E2E upload attempts with .prj included."""

    def test_upload_with_epsg_prj_succeeds(self, client, auth_headers, tmp_path):
        zip_path = _write_shp_zip(tmp_path, "prj_epsg", crs="EPSG:4326")
        resp = _post_shp_zip(client, auth_headers, zip_path, "prj-epsg-test")
        assert resp.status_code == 201, resp.get_data(as_text=True)
        data = resp.get_json()["data"]
        cs = data["coordinate_system"]
        assert cs, "coordinate_system must not be empty when a .prj is present"
        assert len(cs) <= 100
        assert cs.startswith("EPSG:")

    def test_upload_with_custom_wkt_prj_truncates_to_column_width(self, client, auth_headers, tmp_path):
        assert len(CUSTOM_PRJ_WKT) > 100
        zip_path = _write_shp_zip(tmp_path, "prj_custom", crs="EPSG:4326", prj_wkt=CUSTOM_PRJ_WKT)
        resp = _post_shp_zip(client, auth_headers, zip_path, "prj-custom-test")
        assert resp.status_code == 201, resp.get_data(as_text=True)
        cs = resp.get_json()["data"]["coordinate_system"]
        assert cs, "coordinate_system must not be empty when a .prj is present"
        assert len(cs) <= 100

    def test_failed_upload_cleans_extracted_orphans(self, app, client, auth_headers, tmp_path):
        """A rejected zip (two .shp files) must not leave the saved zip or the
        extracted directory behind."""
        zip_path = _write_shp_zip(tmp_path, "two_shp", crs="EPSG:4326", n_shp=2)
        resp = _post_shp_zip(client, auth_headers, zip_path, "two-shp-test")
        assert resp.status_code == 400

        shp_uploads = os.path.join(app.config["UPLOAD_FOLDER"], "shp_uploads")
        assert not os.path.exists(os.path.join(shp_uploads, "two_shp.zip"))
        assert not os.path.exists(os.path.join(shp_uploads, "two_shp"))


def test_wkt_fixture_is_parseable():
    """Guard: the custom WKT used above must be parseable and not resolve to an EPSG code."""
    from pyproj import CRS

    crs = CRS.from_user_input(CUSTOM_PRJ_WKT)
    assert crs.to_epsg() is None
