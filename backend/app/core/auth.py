"""Contraseñas y tokens, solo con la biblioteca estándar.

- Contraseñas: scrypt con sal aleatoria (`scrypt$n$r$p$sal$hash`, en base64 URL-safe).
- Tokens: `payload.firma` con HMAC-SHA256 sobre el payload (id de usuario y vencimiento). No guardan datos sensibles.
- Roles, de menor a mayor poder: lectura < analista < calidad < admin.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

ROLES = ("lectura", "analista", "calidad", "admin")
NIVEL = {r: i for i, r in enumerate(ROLES, start=1)}

_N, _R, _P = 2**14, 8, 1
MIN_CLAVE = 10


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class ClaveDebil(ValueError):
    pass


def validar_clave_nueva(clave: str) -> None:
    if len(clave) < MIN_CLAVE:
        raise ClaveDebil(f"La clave tiene que tener al menos {MIN_CLAVE} caracteres")
    if clave.lower() == clave or clave.upper() == clave or not any(c.isdigit() for c in clave):
        raise ClaveDebil("La clave tiene que combinar mayúsculas, minúsculas y al menos un número")


def hash_clave(clave: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(clave.encode("utf-8"), salt=sal, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${_b64(sal)}${_b64(h)}"


def verificar_clave(clave: str, guardado: str) -> bool:
    try:
        esquema, n, r, p, sal, h = guardado.split("$")
        if esquema != "scrypt":
            return False
        calculado = hashlib.scrypt(clave.encode("utf-8"), salt=_unb64(sal), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calculado, _unb64(h))
    except (ValueError, TypeError):
        return False


# Una clave inexistente también cuesta un scrypt: así no se distingue "usuario inexistente" por el tiempo de respuesta.
_HASH_FALSO = hash_clave("clave-falsa-para-igualar-tiempos")


def verificar_contra_nada(clave: str) -> None:
    verificar_clave(clave, _HASH_FALSO)


def emitir_token(usuario_id: int, secreto: str, horas: float, ahora: float | None = None) -> str:
    vence = int((ahora if ahora is not None else time.time()) + horas * 3600)
    payload = _b64(json.dumps({"sub": usuario_id, "exp": vence}, separators=(",", ":")).encode())
    firma = _b64(hmac.new(secreto.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{firma}"


def leer_token(token: str, secreto: str, ahora: float | None = None) -> int | None:
    """Devuelve el id de usuario si el token es auténtico y no venció; si no, None."""
    try:
        payload, firma = token.split(".")
        esperada = _b64(hmac.new(secreto.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(firma, esperada):
            return None
        datos = json.loads(_unb64(payload))
        if datos["exp"] < (ahora if ahora is not None else time.time()):
            return None
        return int(datos["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def alcanza(rol: str, minimo: str) -> bool:
    return NIVEL.get(rol, 0) >= NIVEL[minimo]


class LimiteDeIntentos:
    """Bloquea un correo después de varios fallos seguidos (en memoria: se reinicia con el servidor)."""

    def __init__(self, maximo: int = 5, minutos: float = 5.0):
        self.maximo = maximo
        self.segundos = minutos * 60
        self._fallos: dict[str, tuple[int, float]] = {}

    def bloqueado(self, clave: str, ahora: float | None = None) -> float:
        """Segundos que faltan para poder reintentar (0 si no está bloqueado)."""
        t = ahora if ahora is not None else time.time()
        n, hasta = self._fallos.get(clave, (0, 0.0))
        if n >= self.maximo and hasta > t:
            return hasta - t
        if n >= self.maximo and hasta <= t:
            self._fallos.pop(clave, None)
        return 0.0

    def fallo(self, clave: str, ahora: float | None = None) -> None:
        t = ahora if ahora is not None else time.time()
        n, _ = self._fallos.get(clave, (0, 0.0))
        self._fallos[clave] = (n + 1, t + self.segundos)

    def acierto(self, clave: str) -> None:
        self._fallos.pop(clave, None)

    def reiniciar(self) -> None:
        self._fallos.clear()


LIMITE_LOGIN = LimiteDeIntentos()
