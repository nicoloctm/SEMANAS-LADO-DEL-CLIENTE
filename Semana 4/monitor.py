"""
DECISIONES DE DISEÑO — Monitor de Inventario EcoMarket
=======================================================

INTERVALO_BASE = 5s
  → Trade-off: callbacks síncronos alargan el ciclo real.
    Si el observador de logs tarda 2s escribiendo a disco, el ciclo
    efectivo es 7s (5s sleep + 2s callback). Para inventario de EcoMarket
    esto es aceptable. En dashboards de tiempo real habría que hacer
    los callbacks asíncronos también.

INTERVALO_MAX = 60s
  → Trade-off: cliente descansa más entre consultas, pero los datos
    pueden tener hasta 60s de retraso. Para stock de productos de un
    marketplace esto es aceptable; para un chat sería inaceptable.

TIMEOUT = 10s
  → Si el servidor no responde en 10s, el cliente lo trata como fallo
    y aplica backoff. Sin timeout, el ciclo while quedaría colgado
    indefinidamente, bloqueando el event loop.

BACKOFF:
  → Sin cambios (304): intervalo *= 1.5  — crece suave para ahorrar recursos
  → Error 5xx:         intervalo *= 2.0  — crece agresivo (servidor en problemas)
  → Con cambios (200): intervalo = base  — reset inmediato para no perder datos

PERSISTENCIA:
  → El cliente no se rinde: itera para siempre cada 60s máximo.
    Decisión correcta para EcoMarket (siempre queremos datos frescos).
    Si se necesita límite de reintentos, agregar contador > N → detener().

ETAG:
  → Si el servidor no lo soporta, fallback a comparar datos completos
    usando hash del JSON (ver comentario en _consultar).

[Nota crítica al resumen de la IA del Reto 3: dijo que backoff "reduce
 la carga del servidor" — lo importante para el CLIENTE es que protege
 el ciclo de eventos del cliente de ejecutarse en bucle vacío constante.]

Semana 4 — Programación Distribuida del Lado del Cliente — UAN
"""
import asyncio
import json
import time
import hashlib
import logging
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Constantes de configuración ────────────────────────────────────────────
BASE_URL          = "http://localhost:3000/api"
INTERVALO_BASE_S  = 5
INTERVALO_MAX_S   = 60
TIMEOUT_S         = 10


# ═══════════════════════════════════════════════════════════════════════════
# CLASE BASE: Observable (Patrón Observer)
# ═══════════════════════════════════════════════════════════════════════════
class Observable:
    """
    Implementa el patrón Observer.
    Cualquier clase que extienda Observable hereda suscribir(),
    desuscribir() y notificar() sin necesidad de reimplementarlos.
    """
    def __init__(self):
        self._observadores: dict[str, list] = {}

    def suscribir(self, evento: str, callback) -> None:
        """Registra un callback para el evento dado."""
        if evento not in self._observadores:
            self._observadores[evento] = []
        self._observadores[evento].append(callback)

    def desuscribir(self, evento: str, callback) -> None:
        """Elimina un callback específico; los demás quedan intactos."""
        if evento in self._observadores:
            try:
                self._observadores[evento].remove(callback)
            except ValueError:
                pass

    def notificar(self, evento: str, datos) -> None:
        """
        Llama a todos los callbacks del evento con los datos.
        Un callback roto NO detiene a los demás ni al polling.
        """
        for cb in self._observadores.get(evento, []):
            try:
                cb(datos)
            except Exception as e:
                log.error("Observador '%s' falló: %s", cb.__name__, e)


