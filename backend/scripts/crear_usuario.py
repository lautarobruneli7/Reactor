"""Crea un usuario desde la terminal (útil para el primer administrador).

    python scripts/crear_usuario.py correo@dominio.com "Nombre Apellido" admin
    (la clave se pide sin mostrarla; también puede venir en SIM_NUEVA_CLAVE)
Usa la misma base que el servidor (SIM_DATABASE_URL). Roles: lectura, analista, calidad, admin.
"""
import getpass
import os
import sys

from app.core import auth, servicio_ensayos as srv
from app.db import datos
from app.models.ensayos import UsuarioNuevo


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    email, nombre, rol = sys.argv[1:]
    clave = os.getenv("SIM_NUEVA_CLAVE") or getpass.getpass("Clave: ")
    datos.init_datos()
    try:
        u = srv.crear_usuario(UsuarioNuevo(email=email, nombre=nombre, rol=rol, clave=clave), por=None)
    except (auth.ClaveDebil, srv.Conflicto, ValueError) as e:
        print(f"No se creó el usuario: {e}")
        return 1
    print(f"Usuario creado: {u.email} ({u.rol})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
