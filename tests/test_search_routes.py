from ukb.api.main import app


def test_search_and_connector_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/ingestion/web" in paths
    assert "/connectors/web/status" in paths
    assert "/brain/search" in paths
    assert "/search/status" in paths
    assert "/search/rebuild" in paths
