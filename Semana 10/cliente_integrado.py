"""
cliente_integrado.py
====================
Script de integración / demo del sistema completo.
Levanta el mock, ejecuta escenarios de prueba y muestra el resultado.

Escenarios que demuestra:
  1. Login exitoso y obtención de token
  2. Peticiones normales (circuito cerrado)
  3. Fallo del servidor → apertura del circuito
  4. Fail-fast mientras el circuito está abierto
  5. Recuperación del circuito (estado SEMIABIERTO → CERRADO)

Para ejecutarlo:
  python cliente_integrado.py
"""

import asyncio
import aiohttp

from mock_ecomarket import crear_app
from cliente_robusto import ClienteRobusto
from aiohttp import web


# ──────────────────────────────────────────
# Helpers de visualización
# ──────────────────────────────────────────
def titulo(texto):
    print(f"\n{'=' * 55}")
    print(f"  {texto}")
    print(f"{'=' * 55}")

def paso(n, texto):
    print(f"\n  [{n}] {texto}")

def ok(texto):
    print(f"      [OK] {texto}")

def fallo(texto):
    print(f"      [FAIL] {texto}")


# ──────────────────────────────────────────
# Escenarios de prueba
# ──────────────────────────────────────────
async def activar_modo_falla(activo: bool):
    async with aiohttp.ClientSession() as s:
        await s.post("http://localhost:8080/admin/modo_falla", json={"activo": activo})


async def demo(cliente: ClienteRobusto):
    titulo("DEMO - Cliente Robusto EcoMarket")

    # ── Escenario 1: Login y petición normal ──
    paso(1, "Petición normal (circuito CERRADO)")
    try:
        productos = await cliente.get("/productos")
        ok(f"Recibidos {len(productos)} productos. Circuito: {cliente.estado_circuito()}")
    except Exception as e:
        fallo(f"{e}")

    # ── Escenario 2: Forzar fallos para abrir el circuito ──
    paso(2, "Activando modo falla en el servidor...")
    await activar_modo_falla(True)

    for i in range(4):
        try:
            await cliente.get("/productos")
            ok("Petición exitosa (inesperado)")
        except Exception as e:
            fallo(f"Intento {i+1}: {type(e).__name__} - {e}")
        print(f"      Estado circuito: {cliente.estado_circuito()}")

    # ── Escenario 3: Fail-fast (circuito abierto) ──
    paso(3, "Petición con circuito ABIERTO (debe fallar rápido sin llegar al servidor)")
    try:
        await cliente.get("/productos")
        ok("Petición exitosa (inesperado)")
    except Exception as e:
        fallo(f"{type(e).__name__}: {e}")

    # ── Escenario 4: Esperar timeout y recuperación ──
    paso(4, "Desactivando modo falla y esperando timeout del circuito (6s)...")
    await activar_modo_falla(False)
    await asyncio.sleep(6)  # timeout del circuito es 5s

    try:
        productos = await cliente.get("/productos")
        ok(f"¡Recuperado! {len(productos)} productos. Circuito: {cliente.estado_circuito()}")
    except Exception as e:
        fallo(f"{type(e).__name__}: {e}")

    titulo("FIN DE LA DEMO")


# ──────────────────────────────────────────
# Arrancar mock + demo en el mismo proceso
# ──────────────────────────────────────────
async def main():
    # Levantar el mock en background
    app = crear_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()
    print("\n  Mock EcoMarket activo en http://localhost:8080")

    # Esperar un instante para que el servidor esté listo
    await asyncio.sleep(0.3)

    cliente = ClienteRobusto(base_url="http://localhost:8080", umbral=5, timeout=10)

    try:
        await demo(cliente)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