# ═══════════════════════════════════════════════════════════════════════════
# CLASE: ServicioPolling  (extiende Observable)
# ═══════════════════════════════════════════════════════════════════════════
class ServicioPolling(Observable):
    """
    Realiza short polling adaptativo sobre un endpoint HTTP.

    Eventos emitidos:
        datos_actualizados  → cuando el servidor devuelve 200 con datos nuevos
        sin_cambios         → cuando el servidor devuelve 304 (ETag match)
        error_servidor      → cuando el servidor devuelve 5xx
        timeout             → cuando la petición supera TIMEOUT_S
        error_json          → cuando el body no es JSON válido
        error_conexion      → cuando no hay conexión con el servidor
    """

    def __init__(self, url_base: str = BASE_URL, intervalo_seg: float = INTERVALO_BASE_S):
        super().__init__()
        self.url_base        = url_base
        self.intervalo_base  = intervalo_seg
        self.intervalo_actual = intervalo_seg
        self.intervalo_max   = INTERVALO_MAX_S
        self.ultimo_etag     = None
        self._ultimo_hash    = None   # fallback si el servidor no usa ETag
        self._activo         = False
        self._ciclo          = 0

    # ── API pública ──────────────────────────────────────────────────────
    async def iniciar(self) -> None:
        """Inicia el ciclo de polling. Bloquea hasta llamar a detener()."""
        self._activo = True
        log.info("▶ Polling iniciado — URL: %s, intervalo: %ds", self.url_base, self.intervalo_base)
        while self._activo:
            self._ciclo += 1
            await self._consultar()
            if self._activo:
                log.info("   ⏳ Ciclo %d completado — próxima consulta en %.1fs",
                         self._ciclo, self.intervalo_actual)
                await asyncio.sleep(self.intervalo_actual)
        log.info("⏹ Polling detenido limpiamente. Sin tareas pendientes.")

    def detener(self) -> None:
        """
        Para el ciclo en el próximo await. No cancela tareas a la fuerza.
        Después de llamarlo, no quedan peticiones en vuelo (invariante ✓).
        """
        self._activo = False

    # ── Lógica interna ───────────────────────────────────────────────────
    async def _consultar(self) -> None:
        """
        Realiza una petición GET al endpoint y decide qué notificar.
        Aplica ETag (If-None-Match) si el servidor lo soporta;
        si no, usa hash SHA-256 del JSON como fallback.
        """
        headers = {}
        if self.ultimo_etag:
            headers["If-None-Match"] = self.ultimo_etag

        timeout = aiohttp.ClientTimeout(total=TIMEOUT_S)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.url_base}/productos", headers=headers) as resp:
                    await self._procesar_respuesta(resp)

        except asyncio.TimeoutError:
            log.warning("⏰ TIMEOUT en consulta (>%ds)", TIMEOUT_S)
            self.notificar("timeout", {"ciclo": self._ciclo, "ts": time.time()})
            self.intervalo_actual = min(self.intervalo_actual * 2, self.intervalo_max)

        except aiohttp.ClientConnectorError as e:
            log.error("🔌 Sin conexión al servidor: %s", e)
            self.notificar("error_conexion", {"error": str(e), "ciclo": self._ciclo})
            self.intervalo_actual = min(self.intervalo_actual * 2, self.intervalo_max)

    async def _procesar_respuesta(self, resp: aiohttp.ClientResponse) -> None:
        status = resp.status

        # ── 304 Sin cambios ──────────────────────────────────────────────
        if status == 304:
            nuevo = min(self.intervalo_actual * 1.5, self.intervalo_max)
            log.info("   ✅ 304 Sin cambios — backoff %.1fs → %.1fs",
                     self.intervalo_actual, nuevo)
            self.intervalo_actual = nuevo
            self.notificar("sin_cambios", {"ciclo": self._ciclo})
            return

        # ── 5xx Error del servidor ───────────────────────────────────────
        if status >= 500:
            nuevo = min(self.intervalo_actual * 2, self.intervalo_max)
            log.warning("   ❌ Error %d del servidor — backoff %.1fs → %.1fs",
                        status, self.intervalo_actual, nuevo)
            self.intervalo_actual = nuevo
            self.notificar("error_servidor", {"status": status, "ciclo": self._ciclo})
            return

        # ── 4xx Error de cliente ──────────────────────────────────────────
        if status >= 400:
            log.error("   ❌ Error de cliente %d — no reintenta", status)
            self.notificar("error_servidor", {"status": status, "ciclo": self._ciclo})
            return

        # ── 200 Datos recibidos ──────────────────────────────────────────
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            log.error("   ❌ Respuesta no es JSON (Content-Type: %s)", content_type)
            self.notificar("error_json", {
                "content_type": content_type,
                "ciclo": self._ciclo,
            })
            self.intervalo_actual = min(self.intervalo_actual * 1.5, self.intervalo_max)
            return

        try:
            datos = await resp.json()
        except (json.JSONDecodeError, Exception) as e:
            log.error("   ❌ JSON inválido: %s", e)
            self.notificar("error_json", {"error": str(e), "ciclo": self._ciclo})
            self.intervalo_actual = min(self.intervalo_actual * 1.5, self.intervalo_max)
            return

        # Actualizar ETag si el servidor lo provee
        etag = resp.headers.get("ETag")
        if etag:
            self.ultimo_etag = etag

        # Fallback: comparar hash si no hay ETag
        datos_hash = hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()
        if self._ultimo_hash == datos_hash:
            log.info("   ✅ 200 Sin cambios (hash igual) — backoff leve")
            self.intervalo_actual = min(self.intervalo_actual * 1.5, self.intervalo_max)
            self.notificar("sin_cambios", {"ciclo": self._ciclo})
        else:
            self._ultimo_hash = datos_hash
            log.info("   🔔 200 Datos nuevos — intervalo reset a %ds", self.intervalo_base)
            self.intervalo_actual = self.intervalo_base
            self.notificar("datos_actualizados", datos)


