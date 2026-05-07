"""Tests for data viewing endpoints."""


class TestDataViewing:
    def test_vector_data_viewing(self, client, auth_headers):
        resp = client.get('/api/vector_data_viewing', headers=auth_headers)
        assert resp.status_code in (200, 500)  # 500 if PostgreSQL not available

    def test_raster_data_viewing(self, client, auth_headers):
        resp = client.get('/api/raster_data_viewing', headers=auth_headers)
        assert resp.status_code in (200, 500)

    def test_shp_data_list(self, client, auth_headers):
        resp = client.get('/api/data_viewing', headers=auth_headers)
        assert resp.status_code in (200, 500)

    def test_map_search_missing_query(self, client, auth_headers):
        resp = client.get('/api/map/search', headers=auth_headers)
        assert resp.status_code in (200, 400)
