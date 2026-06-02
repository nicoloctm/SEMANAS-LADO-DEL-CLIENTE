"""
mock_ecomarket.py
=================
Servidor falso (mock) de EcoMarket para pruebas locales.
Simula endpoints de autenticación y de productos con fallas controladas.

Endpoints disponibles:
  POST /auth/login           → Devuelve un JWT de prueba
  GET  /productos            → Lista de productos (puede fallar)
  GET  /productos/{id}       → Producto específico
  POST /admin/modo_falla     → Activa/desactiva el modo de falla del servidor
"""

import asyncio
import json
import time
import base64
from aiohttp import web

# ──────────────────────────────────────────
# Estado interno del mock
# ──────────────────────────────────────────
_modo_falla = False   # Si True, los endpoints devuelven 500
_fallas_consecutivas = 0

PRODUCTOS = [
    {"id": 1, "nombre": "Manzana orgánica", "precio": 1.50, "stock": 200},
    {"id": 2, "nombre": "Leche de avena",   "precio": 2.80, "stock": 50},
    {"id": 3, "nombre": "Pan integral",      "precio": 1.20, "stock": 100},
]


# ──────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────
def _crear_jwt_falso(username: str, segundos_vigencia: int = 30) -> str:
    """
    Crea un JWT falso con estructura válida para que el TokenManager
    pueda decodificarlo y calcular la expiración (campo 'exp').
    NO usa firma real; solo es para pruebas locales.
    """
    header  = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b'=').decode()
    exp     = int(time.time()) + segundos_vigencia
    payload = json.dumps({"sub": username, "exp": exp}).encode()
    payload_b64 = base64.urlsafe_b64encode(payload).rstrip(b'=').decode()
    return f"{header}.{payload_b64}.signature_falsa"


# ──────────────────────────────────────────
# Handlers (manejadores de rutas)
# ──────────────────────────────────────────
async def login(request):
    """POST /auth/login → Devuelve tokens de acceso y refresco."""
    data = await request.json()
    username = data.get("username", "anonimo")
    access_token  = _crear_jwt_falso(username, segundos_vigencia=30)
    refresh_token = _crear_jwt_falso(username, segundos_vigencia=3600)
    print(f"  [mock] /auth/login <- usuario='{username}' -> token emitido")
    return web.json_response({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "Bearer",
    })


async def get_productos(request):
    """GET /productos → Lista todos los productos (falla si modo_falla activo)."""
    global _modo_falla
    if _modo_falla:
        print("  [mock] /productos -> 500 (modo falla activo)")
        return web.json_response({"error": "Servidor no disponible"}, status=500)
    print("  [mock] /productos -> 200 OK")
    return web.json_response(PRODUCTOS)


async def get_producto(request):
    """GET /productos/{id} → Producto por ID."""
    global _modo_falla
    if _modo_falla:
        print("  [mock] /productos/{id} -> 500 (modo falla activo)")
        return web.json_response({"error": "Servidor no disponible"}, status=500)
    pid = int(request.match_info["id"])
    producto = next((p for p in PRODUCTOS if p["id"] == pid), None)
    if not producto:
        return web.json_response({"error": "No encontrado"}, status=404)
    print(f"  [mock] /productos/{pid} -> 200 OK")
    return web.json_response(producto)


async def set_modo_falla(request):
    """POST /admin/modo_falla → Activa o desactiva el modo de falla. Body: {"activo": true/false}"""
    global _modo_falla
    data = await request.json()
    _modo_falla = bool(data.get("activo", False))
    estado = "ACTIVADO" if _modo_falla else "DESACTIVADO"
    print(f"  [mock] /admin/modo_falla -> modo falla {estado}")
    return web.json_response({"modo_falla": _modo_falla, "estado": estado})


# ──────────────────────────────────────────
# Configuración y arranque del servidor
# ──────────────────────────────────────────
def crear_app():
    app = web.Application()
    app.router.add_post("/auth/login",        login)
    app.router.add_get( "/productos",         get_productos)
    app.router.add_get( "/productos/{id}",    get_producto)
    app.router.add_post("/admin/modo_falla",  set_modo_falla)
    return app


if __name__ == "__main__":
    print("=" * 50)
    print(" Mock EcoMarket corriendo en http://localhost:8080")
    print(" Endpoints:")
    print("   POST /auth/login")
    print("   GET  /productos")
    print("   GET  /productos/{id}")
    print("   POST /admin/modo_falla")
    print("=" * 50)
    web.run_app(crear_app(), host="localhost", port=8080)
