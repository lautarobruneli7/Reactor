"""Dependencias de FastAPI: quién es el usuario de este pedido y qué rol mínimo hace falta."""
from fastapi import Depends, HTTPException, Request

from app import config
from app.core import auth, servicio_ensayos as srv
from app.models.ensayos import UsuarioOut


def usuario_actual(request: Request) -> UsuarioOut:
    if not config.auth_activa():
        return srv.asegurar_usuario_local()
    cabecera = request.headers.get("authorization", "")
    esquema, _, token = cabecera.partition(" ")
    no_autenticado = HTTPException(status_code=401, detail="Hay que iniciar sesión", headers={"WWW-Authenticate": "Bearer"})
    if esquema.lower() != "bearer" or not token:
        raise no_autenticado
    uid = auth.leer_token(token.strip(), config.secreto())
    if uid is None:
        raise HTTPException(status_code=401, detail="La sesión venció o no es válida: volvé a iniciar sesión", headers={"WWW-Authenticate": "Bearer"})
    usuario = srv.obtener_usuario(uid)
    if usuario is None or not usuario.activo:
        raise HTTPException(status_code=401, detail="El usuario no existe o está desactivado", headers={"WWW-Authenticate": "Bearer"})
    return usuario


def requiere(minimo: str):
    """Dependencia que exige un rol mínimo (lectura < analista < calidad < admin)."""

    def _dep(usuario: UsuarioOut = Depends(usuario_actual)) -> UsuarioOut:
        if not auth.alcanza(usuario.rol, minimo):
            raise HTTPException(status_code=403, detail=f"Esta acción requiere el rol «{minimo}» o superior (el tuyo es «{usuario.rol}»)")
        return usuario

    return _dep


def a_http(e: Exception) -> HTTPException:
    """Traduce los errores de negocio a respuestas HTTP."""
    from app.core.pedido import ReaccionDesconocida
    from app.core.simulador import ComponenteDesconocido

    if isinstance(e, srv.NoEncontrado | ReaccionDesconocida | ComponenteDesconocido):
        return HTTPException(status_code=404, detail=str(e))
    if isinstance(e, srv.Prohibido):
        return HTTPException(status_code=403, detail=str(e))
    if isinstance(e, srv.Conflicto):
        return HTTPException(status_code=409, detail=str(e))
    return HTTPException(status_code=422, detail=str(e))
