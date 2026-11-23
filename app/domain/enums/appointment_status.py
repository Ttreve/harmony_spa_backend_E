"""Estados del ciclo de vida de una cita.

Ejemplo: cuando un cliente reserva, la cita queda PENDIENTE; cuando el spa la
acepta pasa a CONFIRMADA. Se usa en models/appointment.py (columna `status`).
"""

from enum import Enum


class AppointmentStatus(str, Enum):
    PENDIENTE = "PENDIENTE"  # reservada, aún sin aceptar por el spa
    CONFIRMADA = "CONFIRMADA"  # aceptada por el spa
    EN_PROCESO = "EN_PROCESO"  # el cliente está siendo atendido
    COMPLETADA = "COMPLETADA"  # atención finalizada
    CANCELADA = "CANCELADA"  # cancelada (puede tener penalización)
    NO_ASISTIO = "NO_ASISTIO"  # el cliente no se presentó
