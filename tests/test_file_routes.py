from ukb.api.main import app


def test_api_includes_additional_routes() -> None:
    assert len(app.routes) >= 15
