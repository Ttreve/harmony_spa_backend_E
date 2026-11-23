from datetime import timedelta

import pytest

from app.core.permissions import assignable_roles, can_manage
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_jti,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.domain.enums.user_role import UserRole
from app.models.user import utc_now_naive


def test_hash_and_verify_password():
    hashed = hash_password("ClaveSegura2026")

    assert hashed != "ClaveSegura2026"
    assert verify_password("ClaveSegura2026", hashed)
    assert not verify_password("OtraClave2026", hashed)


def test_password_is_hashed_with_argon2id():
    # Argon2id deja su identificador al inicio del hash.
    assert hash_password("ClaveSegura2026").startswith("$argon2id$")


def test_same_password_produces_different_hashes():
    # Cada hash lleva una sal aleatoria distinta.
    assert hash_password("ClaveSegura2026") != hash_password("ClaveSegura2026")


def test_verify_password_with_invalid_hash_returns_false():
    assert not verify_password("ClaveSegura2026", "esto-no-es-un-hash")


@pytest.mark.parametrize(
    "password",
    [
        "corta1",  # menos de 12 caracteres
        "Clave12345",  # 10 caracteres
        "ClaveSegura!!",  # sin números
        "123456789012",  # sin letras
        "a1" * 70,  # más de 128 caracteres
    ],
)
def test_weak_passwords_are_rejected(password):
    with pytest.raises(ValueError):
        validate_password_strength(password)


def test_strong_password_is_accepted():
    assert validate_password_strength("MiClaveSegura2026!") == "MiClaveSegura2026!"


def test_token_roundtrip():
    jti = generate_jti()
    token = create_access_token(
        user_id=7,
        role="ADMIN",
        jti=jti,
        expires_at=utc_now_naive() + timedelta(minutes=5),
    )

    payload = decode_access_token(token)

    assert payload is not None
    assert payload.user_id == 7
    assert payload.role == "ADMIN"
    assert payload.jti == jti


def test_tampered_token_is_rejected():
    token = create_access_token(
        user_id=1,
        role="CLIENTE",
        jti=generate_jti(),
        expires_at=utc_now_naive() + timedelta(minutes=5),
    )

    assert decode_access_token(token + "x") is None
    assert decode_access_token("no-es-un-jwt") is None


def test_expired_token_is_rejected():
    token = create_access_token(
        user_id=1,
        role="CLIENTE",
        jti=generate_jti(),
        expires_at=utc_now_naive() - timedelta(minutes=1),
    )

    assert decode_access_token(token) is None


def test_role_permissions():
    assert can_manage(UserRole.SUPER_ADMIN, UserRole.ADMIN)
    assert can_manage(UserRole.ADMIN, UserRole.CLIENTE)
    assert not can_manage(UserRole.ADMIN, UserRole.ADMIN)
    assert not can_manage(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    assert not can_manage(UserRole.CLIENTE, UserRole.ESTETICISTA)

    assert UserRole.SUPER_ADMIN not in assignable_roles(UserRole.SUPER_ADMIN)
    assert UserRole.ADMIN not in assignable_roles(UserRole.ADMIN)
    assert assignable_roles(UserRole.CLIENTE) == frozenset()
