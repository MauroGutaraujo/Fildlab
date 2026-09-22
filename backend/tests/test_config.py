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