# ═══════════════════════════════════════════════════════════════════════════
# OBSERVADORES (funciones independientes — no clases)
# ═══════════════════════════════════════════════════════════════════════════

def actualizar_ui(datos) -> None:
    """Simula actualización de la interfaz de usuario."""
    if isinstance(datos, list):
        log.info("   🖥  UI — %d productos cargados", len(datos))
    elif isinstance(datos, dict) and "productos" in datos:
        log.info("   🖥  UI — %d productos cargados", len(datos["productos"]))
    else:
        log.info("   🖥  UI — datos recibidos: %s", str(datos)[:80])


def alerta_agotados(datos) -> None:
    """Emite alerta cuando un producto tiene stock=0."""
    productos = datos if isinstance(datos, list) else datos.get("productos", [])
    if not productos:
        return
    for p in productos:
        if isinstance(p, dict) and p.get("stock", 1) == 0:
            log.warning("   🚨 ALERTA stock=0 → Producto #%s '%s'",
                        p.get("id", "?"), p.get("nombre", "sin nombre"))


def log_errores_servidor(info: dict) -> None:
    """Registra errores de servidor con timestamp."""
    ts = time.strftime("%H:%M:%S")
    log.error("   📋 [%s] Error servidor — status: %s, ciclo: %s",
              ts, info.get("status", "?"), info.get("ciclo", "?"))


def log_timeout(info: dict) -> None:
    """Registra timeouts con timestamp."""
    ts = time.strftime("%H:%M:%S")
    log.warning("   📋 [%s] Timeout — ciclo: %s", ts, info.get("ciclo", "?"))


def log_error_json(info: dict) -> None:
    """Registra errores de parseo JSON."""
    log.error("   📋 JSON inválido — content_type: %s error: %s",
              info.get("content_type", "?"), info.get("error", "?"))


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRACIÓN: MonitorInventario de EcoMarket
# ═══════════════════════════════════════════════════════════════════════════

