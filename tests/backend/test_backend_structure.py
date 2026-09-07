def test_backend_imports():
    import config.settings
    import config.urls

    assert config.settings is not None
    assert config.urls is not None


def test_all_backend_apps_import():
    modules = [
        "apps.auth.views",
        "apps.auth.urls",
        "apps.users.views",
        "apps.users.serializers",
        "apps.users.urls",
        "apps.files.views",
        "apps.files.validators",
        "apps.files.urls",
        "apps.processing.services",
        "apps.processing.views",
        "apps.processing.urls",
        "apps.data.views",
        "apps.data.urls",
        "apps.dashboard.views",
        "apps.dashboard.urls",
        "apps.exports.views",
        "apps.exports.urls",
        "apps.chatbot.services",
        "apps.chatbot.views",
        "apps.chatbot.urls",
    ]

    for module_name in modules:
        module = __import__(module_name, fromlist=["*"])
        assert module is not None