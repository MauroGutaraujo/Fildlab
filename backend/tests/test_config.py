import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_exige_jwt_secret_no_vacio():
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://u:p@h/db", jwt_secret="")


def test_settings_exige_jwt_secret_de_al_menos_32_caracteres():
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://u:p@h/db", jwt_secret="corta")


def test_settings_exige_database_url_no_vacia():
    with pytest.raises(ValidationError):
        Settings(database_url="", jwt_secret="x" * 32)


def test_settings_acepta_valores_validos():
    s = Settings(database_url="postgresql://u:p@h/db", jwt_secret="x" * 32)
    assert s.jwt_secret == "x" * 32


@pytest.mark.parametrize("origin", ["*", "https://*.pages.dev", "https://allowed.example/path", "https://user:pass@allowed.example"])
def test_cors_requires_explicit_origin_without_wildcards_or_credentials(origin):
    with pytest.raises(ValidationError):
        Settings(cors_origins=[origin])


@pytest.mark.parametrize("limits", [
    {"max_request_body_bytes": 0}, {"login_attempts_per_window": 0},
    {"password_verify_concurrency": 0}, {"password_verify_concurrency": 100},
])
def test_limits_cannot_be_disabled_or_allow_unbounded_password_work(limits):
    with pytest.raises(ValidationError):
        Settings(**limits)
