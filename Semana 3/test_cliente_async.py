"""
test_cliente_async.py  –  Semana 3  –  Reto 8
===============================================
Suite de pruebas para el cliente HTTP asíncrono de EcoMarket.
Categorías: equivalencia funcional, concurrencia correcta, timeouts/cancelación,
            edge cases.

Dependencias:
    pip install pytest pytest-asyncio aioresponses

Ejecutar:
    pytest test_cliente_async.py -v
"""
import asyncio
import pytest
import pytest_asyncio
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from aioresponses import aioresponses

# ── Importamos el módulo a probar ─────────────────────────────────────────────
# Ajusta el path si es necesario
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cliente_async_ecomarket import (
    listar_productos, obtener_producto, crear_producto,
    actualizar_producto, eliminar_producto, cargar_dashboard,
    crear_multiples_productos,
    EcoMarketError, ValidationError, ServerError,
)

BASE = "http://localhost:3000/api/"

pytestmark = pytest.mark.asyncio


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 1 – Equivalencia funcional (5 tests)
# ═════════════════════════════════════════════════════════════════════════════

async def test_listar_productos_retorna_lista():
    """listar_productos debe devolver una lista de productos válida."""
    payload = [{"id": 1, "nombre": "Manzana", "precio": 1.5}]
    with aioresponses() as m:
        m.get(f"{BASE}productos", payload=payload)
        async with aiohttp.ClientSession() as session:
            resultado = await listar_productos(session)
    assert isinstance(resultado, list)
    assert resultado[0]["nombre"] == "Manzana"


async def test_obtener_producto_retorna_dict():
    """obtener_producto debe devolver un dict con la clave 'id'."""
    payload = {"id": 3, "nombre": "Pan integral", "precio": 1.2}
    with aioresponses() as m:
        m.get(f"{BASE}productos/3", payload=payload)
        async with aiohttp.ClientSession() as session:
            resultado = await obtener_producto(session, 3)
    assert resultado["id"] == 3


async def test_crear_producto_retorna_producto_creado():
    """crear_producto debe devolver el producto con id asignado."""
    nuevo = {"nombre": "Tofu", "precio": 3.0}
    respuesta = {"id": 10, "nombre": "Tofu", "precio": 3.0}
    with aioresponses() as m:
        m.post(f"{BASE}productos", payload=respuesta)
        async with aiohttp.ClientSession() as session:
            resultado = await crear_producto(session, nuevo)
    assert resultado["id"] == 10


async def test_error_4xx_lanza_ValidationError():
    """Un 404 debe lanzar ValidationError, no ServerError."""
    with aioresponses() as m:
        m.get(f"{BASE}productos/999", status=404)
        async with aiohttp.ClientSession() as session:
            with pytest.raises(ValidationError):
                await obtener_producto(session, 999)


async def test_error_5xx_lanza_ServerError():
    """Un 503 debe lanzar ServerError."""
    with aioresponses() as m:
        m.get(f"{BASE}productos", status=503)
        async with aiohttp.ClientSession() as session:
            with pytest.raises(ServerError):
                await listar_productos(session)


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 2 – Concurrencia correcta (5 tests)
# ═════════════════════════════════════════════════════════════════════════════

async def test_cargar_dashboard_tres_exitos():
    """cargar_dashboard con 3 endpoints OK y 1 con error retorna los 3 éxitos."""
    with aioresponses() as m:
        m.get(f"{BASE}productos",      payload=[{"id": 1}])
        m.get(f"{BASE}categorias",     payload=[{"id": 2}])
        m.get(f"{BASE}perfil",         payload={"usuario": "ana"})
        m.get(f"{BASE}notificaciones", status=500)     # falla intencional
        resultado = await cargar_dashboard()

    assert len(resultado["datos"]) == 3
    assert len(resultado["errores"]) == 1
    assert "notificaciones" in resultado["errores"]


async def test_gather_con_return_exceptions_no_cancela_exitosas():
    """gather con return_exceptions=True preserva los resultados exitosos."""
    with aioresponses() as m:
        m.get(f"{BASE}productos",      payload=[{"id": 1}])
        m.get(f"{BASE}categorias",     status=500)
        m.get(f"{BASE}perfil",         payload={"usuario": "bob"})
        m.get(f"{BASE}notificaciones", payload=[])
        resultado = await cargar_dashboard()

    assert "productos" in resultado["datos"]
    assert "perfil" in resultado["datos"]


async def test_eliminar_producto_retorna_true_en_204():
    """eliminar_producto con 204 debe retornar True."""
    with aioresponses() as m:
        m.delete(f"{BASE}productos/5", status=204)
        async with aiohttp.ClientSession() as session:
            ok = await eliminar_producto(session, 5)
    assert ok is True


async def test_crear_multiples_productos_con_semaforo():
    """crear_multiples_productos debe retornar (creados, fallidos) correctamente."""
    lista = [{"nombre": f"P{i}", "precio": float(i)} for i in range(6)]
    with aioresponses() as m:
        for i in range(4):
            m.post(f"{BASE}productos", payload={"id": i, "nombre": f"P{i}", "precio": float(i)})
        for i in range(4, 6):
            m.post(f"{BASE}productos", status=422)

        creados, fallidos = await crear_multiples_productos(lista)

    assert len(creados) == 4
    assert len(fallidos) == 2


async def test_actualizar_producto_retorna_datos_actualizados():
    """actualizar_producto debe retornar el producto con los nuevos datos."""
    actualizado = {"id": 1, "nombre": "Manzana Premium", "precio": 2.0}
    with aioresponses() as m:
        m.put(f"{BASE}productos/1", payload=actualizado)
        async with aiohttp.ClientSession() as session:
            resultado = await actualizar_producto(session, 1, {"precio": 2.0})
    assert resultado["precio"] == 2.0


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 3 – Timeouts y cancelación (5 tests)
# ═════════════════════════════════════════════════════════════════════════════

