"""Sesión y usuarios."""
from fastapi import APIRouter, Depends, HTTPException

from app import config
from app.api.deps import a_http, requiere, usuario_actual
from app.core import auth, servicio_ensayos as srv
from app.core.propiedades import rdkit_disponible
from app.db import datos
from app.models.ensayos import LoginEntrada, LoginSalida, Sistema, UsuarioCambio, UsuarioNuevo, UsuarioOut

router = APIRouter(tags=["usuarios"])


@router.get("/sistema", response_model=Sistema)
def sistema():
    """Versión y modo de funcionamiento (sin login es de un solo usuario). No requiere sesión."""
    return Sistema(version=config.VERSION, auth_activa=config.auth_activa(), base=datos.dialecto(), rdkit=rdkit_disponible())


@router.post("/auth/login", response_model=LoginSalida)
def login(entrada: LoginEntrada):
    if not config.auth_activa():
        raise HTTPException(status_code=409, detail="El login está desactivado (modo local de un solo usuario): no hace falta iniciar sesión")
    email = entrada.email.strip().lower()
    espera = auth.LIMITE_LOGIN.bloqueado(email)
    if espera > 0:
        raise HTTPException(
            status_code=429, detail=f"Demasiados intentos fallidos. Probá de nuevo en {int(espera // 60) + 1} minuto(s).",
            headers={"Retry-After": str(int(espera) + 1)},
        )
    fila = srv.obtener_usuario_con_clave(email)
    if fila is None:
        auth.verificar_contra_nada(entrada.clave)
        ok = False
    else:
        ok = bool(fila["activo"]) and auth.verificar_clave(entrada.clave, fila["clave_hash"])
    if not ok:
        auth.LIMITE_LOGIN.fallo(email)
        srv.registrar_sesion(fila["id"] if fila else None, False, email)
        raise HTTPException(status_code=401, detail="Correo o clave incorrectos")
    auth.LIMITE_LOGIN.acierto(email)
    srv.registrar_sesion(fila["id"], True, email)
    horas = config.token_horas()
    usuario = srv.obtener_usuario(fila["id"])
    assert usuario is not None
    return LoginSalida(token=auth.emitir_token(usuario.id, config.secreto(), horas), usuario=usuario, horas=horas)


@router.get("/auth/yo", response_model=UsuarioOut)
def yo(usuario: UsuarioOut = Depends(usuario_actual)):
    return usuario


@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(_: UsuarioOut = Depends(requiere("admin"))):
    return srv.listar_usuarios()


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
def crear_usuario(nuevo: UsuarioNuevo, admin: UsuarioOut = Depends(requiere("admin"))):
    try:
        return srv.crear_usuario(nuevo, por=admin.id)
    except Exception as e:  # noqa: BLE001 - se traduce abajo
        raise a_http(e)


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioOut)
def cambiar_usuario(usuario_id: int, cambio: UsuarioCambio, admin: UsuarioOut = Depends(requiere("admin"))):
    try:
        return srv.cambiar_usuario(usuario_id, cambio, por=admin.id)
    except Exception as e:  # noqa: BLE001
        raise a_http(e)
