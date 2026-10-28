"""Lógica de usuarios, ensayos guardados y auditoría. Trabaja sobre la base persistente (`app.db.datos`)."""
from __future__ import annotations

import json
import os
from typing import Any

from sqlalchemy import func, insert, select, update

from app import config
from app.core import auth
from app.core.pedido import ejecutar
from app.db import datos
from app.db.datos import anexar_registro, canonico, con_reintentos, digest_ensayo, digest_evento, ensayos, eventos, motor, registro, usuarios
from app.models.ensayos import (
    Comparacion,
    ConteoEstados,
    EnsayoNuevo,
    EnsayoOut,
    EnsayoResumen,
    EventoNuevo,
    EventoOut,
    RegistroOut,
    SelloRegistro,
    UsuarioCambio,
    UsuarioNuevo,
    UsuarioOut,
    VerificacionOut,
)
from app.models.schemas import Reaccion, SimulacionEntrada, SimulacionSalida

TRANSICIONES = {"registrado": {"revisado", "rechazado"}, "revisado": {"aprobado", "rechazado"}}
EMAIL_LOCAL = "local@retorta"


class NoEncontrado(LookupError):
    pass


class Prohibido(PermissionError):
    pass


class Conflicto(ValueError):
    pass


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------
def _usuario_out(f: Any) -> UsuarioOut:
    return UsuarioOut(id=f["id"], email=f["email"], nombre=f["nombre"], rol=f["rol"], activo=bool(f["activo"]), creado_en=f["creado_en"])


def obtener_usuario(usuario_id: int) -> UsuarioOut | None:
    with motor().connect() as c:
        f = c.execute(select(usuarios).where(usuarios.c.id == usuario_id)).mappings().first()
    return _usuario_out(f) if f else None


def obtener_usuario_con_clave(email: str) -> dict[str, Any] | None:
    with motor().connect() as c:
        f = c.execute(select(usuarios).where(usuarios.c.email == email.strip().lower())).mappings().first()
    return dict(f) if f else None


def listar_usuarios() -> list[UsuarioOut]:
    with motor().connect() as c:
        return [_usuario_out(f) for f in c.execute(select(usuarios).order_by(usuarios.c.id)).mappings()]


def crear_usuario(nuevo: UsuarioNuevo, por: int | None, validar_clave: bool = True) -> UsuarioOut:
    if validar_clave:
        auth.validar_clave_nueva(nuevo.clave)
    clave_hash = auth.hash_clave(nuevo.clave)

    def op():
        with motor().begin() as c:
            if c.execute(select(usuarios.c.id).where(usuarios.c.email == nuevo.email)).first():
                raise Conflicto(f"Ya existe un usuario con el correo {nuevo.email}")
            res = c.execute(insert(usuarios).values(
                email=nuevo.email, nombre=nuevo.nombre, rol=nuevo.rol, clave_hash=clave_hash, activo=True, creado_en=datos.ahora(),
            ))
            uid = res.inserted_primary_key[0]
            anexar_registro(c, usuario_id=por, accion="usuario.crear", entidad="usuario", entidad_id=uid,
                            detalle={"email": nuevo.email, "rol": nuevo.rol})
            return uid

    uid = con_reintentos(op)
    return obtener_usuario(uid)  # type: ignore[return-value]


def cambiar_usuario(usuario_id: int, cambio: UsuarioCambio, por: int) -> UsuarioOut:
    valores: dict[str, Any] = {}
    detalle: dict[str, Any] = {}
    if cambio.nombre is not None:
        valores["nombre"] = cambio.nombre
        detalle["nombre"] = cambio.nombre
    if cambio.rol is not None:
        valores["rol"] = cambio.rol
        detalle["rol"] = cambio.rol
    if cambio.activo is not None:
        valores["activo"] = cambio.activo
        detalle["activo"] = cambio.activo
    if cambio.clave is not None:
        auth.validar_clave_nueva(cambio.clave)
        valores["clave_hash"] = auth.hash_clave(cambio.clave)
        detalle["clave"] = "restablecida"  # nunca se registra la clave ni su hash
    if not valores:
        raise ValueError("No se indicó ningún cambio")

    def op():
        with motor().begin() as c:
            actual = c.execute(select(usuarios).where(usuarios.c.id == usuario_id)).mappings().first()
            if actual is None:
                raise NoEncontrado("Usuario no encontrado")
            nuevo_rol = valores.get("rol", actual["rol"])
            nuevo_activo = valores.get("activo", actual["activo"])
            if actual["rol"] == "admin" and actual["activo"] and (nuevo_rol != "admin" or not nuevo_activo):
                otros = c.execute(select(func.count()).select_from(usuarios).where(
                    usuarios.c.rol == "admin", usuarios.c.activo.is_(True), usuarios.c.id != usuario_id)).scalar()
                if not otros:
                    raise Conflicto("No se puede dejar el sistema sin ningún administrador activo")
            c.execute(update(usuarios).where(usuarios.c.id == usuario_id).values(**valores))
            anexar_registro(c, usuario_id=por, accion="usuario.modificar", entidad="usuario", entidad_id=usuario_id, detalle=detalle)

    con_reintentos(op)
    return obtener_usuario(usuario_id)  # type: ignore[return-value]


