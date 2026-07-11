from backend.integrations import (
    AdapterSettings,
    IntegrationNotConfigured,
    ManualAdapter,
)


def test_manual_adapter_never_sends():
    adapter = ManualAdapter("test", AdapterSettings())
    assert adapter.status()["networkCallsAllowed"] is False
    try:
        adapter.send({"record": 1}, "idem-1")
    except IntegrationNotConfigured:
        pass
    else:
        raise AssertionError("Manual adapter must fail closed")


def test_settings_require_explicit_enablement(monkeypatch):
    monkeypatch.setenv("PORT_MODE", "API")
    monkeypatch.setenv("PORT_BASE_URL", "https://sandbox.invalid")
    monkeypatch.setenv("PORT_CREDENTIAL_REF", "vault://port/test")
    settings = AdapterSettings.from_environment("PORT")
    assert settings.ready is False

    monkeypatch.setenv("PORT_ENABLED", "true")
    assert AdapterSettings.from_environment("PORT").ready is True
