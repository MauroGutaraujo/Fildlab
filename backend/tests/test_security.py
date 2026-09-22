from datetime import timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_es_argon2_y_no_reversible():
    h = hash_password("secreto-123")
    assert h.startswith("$argon2id$")
    assert "secreto-123" not in h
    assert hash_password("secreto-123") != h  # sal distinta


def test_verify_rechaza_password_incorrecto():
    h = hash_password("correcto")
    assert verify_password("correcto", h) is True
    assert verify_password("otro", h) is False
    assert verify_password("x", "no-es-un-hash") is False


def test_token_contiene_sub_y_rol():
    p = decode_access_token(create_access_token(7, "GERENCIA"))
    assert p.sub == 7 and p.rol == "GERENCIA"


def test_token_expirado_lanza_error():
    t = create_access_token(1, "TECNICO", expires_delta=timedelta(seconds=-1))
    with pytest.raises(TokenError):
        decode_access_token(t)


def test_token_manipulado_lanza_error():
    t = create_access_token(1, "TECNICO")
    with pytest.raises(TokenError):
        decode_access_token(t[:-2] + ("AA" if not t.endswith("AA") else "BB"))


def test_token_firmado_con_otra_clave_lanza_error():
    t = jwt.encode({"sub": "1", "rol": "GERENCIA", "exp": 9999999999}, "otra-clave-distinta-de-32-bytes-min!!", "HS256")
    with pytest.raises(TokenError):
        decode_access_token(t)


def test_argon2_usa_parametros_owasp():
    s = get_settings()
    assert s.jwt_secret  # configurada
    h = hash_password("x")
    assert "m=19456,t=2,p=1" in h
