from datetime import timedelta

from sqlalchemy import select

from app.domain.enums.user_role import UserRole
from app.infrastructure.database.session import SessionLocal
from app.models import UserSession
from app.models.user import utc_now_naive
from tests.conftest import PASSWORD

LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def _get_session_by_user(user_id: int) -> list[UserSession]:
    with SessionLocal() as db:
        return list(
            db.execute(select(UserSession).where(UserSession.user_id == user_id))
            .scalars()
            .all()
        )


def test_login_success(client, make_user):
    user = make_user(UserRole.ADMIN, email="admin@harmonyspa.co")

    response = client.post(LOGIN, json={"email": "admin@harmonyspa.co", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] == 7200  # 2 horas
    assert body["inactivity_timeout"] == 1800  # 30 minutos
    assert body["user"]["email"] == "admin@harmonyspa.co"
    assert body["user"]["role"] == "ADMIN"
    assert "password_hash" not in body["user"]

    sessions = _get_session_by_user(user.id)
    assert len(sessions) == 1
    assert sessions[0].is_active is True


def test_login_is_case_insensitive_on_email(client, make_user):
    make_user(email="cliente@harmonyspa.co")

    response = client.post(LOGIN, json={"email": "CLIENTE@HarmonySpa.co", "password": PASSWORD})

    assert response.status_code == 200


def test_login_wrong_password(client, make_user):
    make_user(email="cliente@harmonyspa.co")

    response = client.post(LOGIN, json={"email": "cliente@harmonyspa.co", "password": "Incorrecta1"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


def test_login_unknown_email_has_same_error(client):
    response = client.post(LOGIN, json={"email": "nadie@harmonyspa.co", "password": PASSWORD})

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


def test_login_inactive_user(client, make_user):
    make_user(email="inactivo@harmonyspa.co", is_active=False)

    response = client.post(LOGIN, json={"email": "inactivo@harmonyspa.co", "password": PASSWORD})

    assert response.status_code == 403


def test_me_requires_token(client):
    assert client.get(ME).status_code == 401
    assert client.get(ME, headers={"Authorization": "Bearer basura"}).status_code == 401


def test_me_returns_current_user(client, make_user, login, auth):
    make_user(UserRole.ESTETICISTA, email="esteticista@harmonyspa.co")
    token = login("esteticista@harmonyspa.co")

    response = client.get(ME, headers=auth(token))

    assert response.status_code == 200
    assert response.json()["email"] == "esteticista@harmonyspa.co"


def test_logout_revokes_session(client, make_user, login, auth):
    user = make_user(email="cliente@harmonyspa.co")
    token = login("cliente@harmonyspa.co")

    response = client.post(LOGOUT, headers=auth(token))

    assert response.status_code == 204  # No Content
    assert client.get(ME, headers=auth(token)).status_code == 401

    session = _get_session_by_user(user.id)[0]
    assert session.is_active is False
    assert session.revoked_at is not None


def test_logout_only_closes_that_session(client, make_user, login, auth):
    make_user(email="cliente@harmonyspa.co")
    token_a = login("cliente@harmonyspa.co")
    token_b = login("cliente@harmonyspa.co")

    client.post(LOGOUT, headers=auth(token_a))

    assert client.get(ME, headers=auth(token_a)).status_code == 401
    assert client.get(ME, headers=auth(token_b)).status_code == 200


def test_expired_session_is_rejected(client, make_user, login, auth):
    user = make_user(email="cliente@harmonyspa.co")
    token = login("cliente@harmonyspa.co")

    with SessionLocal() as db:
        session = db.execute(
            select(UserSession).where(UserSession.user_id == user.id)
        ).scalar_one()
        session.expires_at = utc_now_naive() - timedelta(minutes=1)
        db.commit()

    assert client.get(ME, headers=auth(token)).status_code == 401


def test_inactive_session_is_closed(client, make_user, login, auth):
    user = make_user(email="cliente@harmonyspa.co")
    token = login("cliente@harmonyspa.co")

    with SessionLocal() as db:
        session = db.execute(
            select(UserSession).where(UserSession.user_id == user.id)
        ).scalar_one()
        session.last_activity_at = utc_now_naive() - timedelta(hours=2)
        db.commit()

    response = client.get(ME, headers=auth(token))

    assert response.status_code == 401
    assert "inactividad" in response.json()["detail"]
    assert _get_session_by_user(user.id)[0].is_active is False


def test_activity_refreshes_last_activity(client, make_user, login, auth):
    user = make_user(email="cliente@harmonyspa.co")
    token = login("cliente@harmonyspa.co")

    with SessionLocal() as db:
        session = db.execute(
            select(UserSession).where(UserSession.user_id == user.id)
        ).scalar_one()
        old = utc_now_naive() - timedelta(minutes=10)
        session.last_activity_at = old
        db.commit()

    assert client.get(ME, headers=auth(token)).status_code == 200

    assert _get_session_by_user(user.id)[0].last_activity_at > old