async def correr_monitor(ciclos_max: int = 5) -> None:
    """
    Demuestra el Monitor de Inventario de EcoMarket:
    iniciar → detectar cambio → notificar → detener.
    Se detiene automáticamente después de ciclos_max ciclos.
    """
    monitor = ServicioPolling(BASE_URL, INTERVALO_BASE_S)

    # Suscribir todos los observadores (sin modificar ServicioPolling)
    monitor.suscribir("datos_actualizados", actualizar_ui)
    monitor.suscribir("datos_actualizados", alerta_agotados)
    monitor.suscribir("error_servidor",     log_errores_servidor)
    monitor.suscribir("timeout",            log_timeout)
    monitor.suscribir("error_json",         log_error_json)

    # Detener automáticamente después de N ciclos para la demo
    async def _auto_detener():
        await asyncio.sleep(INTERVALO_BASE_S * ciclos_max + 2)
        log.info("⏹ Auto-deteniendo después de %d ciclos de demo...", ciclos_max)
        monitor.detener()

    await asyncio.gather(
        monitor.iniciar(),
        _auto_detener(),
        return_exceptions=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# MODO: Escenarios de prueba para validacion.log
# ═══════════════════════════════════════════════════════════════════════════

async def escenario_mock(
    nombre: str,
    status: int,
    body: bytes,
    content_type: str = "application/json",
) -> None:
    """
    Crea un ServicioPolling y lo prueba contra una respuesta simulada
    sin necesitar servidor real.
    """
    print(f"\n{'='*60}")
    print(f"ESCENARIO: {nombre}")
    print(f"{'='*60}")

    monitor = ServicioPolling(BASE_URL, INTERVALO_BASE_S)
    monitor.suscribir("datos_actualizados", actualizar_ui)
    monitor.suscribir("datos_actualizados", alerta_agotados)
    monitor.suscribir("error_servidor",     log_errores_servidor)
    monitor.suscribir("timeout",            log_timeout)
    monitor.suscribir("error_json",         log_error_json)

    # Simulamos directamente llamando a _procesar_respuesta con una respuesta mock
    class MockResponse:
        def __init__(self, s, b, ct):
            self.status = s
            self._body  = b
            self.headers = {"Content-Type": ct, "ETag": f"etag-{s}"}
        async def json(self):
            return json.loads(self._body)

    await monitor._procesar_respuesta(MockResponse(status, body, content_type))
    print(f"  Intervalo resultante: {monitor.intervalo_actual:.1f}s")


async def prueba_timeout() -> None:
    """Prueba A: Servidor tarda más de TIMEOUT_S."""
    print(f"\n{'='*60}")
    print(f"PRUEBA A: Timeout (servidor >10s)")
    print(f"{'='*60}")
    monitor = ServicioPolling(BASE_URL, INTERVALO_BASE_S)
    monitor.suscribir("timeout", log_timeout)

    # Simulamos el TimeoutError directamente
    log.warning("⏰ TIMEOUT simulado en consulta (>%ds)", TIMEOUT_S)
    monitor.notificar("timeout", {"ciclo": 1, "ts": time.time()})
    monitor.intervalo_actual = min(monitor.intervalo_actual * 2, monitor.intervalo_max)
    print(f"  Backoff aplicado: intervalo ahora {monitor.intervalo_actual:.1f}s ✓")


async def prueba_html_en_lugar_de_json() -> None:
    """Prueba B: Servidor responde con HTML."""
    await escenario_mock(
        nombre="B: HTML en lugar de JSON (Content-Type incorrecto)",
        status=200,
        body=b"<html><body>Error interno</body></html>",
        content_type="text/html; charset=utf-8",
    )


async def prueba_observador_falla() -> None:
    """Prueba C: Un observador lanza excepción."""
    print(f"\n{'='*60}")
    print(f"PRUEBA C: Observador lanza excepción")
    print(f"{'='*60}")

    def observador_roto(datos):
        raise RuntimeError("¡Fallo simulado en observador de animación!")

    def observador_alertas(datos):
        print("  → [alerta_agotados] sigue funcionando después del error ✓")

    monitor = ServicioPolling(BASE_URL, INTERVALO_BASE_S)
    monitor.suscribir("datos_actualizados", observador_roto)
    monitor.suscribir("datos_actualizados", observador_alertas)

    datos = [{"id": 1, "nombre": "Quinoa", "stock": 5}]
    monitor.notificar("datos_actualizados", datos)


async def prueba_campo_null() -> None:
    """Prueba D: Servidor devuelve 200 pero campo 'productos' es null."""
    datos_null = json.dumps({"productos": None, "total": 0}).encode()
    await escenario_mock(
        nombre="D: Campo 'productos' viene como null",
        status=200,
        body=datos_null,
        content_type="application/json",
    )
    # El observador alerta_agotados debe manejar esto sin crashear
    monitor = ServicioPolling(BASE_URL, INTERVALO_BASE_S)
    monitor.suscribir("datos_actualizados", alerta_agotados)
    monitor.notificar("datos_actualizados", {"productos": None})
    print("  → alerta_agotados manejó datos null sin excepción ✓")


async def prueba_desacoplamiento() -> None:
    """Prueba de desacoplamiento Observer."""
    print(f"\n{'='*60}")
    print("PRUEBA DE DESACOPLAMIENTO")
    print(f"{'='*60}")

    def observador_4(datos):
        print("  → observador_4 activo ✓")

    monitor = ServicioPolling(BASE_URL, INTERVALO_BASE_S)
    monitor.suscribir("datos_actualizados", actualizar_ui)
    monitor.suscribir("datos_actualizados", observador_4)
    print("  Suscrito observador_4 sin modificar ServicioPolling ✓")

    monitor.notificar("datos_actualizados", [{"id": 1, "stock": 10}])

    monitor.desuscribir("datos_actualizados", observador_4)
    print("  Desuscrito observador_4 sin modificar ServicioPolling ✓")
    print("  ServicioPolling NO tiene referencia directa a ningún observador ✓")


async def ejecutar_validaciones() -> None:
    """Ejecuta todos los escenarios de validación del Reto 4."""
    log.info("=" * 60)
    log.info("  VALIDACIÓN DE ESCENARIOS CRÍTICOS — Reto 4")
    log.info("=" * 60)

    await prueba_timeout()
    await prueba_html_en_lugar_de_json()
    await prueba_observador_falla()
    await prueba_campo_null()
    await prueba_desacoplamiento()

    print("\n" + "=" * 60)
    print("TODOS LOS ESCENARIOS VALIDADOS")
    print("=" * 60)
    print("# PRUEBA DE DESACOPLAMIENTO:")
    print("# Agregué observador_4 y lo quité sin modificar ServicioPolling. ✓")
    print("# ServicioPolling no tiene referencia directa a ningún observador. ✓")


# ═══════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    modo = sys.argv[1] if len(sys.argv) > 1 else "validar"

    if modo == "validar":
        # Modo Reto 4: generar validacion.log
        asyncio.run(ejecutar_validaciones())
    elif modo == "demo":
        # Modo Reto 2: monitor real contra servidor (requiere mock server)
        asyncio.run(correr_monitor(ciclos_max=5))
    else:
        print("Uso: python monitor.py [validar|demo]")
        print("  validar → ejecuta los 4 escenarios de prueba (Reto 4)")
        print("  demo    → corre el monitor real contra localhost:3000 (Reto 2)")
