from ukb.api.main import app


def test_search_and_connector_routes_are_registered() -> None:
    assert any(getattr(route, "path", "") == "/brain/search" for route in app.routes)
    assert any(getattr(route, "path", "") == "/ingestion/web" for route in app.routes)