def registrar_sesion(usuario_id: int | None, ok: bool, email: str) -> None:
    def op():
        with motor().begin() as c:
            anexar_registro(c, usuario_id=usuario_id, accion="sesion.inicio" if ok else "sesion.fallida", entidad="usuario",
                            entidad_id=usuario_id, detalle={"email": email})

    con_reintentos(op)


def asegurar_usuario_local() -> UsuarioOut:
    """Modo sin login: todo lo hace un usuario administrador local, que se crea la primera vez."""
    f = obtener_usuario_con_clave(EMAIL_LOCAL)
    if f:
        return _usuario_out(f)
    import secrets

    return crear_usuario(
        UsuarioNuevo(email=EMAIL_LOCAL, nombre="Usuario local", rol="admin", clave=secrets.token_urlsafe(24)), por=None, validar_clave=False
    )


def asegurar_admin_inicial() -> UsuarioOut | None:
    """Si no hay usuarios reales y están SIM_ADMIN_EMAIL / SIM_ADMIN_CLAVE, crea el primer administrador."""
    email, clave = os.getenv("SIM_ADMIN_EMAIL"), os.getenv("SIM_ADMIN_CLAVE")
    if not email or not clave:
        return None
    with motor().connect() as c:
        hay = c.execute(select(func.count()).select_from(usuarios).where(usuarios.c.email != EMAIL_LOCAL)).scalar()
    if hay:
        return None
    return crear_usuario(UsuarioNuevo(email=email, nombre="Administrador", rol="admin", clave=clave), por=None)


# ---------------------------------------------------------------------------
# Ensayos
# ---------------------------------------------------------------------------
def version_modelo(reaccion: Reaccion, especificaciones: list) -> str:
    """Identifica con qué versión del programa y de los parámetros se calculó un ensayo."""
    huella = datos.sha256(canonico(reaccion.model_dump(mode="json")) + canonico([e.model_dump(mode="json") for e in especificaciones]))
    return f"{config.VERSION}+{huella[:12]}"


def _estado(eventos_ensayo: list[dict]) -> str:
    est = "registrado"
    for e in eventos_ensayo:
        if e["tipo"] in ("revisado", "aprobado", "rechazado"):
            est = e["tipo"]
    return est


def _eventos_de(c, ids: list[int]) -> dict[int, list[dict]]:
    if not ids:
        return {}
    filas = c.execute(
        select(eventos, usuarios.c.nombre.label("usuario")).join(usuarios, usuarios.c.id == eventos.c.usuario_id)
        .where(eventos.c.ensayo_id.in_(ids)).order_by(eventos.c.id)
    ).mappings()
    por: dict[int, list[dict]] = {i: [] for i in ids}
    for f in filas:
        por[f["ensayo_id"]].append(dict(f))
    return por


