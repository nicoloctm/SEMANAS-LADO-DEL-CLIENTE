"""
coordinador_async.py  –  Semana 3  –  Reto 4
==============================================
Implementa tres estrategias de control de flujo asíncrono:
  1. Timeout individual por petición (asyncio.wait_for)
  2. Cancelación de tareas en grupo ante error crítico (401)
  3. Carga con prioridad: mostrar dashboard parcial al llegar las tareas críticas
"""
import asyncio
import logging
import aiohttp

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_URL = "http://localhost:3000/api/"

# ─────────────────────────────────────────────────────────────────────────────
# 1. TIMEOUT INDIVIDUAL POR PETICIÓN
# ─────────────────────────────────────────────────────────────────────────────
async def _get_con_timeout(session: aiohttp.ClientSession, url: str, timeout_s: float) -> dict:
    """
    Envuelve session.get() con asyncio.wait_for para imponer un timeout
    independiente al de aiohttp. Si la petición tarda más de timeout_s,
    se lanza asyncio.TimeoutError y las DEMÁS peticiones continúan.
    """
    try:
        async with asyncio.timeout(timeout_s):
            async with session.get(url) as resp:
                if resp.status >= 400:
                    raise aiohttp.ClientResponseError(resp.request_info, resp.history, status=resp.status)
                return await resp.json()
    except asyncio.TimeoutError:
        log.warning("TIMEOUT (%.1fs) en %s", timeout_s, url)
        raise
    except aiohttp.ClientConnectorError as e:
        log.error("Servidor inalcanzable: %s", e)
        raise


async def cargar_con_timeouts_individuales() -> dict:
    """
    Cada endpoint tiene su propio timeout configurado.
    Si /categorias falla por timeout, /productos y /perfil completan normalmente.
    """
    timeouts = {
        "productos":    (f"{BASE_URL}productos",    5.0),
        "categorias":   (f"{BASE_URL}categorias",   3.0),   # ← timeout corto
        "perfil":       (f"{BASE_URL}perfil",        2.0),
    }
    async with aiohttp.ClientSession() as session:
        tareas = {
            nombre: _get_con_timeout(session, url, t)
            for nombre, (url, t) in timeouts.items()
        }
        resultados_raw = await asyncio.gather(*tareas.values(), return_exceptions=True)

    return {
        nombre: (r if not isinstance(r, Exception) else {"error": repr(r)})
        for nombre, r in zip(tareas.keys(), resultados_raw)
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. CANCELACIÓN DE TAREAS EN GRUPO
# ─────────────────────────────────────────────────────────────────────────────
async def _peticion_con_validacion_auth(session: aiohttp.ClientSession, nombre: str, url: str) -> dict:
    """Petición que propaga 401 para que el coordinador cancele las demás."""
    async with session.get(url) as resp:
        if resp.status == 401:
            raise PermissionError(f"No autorizado en {nombre} – cancelando sesión")
        if resp.status >= 400:
            raise aiohttp.ClientResponseError(resp.request_info, resp.history, status=resp.status)
        return await resp.json()


async def cargar_con_cancelacion_ante_401() -> dict:
    """
    Si /perfil responde con 401, cancela activamente las tareas pendientes
    (no tiene sentido cargar datos sin autenticación).
    """
    async with aiohttp.ClientSession() as session:
        loop = asyncio.get_running_loop()
        tareas = {
            nombre: loop.create_task(_peticion_con_validacion_auth(session, nombre, url), name=nombre)
            for nombre, url in [
                ("productos",   f"{BASE_URL}productos"),
                ("categorias",  f"{BASE_URL}categorias"),
                ("perfil",      f"{BASE_URL}perfil"),
                ("notificaciones", f"{BASE_URL}notificaciones"),
            ]
        }
        resultados: dict = {}
        errores: dict = {}

        try:
            for coro_nombre, tarea in tareas.items():
                try:
                    resultados[coro_nombre] = await tarea
                except PermissionError as e:
                    log.error("ERROR CRÍTICO: %s", e)
                    # Cancelar todas las tareas pendientes
                    for n, t in tareas.items():
                        if not t.done():
                            t.cancel()
                            log.info("Tarea '%s' cancelada.", n)
                    errores[coro_nombre] = str(e)
                    break
                except asyncio.CancelledError:
                    log.info("Tarea '%s' fue cancelada por error en otra.", coro_nombre)
                    errores[coro_nombre] = "cancelada"
                except Exception as e:
                    errores[coro_nombre] = repr(e)
        finally:
            # Asegura que todas las tareas canceladas se limpien
            for t in tareas.values():
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tareas.values(), return_exceptions=True)

    return {"datos": resultados, "errores": errores}


# ─────────────────────────────────────────────────────────────────────────────
# 3. CARGA CON PRIORIDAD (asyncio.wait)
# ─────────────────────────────────────────────────────────────────────────────
async def cargar_con_prioridad() -> dict:
    """
    Lanza 4 peticiones simultáneas. Muestra un dashboard PARCIAL en cuanto
    llegan las 2 críticas (productos + perfil). Las secundarias se procesan
    cuando lleguen.
    """
    async with aiohttp.ClientSession() as session:
        endpoints = {
            "productos":      f"{BASE_URL}productos",
            "perfil":         f"{BASE_URL}perfil",
            "categorias":     f"{BASE_URL}categorias",
            "notificaciones": f"{BASE_URL}notificaciones",
        }
        loop = asyncio.get_running_loop()
        tareas_map = {
            loop.create_task(session.get(url).__aenter__(), name=nombre): nombre
            for nombre, url in endpoints.items()
        }
        # Lanzamos con gather directo para simplicidad
        tareas_simple = {
            loop.create_task(_get_con_timeout(session, url, 10.0), name=nombre): nombre
            for nombre, url in endpoints.items()
        }
        pendientes = set(tareas_simple.keys())
        criticos_necesarios = {"productos", "perfil"}
        criticos_recibidos: set = set()
        resultado: dict = {}

        while pendientes:
            listas, pendientes = await asyncio.wait(
                pendientes,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for tarea in listas:
                nombre = tareas_simple[tarea]
                try:
                    resultado[nombre] = tarea.result()
                except Exception as e:
                    resultado[nombre] = {"error": repr(e)}

                if nombre in criticos_necesarios:
                    criticos_recibidos.add(nombre)

                if criticos_necesarios <= criticos_recibidos:
                    log.info("✅ Dashboard PARCIAL disponible con datos críticos: %s", list(criticos_recibidos))

        return resultado


# ─────────────────────────────────────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    print("\n=== 1. Timeouts Individuales ===")
    r = await cargar_con_timeouts_individuales()
    for k, v in r.items():
        print(f"  {k}: {'OK' if 'error' not in v else v}")

    print("\n=== 2. Cancelación ante 401 ===")
    r = await cargar_con_cancelacion_ante_401()
    print("  Datos:", list(r["datos"].keys()))
    print("  Errores:", r["errores"])

    print("\n=== 3. Carga con Prioridad ===")
    r = await cargar_con_prioridad()
    for k, v in r.items():
        print(f"  {k}: {'OK' if 'error' not in str(v) else v}")

if __name__ == "__main__":
    asyncio.run(main())
