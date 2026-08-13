from ukb.api.main import app


def test_new_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]

    assert "/brain/search" in paths
    assert "/ingestion/web" in paths