def _reemplazos(c, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    filas = c.execute(select(ensayos.c.corrige_a, func.max(ensayos.c.id)).where(ensayos.c.corrige_a.in_(ids)).group_by(ensayos.c.corrige_a))
    return {a: b for a, b in filas}


def _resumen(f: Any, evs: list[dict], reemplazado_por: int | None, nombre_usuario: str) -> EnsayoResumen:
    salida = json.loads(f["resultado"])
    r = salida.get("resultado") or {}
    decisiones = [e for e in evs if e["tipo"] != "comentario"]
    ultima = decisiones[-1] if decisiones else None
    return EnsayoResumen(
        id=f["id"], creado_en=f["creado_en"], usuario_id=f["usuario_id"], usuario=nombre_usuario,
        reaccion_id=f["reaccion_id"], reaccion_nombre=r.get("reaccion_nombre", ""), lote=f["lote"], estado=_estado(evs),  # type: ignore[arg-type]
        corrige_a=f["corrige_a"], reemplazado_por=reemplazado_por, vigente=reemplazado_por is None,
        version_modelo=f["version_modelo"], puntaje=r.get("puntaje"), categoria=r.get("categoria"),
        rendimiento_pct=r.get("rendimiento_pct"), pureza_producto_pct=r.get("pureza_producto_pct"),
        gramos_estimados=r.get("gramos_estimados"), origen=r.get("origen"),
        cumplimiento_especificaciones=r.get("cumplimiento_especificaciones"),
        revision_por=ultima["usuario"] if ultima else None,
        revision_en=ultima["creado_en"] if ultima else None,
        revision_comentario=(ultima["comentario"] or None) if ultima else None,
        n_comentarios=sum(1 for e in evs if e["tipo"] == "comentario"),
    )


def crear_ensayo(usuario_id: int, nuevo: EnsayoNuevo, corrige_a: int | None = None) -> EnsayoOut:
    entrada = SimulacionEntrada.model_validate(nuevo.model_dump(exclude={"lote", "notas"}))
    salida, reaccion = ejecutar(entrada)
    if salida.resultado is None:
        msg = salida.alertas[0].mensaje if salida.alertas else "faltan reactivos o hay cantidades en cero"
        raise ValueError(f"La mezcla no permite calcular un resultado, así que no se guarda como ensayo: {msg}")
    from app.db import database

    version = version_modelo(reaccion, database.listar_especificaciones())
    entrada_json = canonico(entrada.model_dump(mode="json"))
    resultado_json = canonico(salida.model_dump(mode="json"))

    def op() -> int:
        with motor().begin() as c:
            if corrige_a is not None:
                orig = c.execute(select(ensayos.c.id, ensayos.c.reaccion_id).where(ensayos.c.id == corrige_a)).first()
                if orig is None:
                    raise NoEncontrado(f"El ensayo {corrige_a} no existe")
                ya = c.execute(select(func.max(ensayos.c.id)).where(ensayos.c.corrige_a == corrige_a)).scalar()
                if ya:
                    raise Conflicto(f"El ensayo {corrige_a} ya fue corregido por el N° {ya}: corregí ese")
            fila = {
                "creado_en": datos.ahora(), "usuario_id": usuario_id, "reaccion_id": nuevo.reaccion_id, "lote": nuevo.lote or None,
                "notas": nuevo.notas, "entrada": entrada_json, "resultado": resultado_json, "version_modelo": version, "corrige_a": corrige_a,
            }
            d = digest_ensayo(fila)
            res = c.execute(insert(ensayos).values(**fila, digest=d))
            eid = res.inserted_primary_key[0]
            anexar_registro(c, usuario_id=usuario_id, accion="ensayo.crear", entidad="ensayo", entidad_id=eid,
                            detalle={"digest": d, "reaccion_id": nuevo.reaccion_id, "corrige_a": corrige_a, "version_modelo": version})
            return eid

    eid = con_reintentos(op)
    return obtener_ensayo(eid)  # type: ignore[return-value]


def listar_ensayos(
    reaccion_id: str | None = None, usuario_id: int | None = None, estado: str | None = None, lote: str | None = None,
    solo_vigentes: bool = False, limit: int = 100, offset: int = 0, orden: str = "recientes",
) -> tuple[list[EnsayoResumen], int]:
    """Devuelve (página de resúmenes, total que cumple los filtros).

    `orden="recientes"` va del más nuevo al más viejo; `orden="antiguos"` al revés (es el orden de una cola de revisión:
    lo que lleva más tiempo esperando va primero)."""
    q = select(ensayos, usuarios.c.nombre.label("nombre_usuario")).join(usuarios, usuarios.c.id == ensayos.c.usuario_id)
    cuenta = select(func.count()).select_from(ensayos)
    for col, val in ((ensayos.c.reaccion_id, reaccion_id), (ensayos.c.usuario_id, usuario_id)):
        if val is not None:
            q = q.where(col == val)
            cuenta = cuenta.where(col == val)
    if lote:
        q = q.where(ensayos.c.lote.ilike(f"%{lote}%"))
        cuenta = cuenta.where(ensayos.c.lote.ilike(f"%{lote}%"))
    q = q.order_by(ensayos.c.id.asc() if orden == "antiguos" else ensayos.c.id.desc())
    with motor().connect() as c:
        necesita_todos = estado is not None or solo_vigentes
        total = c.execute(cuenta).scalar() or 0
        filas = list(c.execute(q if necesita_todos else q.limit(limit).offset(offset)).mappings())
        ids = [f["id"] for f in filas]
        evs = _eventos_de(c, ids)
        reem = _reemplazos(c, ids)
        res = [_resumen(f, evs.get(f["id"], []), reem.get(f["id"]), f["nombre_usuario"]) for f in filas]
    if necesita_todos:
        if estado is not None:
            res = [r for r in res if r.estado == estado]
        if solo_vigentes:
            res = [r for r in res if r.vigente]
        total = len(res)
        res = res[offset : offset + limit]
    return res, total


def conteo_por_estado() -> ConteoEstados:
    """Cuántos ensayos hay en cada estado, para los contadores del panel de aceptación.

    Cuenta con tres consultas livianas (ids, ensayos que ya fueron corregidos y eventos de decisión) en vez de armar
    cada resumen, así que sigue siendo barato aunque haya miles de ensayos."""
    with motor().connect() as c:
        ids = list(c.execute(select(ensayos.c.id)).scalars())
        corregidos = set(c.execute(select(ensayos.c.corrige_a).where(ensayos.c.corrige_a.is_not(None)).distinct()).scalars())
        ultimo: dict[int, str] = {}
        for ensayo_id, tipo in c.execute(
            select(eventos.c.ensayo_id, eventos.c.tipo).where(eventos.c.tipo != "comentario").order_by(eventos.c.id)
        ):
            ultimo[ensayo_id] = tipo
    cuenta = {"registrado": 0, "revisado": 0, "aprobado": 0, "rechazado": 0, "reemplazados": 0}
    for i in ids:
        if i in corregidos:
            cuenta["reemplazados"] += 1
        else:
            cuenta[ultimo.get(i, "registrado")] += 1
    return ConteoEstados(**cuenta, total=len(ids))


def obtener_ensayo(ensayo_id: int) -> EnsayoOut | None:
    with motor().connect() as c:
        f = c.execute(
            select(ensayos, usuarios.c.nombre.label("nombre_usuario")).join(usuarios, usuarios.c.id == ensayos.c.usuario_id)
            .where(ensayos.c.id == ensayo_id)
        ).mappings().first()
        if f is None:
            return None
        evs = _eventos_de(c, [ensayo_id]).get(ensayo_id, [])
        reem = _reemplazos(c, [ensayo_id]).get(ensayo_id)
        sello = c.execute(
            select(registro).where(registro.c.accion == "ensayo.crear", registro.c.entidad_id == ensayo_id)
        ).mappings().first()
    base = _resumen(f, evs, reem, f["nombre_usuario"])
    return EnsayoOut(
        **base.model_dump(),
        notas=f["notas"],
        entrada=SimulacionEntrada.model_validate(json.loads(f["entrada"])),
        salida=SimulacionSalida.model_validate(json.loads(f["resultado"])),
        eventos=[EventoOut(id=e["id"], tipo=e["tipo"], usuario_id=e["usuario_id"], usuario=e["usuario"], creado_en=e["creado_en"], comentario=e["comentario"]) for e in evs],
        digest=f["digest"],
        sello=SelloRegistro(id=sello["id"], hash=sello["hash"], prev_hash=sello["prev_hash"], creado_en=sello["creado_en"]) if sello else None,
    )


def agregar_evento(usuario_id: int, rol: str, ensayo_id: int, nuevo: EventoNuevo) -> EnsayoOut:
    comentario = nuevo.comentario.strip()
    if nuevo.tipo == "comentario" and not comentario:
        raise ValueError("Un comentario no puede estar vacío")
    if nuevo.tipo == "rechazado" and not comentario:
        raise ValueError("Para rechazar hay que escribir el motivo")
    if nuevo.tipo != "comentario" and not auth.alcanza(rol, "calidad"):
        raise Prohibido("Revisar, aprobar o rechazar un ensayo requiere el rol de calidad")

    def op() -> None:
        with motor().begin() as c:
            f = c.execute(select(ensayos).where(ensayos.c.id == ensayo_id)).mappings().first()
            if f is None:
                raise NoEncontrado("Ensayo no encontrado")
            if nuevo.tipo != "comentario":
                if f["usuario_id"] == usuario_id:
                    raise Prohibido("Quien hizo el ensayo no puede revisarlo, aprobarlo ni rechazarlo")
                reem = _reemplazos(c, [ensayo_id]).get(ensayo_id)
                if reem:
                    raise Conflicto(f"Este ensayo fue reemplazado por el N° {reem}: se revisa ese")
                actual = _estado(_eventos_de(c, [ensayo_id]).get(ensayo_id, []))
                if nuevo.tipo not in TRANSICIONES.get(actual, set()):
                    raise Conflicto(f"Un ensayo «{actual}» no puede pasar a «{nuevo.tipo}»")
            fila = {"ensayo_id": ensayo_id, "tipo": nuevo.tipo, "usuario_id": usuario_id, "creado_en": datos.ahora(), "comentario": comentario}
            d = digest_evento(fila)
            res = c.execute(insert(eventos).values(**fila, digest=d))
            evid = res.inserted_primary_key[0]
            anexar_registro(c, usuario_id=usuario_id, accion=f"ensayo.{nuevo.tipo}", entidad="evento", entidad_id=evid,
                            detalle={"digest": d, "ensayo_id": ensayo_id})

    con_reintentos(op)
    return obtener_ensayo(ensayo_id)  # type: ignore[return-value]


def comparar(ids: list[int]) -> Comparacion:
    """Pone ensayos lado a lado: métricas y carga de cada compuesto (en gramos de material)."""
    outs = []
    for i in ids:
        e = obtener_ensayo(i)
        if e is None:
            raise NoEncontrado(f"El ensayo {i} no existe")
        outs.append(e)
    compuestos: dict[str, dict] = {}
    for e in outs:
        for carga in (e.salida.resultado.cargas if e.salida.resultado else []):
            fila = compuestos.setdefault(carga.id, {"id": carga.id, "gramos": {}})
            fila["gramos"][e.id] = carga.gramos_material
    def metrica(nombre: str, f) -> dict:
        return {"metrica": nombre, "valores": {e.id: f(e) for e in outs}}

    r = lambda e: e.salida.resultado  # noqa: E731
    metricas = [
        metrica("Puntaje", lambda e: r(e).puntaje),
        metrica("Rendimiento (%)", lambda e: r(e).rendimiento_pct),
        metrica("Origen del rendimiento", lambda e: r(e).rendimiento_origen),
        metrica("Pureza del producto (%)", lambda e: r(e).pureza_producto_pct),
        metrica("Origen de la pureza", lambda e: r(e).pureza_origen),
        metrica("Producto (g)", lambda e: r(e).gramos_estimados),
        metrica("Producto teórico (g)", lambda e: r(e).gramos_teoricos),
        metrica("Economía atómica (%)", lambda e: r(e).economia_atomica_pct),
        metrica("Reactivo limitante", lambda e: r(e).reactivo_limitante),
        metrica("Especificación", lambda e: r(e).cumplimiento_especificaciones),
        metrica("Datos", lambda e: r(e).origen),
    ]
    return Comparacion(ensayos=[EnsayoResumen(**e.model_dump(include=set(EnsayoResumen.model_fields))) for e in outs], compuestos=list(compuestos.values()), metricas=metricas)


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------
def listar_registro(limit: int = 100, offset: int = 0) -> tuple[list[RegistroOut], int]:
    with motor().connect() as c:
        total = c.execute(select(func.count()).select_from(registro)).scalar() or 0
        filas = c.execute(
            select(registro, usuarios.c.nombre.label("nombre_usuario")).join(usuarios, usuarios.c.id == registro.c.usuario_id, isouter=True)
            .order_by(registro.c.id.desc()).limit(limit).offset(offset)
        ).mappings()
        out = [
            RegistroOut(id=f["id"], creado_en=f["creado_en"], usuario_id=f["usuario_id"], usuario=f["nombre_usuario"], accion=f["accion"],
                        entidad=f["entidad"], entidad_id=f["entidad_id"], detalle=json.loads(f["detalle"]), prev_hash=f["prev_hash"], hash=f["hash"])
            for f in filas
        ]
    return out, total


def verificar() -> VerificacionOut:
    with motor().connect() as c:
        return VerificacionOut(**datos.verificar_cadena(c))
