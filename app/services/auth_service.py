"""Servicio de autenticación: login, logout y validación de cada petición.

Flujo completo (JWT + tabla user_sessions):

  LOGIN   -> valida correo/contraseña (Argon2) -> crea una fila en
             user_sessions con un `jti` único -> devuelve un JWT que lleva ese jti.
  CADA PETICIÓN -> `authenticate` decodifica el JWT, busca la sesión por `jti`
             y comprueba: sesión activa, no vencida (2 h) y sin inactividad
             (30 min). Si todo está bien, actualiza `last_activity_at` (como máximo cada 5 min).
  LOGOUT  -> marca la sesión como revocada: el token deja de servir aunque
             todavía no haya expirado.

Los tiempos salen de `settings` (.env): ACCESS_TOKEN_EXPIRE_MINUTES e
INACTIVITY_TIMEOUT_MINUTES.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    dummy_verify,
    generate_jti,
    verify_password,
)
from app.models import User, UserSession
from app.models.user import utc_now_naive
from app.repositories import SessionRepository, UserRepository

# Cada cuánto se refresca `last_activity_at` como máximo.
ACTIVITY_UPDATE_INTERVAL = timedelta(minutes=5)


class AuthService:
    """Inicio de sesión, cierre de sesión y validación de tokens.

    Cada login crea una fila en user_sessions identificada por el `jti` del
    JWT. Un token solo es válido mientras su sesión esté activa, no haya
    vencido (expires_at) y no supere el tiempo máximo de inactividad.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)

    # ------------------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------------------
    def login(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, datetime, User]:
        """Autentica al usuario y abre una sesión nueva.

        Devuelve (token, fecha de vencimiento, usuario). Un mismo usuario
        puede llamar a login varias veces: cada llamada abre una sesión
        independiente (computador, celular, etc.).
        """
        user = self.users.get_by_email(email.strip().lower())

        # Correo inexistente: se simula una verificación para que la respuesta
        # tarde lo mismo y no se pueda descubrir qué correos existen.
        if user is None:
            dummy_verify(password)
            raise UnauthorizedError("Credenciales inválidas")

        # Mismo mensaje para "correo inexistente" y "contraseña incorrecta".
        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Credenciales inválidas")

        # La contraseña es correcta, pero la cuenta fue desactivada.
        if not user.is_active:
            raise ForbiddenError("La cuenta está desactivada")

        now = utc_now_naive()
        expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jti = generate_jti()

        # Se registra la sesión ANTES de entregar el token.
        self.sessions.add(
            UserSession(
                user_id=user.id,
                jti=jti,
                created_at=now,
                last_activity_at=now,
                expires_at=expires_at,
                is_active=True,
                # Se recortan para que quepan en las columnas (45 y 512).
                ip_address=ip_address[:45] if ip_address else None,
                user_agent=user_agent[:512] if user_agent else None,
            )
        )
        self.db.commit()

        token = create_access_token(
            user_id=user.id,
            role=user.role.value,
            jti=jti,
            expires_at=expires_at,
        )
        return token, expires_at, user

    # ------------------------------------------------------------------
    # LOGOUT
    # ------------------------------------------------------------------
    def logout(self, session: UserSession) -> None:
        """Cierra SOLO la sesión indicada; las demás del usuario siguen activas."""
        self.sessions.revoke(session, utc_now_naive())
        self.db.commit()

    # ------------------------------------------------------------------
    # VALIDACIÓN DE CADA PETICIÓN
    # ------------------------------------------------------------------
    def authenticate(self, token: str) -> tuple[User, UserSession]:
        """Valida el token y su sesión. Registra la actividad del usuario.

        Lo invoca `get_auth_context` (app/api/deps.py) en cada endpoint
        protegido. Lanza UnauthorizedError (401) si algo falla.
        """
        # 1) Firma y vencimiento del JWT.
        payload = decode_access_token(token)
        if payload is None:
            raise UnauthorizedError("Token inválido o expirado")

        # 2) La sesión debe existir, ser del mismo usuario y seguir activa.
        session = self.sessions.get_by_jti(payload.jti)
        if (
            session is None
            or session.user_id != payload.user_id
            or not session.is_active
            or session.revoked_at is not None
        ):
            raise UnauthorizedError("La sesión no es válida")

        now = utc_now_naive()

        # 3) Vencimiento absoluto (máximo 2 horas desde el login).
        if session.expires_at <= now:
            self._close_session(session, now)
            raise UnauthorizedError("La sesión ha expirado")

        # 4) Inactividad (máximo 30 minutos sin usar la API).
        inactivity_limit = timedelta(minutes=settings.INACTIVITY_TIMEOUT_MINUTES)
        if now - session.last_activity_at > inactivity_limit:
            self._close_session(session, now)
            raise UnauthorizedError("Sesión cerrada por inactividad")

        # 5) El usuario debe seguir existiendo y activo.
        user = self.users.get_by_id(session.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("El usuario no está disponible")

        # Todo en orden: se renueva la ventana de inactividad. Para no escribir
        # en MySQL en CADA petición, solo se actualiza si pasaron 5 minutos o más
        # desde el último registro (el límite de 30 min nunca se amplía a propósito).
        if now - session.last_activity_at >= ACTIVITY_UPDATE_INTERVAL:
            session.last_activity_at = now
            self.db.commit()
        return user, session

    def _close_session(self, session: UserSession, now: datetime) -> None:
        """Revoca la sesión y confirma el cambio (expiración o inactividad)."""
        self.sessions.revoke(session, now)
        self.db.commit()
