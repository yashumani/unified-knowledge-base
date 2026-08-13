from ukb.api.main import app


def test_new_routes_are_registered() -> None:
    paths = set()
    for route in app.routes:
        value = getattr(route, "path", "")
        if value:
            paths.add(value)
    assert "/brain/search" in paths
    assert "/ingestion/web" in paths
