def test_app_factory_bootstrap():
    from backend.app.main import create_app

    app = create_app()
    assert app is not None

    routes = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/health" in routes
    assert "/api/upload/" in routes
