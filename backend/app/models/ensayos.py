"""Esquemas de usuarios, ensayos guardados y auditoría."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.schemas import SimulacionEntrada, SimulacionSalida

Rol = Literal["lectura", "analista", "calidad", "admin"]
TipoEvento = Literal["comentario", "revisado", "aprobado", "rechazado"]
EstadoEnsayo = Literal["registrado", "revisado", "aprobado", "rechazado"]


# ---------- Usuarios ----------
class UsuarioOut(BaseModel):
    id: int
    email: str
    nombre: str
    rol: Rol
    activo: bool
    creado_en: str


class UsuarioNuevo(BaseModel):
    email: str = Field(min_length=3, max_length=200, pattern=r"^[^@\s]+@[^@\s]+$")
    nombre: str = Field(min_length=1, max_length=200)
    rol: Rol
    clave: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _minusculas(cls, v: str) -> str:
        return v.strip().lower()


class UsuarioCambio(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    rol: Rol | None = None
    activo: bool | None = None
    clave: str | None = Field(default=None, max_length=200)


class LoginEntrada(BaseModel):
    email: str = Field(max_length=200)
    clave: str = Field(max_length=200)


class LoginSalida(BaseModel):
    token: str
    usuario: UsuarioOut
    horas: float


class Sistema(BaseModel):
    version: str
    auth_activa: bool
    base: str
    rdkit: bool


# ---------- Ensayos ----------
class EnsayoNuevo(SimulacionEntrada):
    """Lo mismo que una simulación, más lote y notas. El resultado lo calcula el servidor: no se acepta uno de afuera."""

    lote: str | None = Field(default=None, max_length=100)
    notas: str = Field(default="", max_length=4000)


class EventoNuevo(BaseModel):
    tipo: TipoEvento
    comentario: str = Field(default="", max_length=4000)


class EventoOut(BaseModel):
    id: int
    tipo: TipoEvento
    usuario_id: int
    usuario: str
    creado_en: str
    comentario: str


class EnsayoResumen(BaseModel):
    id: int
    creado_en: str
    usuario_id: int
    usuario: str
    reaccion_id: str
    reaccion_nombre: str
    lote: str | None
    estado: EstadoEnsayo
    corrige_a: int | None
    reemplazado_por: int | None
    vigente: bool
    version_modelo: str
    puntaje: int | None
    categoria: str | None
    rendimiento_pct: float | None
    pureza_producto_pct: float | None
    gramos_estimados: float | None
    origen: Literal["estimacion", "mixto", "medido"] | None
    cumplimiento_especificaciones: str | None
    # Última decisión (revisado / aprobado / rechazado), salida de los eventos: no es una columna nueva.
    revision_por: str | None = None
    revision_en: str | None = None
    revision_comentario: str | None = None
    n_comentarios: int = 0


class ConteoEstados(BaseModel):
    """Cuántos ensayos hay en cada estado. Los cuatro estados cuentan solo ensayos vigentes; un ensayo reemplazado por una
    corrección va aparte (`reemplazados`) porque ya no se revisa. `total` incluye todos."""

    registrado: int
    revisado: int
    aprobado: int
    rechazado: int
    reemplazados: int
    total: int


class SelloRegistro(BaseModel):
    id: int
    hash: str
    prev_hash: str
    creado_en: str


class EnsayoOut(EnsayoResumen):
    notas: str
    entrada: SimulacionEntrada
    salida: SimulacionSalida
    eventos: list[EventoOut]
    digest: str
    sello: SelloRegistro | None


class RegistroOut(BaseModel):
    id: int
    creado_en: str
    usuario_id: int | None
    usuario: str | None
    accion: str
    entidad: str
    entidad_id: int | None
    detalle: dict
    prev_hash: str
    hash: str


class VerificacionOut(BaseModel):
    ok: bool
    registros: int
    ensayos_verificados: int
    eventos_verificados: int
    ultimo_hash: str
    total_errores: int
    errores: list[dict]


class Comparacion(BaseModel):
    ensayos: list[EnsayoResumen]
    compuestos: list[dict]
    metricas: list[dict]
