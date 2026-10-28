"""Ensayos guardados en el servidor, su revisión, reportes y auditoría."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api.deps import a_http, requiere
from app.core import auth, reportes, servicio_ensayos as srv
from app.db import database
from app.models.ensayos import (
    Comparacion,
    ConteoEstados,
    EnsayoNuevo,
    EnsayoOut,
    EnsayoResumen,
    EventoNuevo,
    RegistroOut,
    UsuarioOut,
    VerificacionOut,
)

router = APIRouter(tags=["ensayos"])

PDF = "application/pdf"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _ensayo_o_404(ensayo_id: int) -> EnsayoOut:
    e = srv.obtener_ensayo(ensayo_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Ensayo no encontrado")
    return e


def _ids(texto: str) -> list[int]:
    try:
        ids = [int(x) for x in texto.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="`ids` tiene que ser una lista de números separados por coma") from None
    if not 2 <= len(ids) <= 8 or len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="Para comparar hacen falta entre 2 y 8 ensayos distintos")
    return ids


def _catalogo_de(e: EnsayoOut) -> dict:
    return database.obtener_compuestos({c.id for c in e.entrada.componentes})


@router.post("/ensayos", response_model=EnsayoOut, status_code=201)
def crear_ensayo(nuevo: EnsayoNuevo, usuario: UsuarioOut = Depends(requiere("analista"))):
    """Guarda un ensayo. El resultado lo calcula el servidor con la mezcla recibida; no se acepta uno de afuera."""
    try:
        return srv.crear_ensayo(usuario.id, nuevo)
    except Exception as e:  # noqa: BLE001
        raise a_http(e)


@router.get("/ensayos", response_model=list[EnsayoResumen])
def listar_ensayos(
    response: Response,
    reaccion_id: str | None = None,
    usuario_id: int | None = None,
    estado: str | None = Query(None, pattern="^(registrado|revisado|aprobado|rechazado)$"),
    lote: str | None = None,
    solo_vigentes: bool = False,
    orden: str = Query("recientes", pattern="^(recientes|antiguos)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: UsuarioOut = Depends(requiere("lectura")),
):
    """Ensayos del más nuevo al más viejo (`orden=antiguos` los da al revés, el orden natural de una cola de revisión).

    El total que cumple los filtros va en `X-Total-Count`."""
    res, total = srv.listar_ensayos(reaccion_id, usuario_id, estado, lote, solo_vigentes, limit, offset, orden)
    response.headers["X-Total-Count"] = str(total)
    return res


@router.get("/ensayos/conteo", response_model=ConteoEstados)
def conteo_por_estado(_: UsuarioOut = Depends(requiere("lectura"))):
    """Cuántos ensayos vigentes hay registrados, revisados, aprobados y rechazados (más los ya reemplazados)."""
    return srv.conteo_por_estado()


@router.get("/ensayos/comparar", response_model=Comparacion)
def comparar(ids: str, _: UsuarioOut = Depends(requiere("lectura"))):
    """Pone de 2 a 8 ensayos lado a lado (`ids=3,5,8`)."""
    try:
        return srv.comparar(_ids(ids))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise a_http(e)


@router.get("/ensayos/comparar.xlsx")
def comparar_xlsx(ids: str, _: UsuarioOut = Depends(requiere("lectura"))):
    try:
        c = srv.comparar(_ids(ids))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise a_http(e)
    catalogo = database.obtener_compuestos({x["id"] for x in c.compuestos})
    return Response(
        reportes.reporte_comparacion_xlsx(c, catalogo), media_type=XLSX,
        headers={"Content-Disposition": 'attachment; filename="comparacion-ensayos.xlsx"'},
    )


@router.get("/ensayos/{ensayo_id}", response_model=EnsayoOut)
def obtener_ensayo(ensayo_id: int, _: UsuarioOut = Depends(requiere("lectura"))):
    return _ensayo_o_404(ensayo_id)


@router.post("/ensayos/{ensayo_id}/corregir", response_model=EnsayoOut, status_code=201)
def corregir_ensayo(ensayo_id: int, nuevo: EnsayoNuevo, usuario: UsuarioOut = Depends(requiere("analista"))):
    """No se edita un ensayo: se guarda otro que lo reemplaza. El original queda tal cual, marcado como reemplazado."""
    original = _ensayo_o_404(ensayo_id)
    if original.usuario_id != usuario.id and not auth.alcanza(usuario.rol, "calidad"):
        raise HTTPException(status_code=403, detail="Solo quien hizo el ensayo o el área de calidad puede corregirlo")
    try:
        return srv.crear_ensayo(usuario.id, nuevo, corrige_a=ensayo_id)
    except Exception as e:  # noqa: BLE001
        raise a_http(e)


@router.post("/ensayos/{ensayo_id}/eventos", response_model=EnsayoOut, status_code=201)
def agregar_evento(ensayo_id: int, nuevo: EventoNuevo, usuario: UsuarioOut = Depends(requiere("analista"))):
    """Comentario, revisión, aprobación o rechazo. Revisar, aprobar y rechazar son del rol calidad y no de quien hizo el ensayo."""
    try:
        return srv.agregar_evento(usuario.id, usuario.rol, ensayo_id, nuevo)
    except Exception as e:  # noqa: BLE001
        raise a_http(e)


@router.get("/ensayos/{ensayo_id}/reporte.pdf")
def reporte_pdf(ensayo_id: int, _: UsuarioOut = Depends(requiere("lectura"))):
    e = _ensayo_o_404(ensayo_id)
    return Response(
        reportes.reporte_pdf(e, _catalogo_de(e)), media_type=PDF,
        headers={"Content-Disposition": f'attachment; filename="ensayo-{e.id:03d}.pdf"'},
    )


@router.get("/ensayos/{ensayo_id}/reporte.xlsx")
def reporte_xlsx(ensayo_id: int, _: UsuarioOut = Depends(requiere("lectura"))):
    e = _ensayo_o_404(ensayo_id)
    return Response(
        reportes.reporte_xlsx(e, _catalogo_de(e)), media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="ensayo-{e.id:03d}.xlsx"'},
    )


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------
@router.get("/auditoria", response_model=list[RegistroOut])
def auditoria(
    response: Response,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: UsuarioOut = Depends(requiere("calidad")),
):
    """Registro de todo lo que se hizo, del más nuevo al más viejo (quién, cuándo, qué)."""
    filas, total = srv.listar_registro(limit, offset)
    response.headers["X-Total-Count"] = str(total)
    return filas


@router.get("/auditoria/verificar", response_model=VerificacionOut)
def verificar(_: UsuarioOut = Depends(requiere("calidad"))):
    """Recorre la cadena de hashes y comprueba que nada se haya modificado o borrado por fuera de la aplicación.

    Guardá `ultimo_hash` en un lugar aparte (otro sistema, un papel firmado): si más adelante la cadena entera fuera reescrita,
    ese valor ya no coincidiría.
    """
    return srv.verificar()
