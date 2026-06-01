"""
cliente_async_ecomarket.py  –  Semana 3
========================================
Cliente HTTP asíncrono para EcoMarket.
Convierte el cliente síncrono de Semana 2 (requests) a asíncrono (aiohttp),
conservando la misma lógica de validación y manejo de errores.

Reto 3 – Fase APLICA
"""
import asyncio
import logging
import aiohttp

# ── Configuración ────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:3000/api/"
TIMEOUT_POR_PETICION = aiohttp.ClientTimeout(total=10)
MAX_CONCURRENCIA = 5        # semáforo para creación masiva

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Excepciones (mismas que Semana 2) ────────────────────────────────────────
class EcoMarketError(Exception):
    pass

class ValidationError(EcoMarketError):
    """Error 4xx – no tiene sentido reintentar."""
    pass

class ServerError(EcoMarketError):
    """Error 5xx – podría reintentarse."""
    pass

class TimeoutError_(EcoMarketError):
    """La petición tardó más de lo permitido."""
    pass

# ── Helper interno ────────────────────────────────────────────────────────────
async def _verificar_respuesta(response: aiohttp.ClientResponse) -> dict:
    """Misma lógica de Semana 2, ahora asíncrona."""
    if response.status >= 500:
        raise ServerError(f"Error del servidor: {response.status}")
    if response.status >= 400:
        raise ValidationError(f"Error del cliente: {response.status}")
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        raise EcoMarketError(f"Respuesta no es JSON: {content_type}")
    return await response.json()

# ── Funciones CRUD asíncronas ─────────────────────────────────────────────────
async def listar_productos(session: aiohttp.ClientSession) -> list:
    async with session.get(f"{BASE_URL}productos", timeout=TIMEOUT_POR_PETICION) as resp:
        return await _verificar_respuesta(resp)

async def obtener_categorias(session: aiohttp.ClientSession) -> list:
    async with session.get(f"{BASE_URL}categorias", timeout=TIMEOUT_POR_PETICION) as resp:
        return await _verificar_respuesta(resp)

async def obtener_perfil(session: aiohttp.ClientSession) -> dict:
    async with session.get(f"{BASE_URL}perfil", timeout=TIMEOUT_POR_PETICION) as resp:
        return await _verificar_respuesta(resp)

async def obtener_notificaciones(session: aiohttp.ClientSession) -> list:
    async with session.get(f"{BASE_URL}notificaciones", timeout=TIMEOUT_POR_PETICION) as resp:
        return await _verificar_respuesta(resp)

async def obtener_producto(session: aiohttp.ClientSession, id_prod: int) -> dict:
    async with session.get(f"{BASE_URL}productos/{id_prod}", timeout=TIMEOUT_POR_PETICION) as resp:
        return await _verificar_respuesta(resp)

async def crear_producto(session: aiohttp.ClientSession, producto: dict) -> dict:
    async with session.post(f"{BASE_URL}productos", json=producto, timeout=TIMEOUT_POR_PETICION) as resp:
        return await _verificar_respuesta(resp)

async def actualizar_producto(session: aiohttp.ClientSession, id_prod: int, datos: dict) -> dict:
    async with session.put(f"{BASE_URL}productos/{id_prod}", json=datos, timeout=TIMEOUT_POR_PETICION) as resp:
        return await _verificar_respuesta(resp)

async def eliminar_producto(session: aiohttp.ClientSession, id_prod: int) -> bool:
    async with session.delete(f"{BASE_URL}productos/{id_prod}", timeout=TIMEOUT_POR_PETICION) as resp:
        if resp.status == 204:
            return True
        await _verificar_respuesta(resp)
        return False

# ── cargar_dashboard ──────────────────────────────────────────────────────────
async def cargar_dashboard() -> dict:
    """
    Carga simultáneamente productos, categorías, perfil y notificaciones.
    Una sola ClientSession. return_exceptions=True para no perder éxitos
    si una petición falla.
    """
    async with aiohttp.ClientSession() as session:
        resultados = await asyncio.gather(
            listar_productos(session),
            obtener_categorias(session),
            obtener_perfil(session),
            obtener_notificaciones(session),
            return_exceptions=True,   # ← invariante crítico
        )

    claves = ["productos", "categorias", "perfil", "notificaciones"]
    dashboard: dict = {}
    errores: dict = {}

    for clave, resultado in zip(claves, resultados):
        if isinstance(resultado, Exception):
            errores[clave] = repr(resultado)
            log.warning("Falla al cargar '%s': %s", clave, resultado)
        else:
            dashboard[clave] = resultado

    log.info("Dashboard: %d éxitos, %d errores", len(dashboard), len(errores))
    return {"datos": dashboard, "errores": errores}

# ── crear_multiples_productos ─────────────────────────────────────────────────
async def crear_multiples_productos(lista_productos: list) -> tuple[list, list]:
    """
    Crea todos los productos en paralelo, limitando a MAX_CONCURRENCIA
    peticiones simultáneas mediante un asyncio.Semaphore.
    Retorna (productos_creados, productos_fallidos).
    """
    semaforo = asyncio.Semaphore(MAX_CONCURRENCIA)

    async def _crear_con_semaforo(session: aiohttp.ClientSession, producto: dict):
        async with semaforo:
            log.debug("Creando producto: %s", producto.get("nombre", "?"))
            return await crear_producto(session, producto)

    async with aiohttp.ClientSession() as session:
        tareas = [_crear_con_semaforo(session, p) for p in lista_productos]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)

    creados = []
    fallidos = []
    for producto, resultado in zip(lista_productos, resultados):
        if isinstance(resultado, Exception):
            fallidos.append({"producto": producto, "error": repr(resultado)})
        else:
            creados.append(resultado)

    log.info("Creación masiva: %d éxitos, %d fallos", len(creados), len(fallidos))
    return creados, fallidos

# ── Punto de entrada ──────────────────────────────────────────────────────────
async def main():
    import time
    t0 = time.time()
    resultado = await cargar_dashboard()
    t1 = time.time()
    print(f"\nDashboard cargado en {t1-t0:.2f}s")
    print("Secciones cargadas:", list(resultado["datos"].keys()))
    if resultado["errores"]:
        print("Errores:", resultado["errores"])

if __name__ == "__main__":
    asyncio.run(main())