async def test_dashboard_completa_aunque_una_peticion_falle():
    """Si una petición falla, las demás deben completar correctamente."""
    with aioresponses() as m:
        m.get(f"{BASE}productos",      payload=[{"id": 1}])
        m.get(f"{BASE}categorias",     exception=aiohttp.ServerTimeoutError())
        m.get(f"{BASE}perfil",         payload={"usuario": "carlos"})
        m.get(f"{BASE}notificaciones", payload=[])
        resultado = await cargar_dashboard()

    assert "productos" in resultado["datos"]
    assert "perfil" in resultado["datos"]
    assert "categorias" in resultado["errores"]


async def test_session_no_queda_abierta_tras_error():
    """La sesión debe cerrarse correctamente incluso cuando hay errores."""
    with aioresponses() as m:
        m.get(f"{BASE}productos",      status=500)
        m.get(f"{BASE}categorias",     status=500)
        m.get(f"{BASE}perfil",         status=500)
        m.get(f"{BASE}notificaciones", status=500)
        # No debe levantar excepciones de resource leak
        resultado = await cargar_dashboard()

    assert len(resultado["errores"]) == 4
    assert len(resultado["datos"]) == 0


async def test_error_4xx_no_oculta_otros_resultados():
    """Un 404 en una petición no debe ocultar las respuestas exitosas de las demás."""
    with aioresponses() as m:
        m.get(f"{BASE}productos",      payload=[])
        m.get(f"{BASE}categorias",     status=404)
        m.get(f"{BASE}perfil",         payload={"usuario": "diana"})
        m.get(f"{BASE}notificaciones", payload=[])
        resultado = await cargar_dashboard()

    assert len(resultado["datos"]) == 3


async def test_error_conexion_reportado_en_errores():
    """Un error de conexión debe aparecer en resultado['errores'], no romper el dashboard."""
    with aioresponses() as m:
        m.get(f"{BASE}productos",      exception=aiohttp.ClientConnectorError(
            connection_key=MagicMock(), os_error=OSError("simulado")))
        m.get(f"{BASE}categorias",     payload=[])
        m.get(f"{BASE}perfil",         payload={"usuario": "elena"})
        m.get(f"{BASE}notificaciones", payload=[])
        resultado = await cargar_dashboard()

    assert "productos" in resultado["errores"]
    assert len(resultado["datos"]) >= 2


async def test_multiples_productos_fallidos_listados_correctamente():
    """Los productos fallidos deben incluir el dict original del producto."""
    lista = [{"nombre": "Fail1"}, {"nombre": "Fail2"}]
    with aioresponses() as m:
        m.post(f"{BASE}productos", status=500)
        m.post(f"{BASE}productos", status=500)
        creados, fallidos = await crear_multiples_productos(lista)

    assert len(creados) == 0
    assert len(fallidos) == 2
    assert fallidos[0]["producto"]["nombre"] == "Fail1"


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 4 – Edge cases de concurrencia (5 tests)
# ═════════════════════════════════════════════════════════════════════════════

async def test_todas_las_peticiones_fallan_simultaneamente():
    """Cuando todo falla, errores debe tener 4 entradas y datos debe estar vacío."""
    with aioresponses() as m:
        m.get(f"{BASE}productos",      status=503)
        m.get(f"{BASE}categorias",     status=503)
        m.get(f"{BASE}perfil",         status=503)
        m.get(f"{BASE}notificaciones", status=503)
        resultado = await cargar_dashboard()

    assert resultado["datos"] == {}
    assert len(resultado["errores"]) == 4


async def test_contenido_tipo_incorrecto_lanza_error():
    """Una respuesta sin Content-Type: application/json debe lanzar EcoMarketError."""
    with aioresponses() as m:
        m.get(f"{BASE}productos", body=b"<html>Error</html>", headers={"Content-Type": "text/html"})
        async with aiohttp.ClientSession() as session:
            with pytest.raises(EcoMarketError):
                await listar_productos(session)


async def test_dos_peticiones_mismo_endpoint_parametros_distintos():
    """Dos GET al mismo endpoint con IDs distintos deben retornar datos distintos."""
    with aioresponses() as m:
        m.get(f"{BASE}productos/1", payload={"id": 1, "nombre": "Manzana"})
        m.get(f"{BASE}productos/2", payload={"id": 2, "nombre": "Leche"})
        async with aiohttp.ClientSession() as session:
            r1, r2 = await asyncio.gather(
                obtener_producto(session, 1),
                obtener_producto(session, 2),
            )

    assert r1["nombre"] == "Manzana"
    assert r2["nombre"] == "Leche"


async def test_crear_multiples_con_lista_vacia():
    """crear_multiples_productos con lista vacía debe retornar ([], [])."""
    creados, fallidos = await crear_multiples_productos([])
    assert creados == []
    assert fallidos == []


async def test_cargar_dashboard_devuelve_estructura_correcta():
    """cargar_dashboard siempre debe retornar un dict con claves 'datos' y 'errores'."""
    with aioresponses() as m:
        m.get(f"{BASE}productos",      payload=[])
        m.get(f"{BASE}categorias",     payload=[])
        m.get(f"{BASE}perfil",         payload={})
        m.get(f"{BASE}notificaciones", payload=[])
        resultado = await cargar_dashboard()

    assert "datos" in resultado
    assert "errores" in resultado
    assert isinstance(resultado["datos"], dict)
    assert isinstance(resultado["errores"], dict)
