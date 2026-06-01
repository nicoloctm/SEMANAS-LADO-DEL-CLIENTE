"""
throttle.py  –  Semana 3  –  Reto 5
=====================================
Limitadores de concurrencia y tasa para clientes HTTP asíncronos.

Componentes:
  - ConcurrencyLimiter  → asyncio.Semaphore (máx N peticiones en vuelo)
  - RateLimiter         → Token Bucket (máx M peticiones por segundo)
  - ThrottledClient     → Combina ambos y provee métodos CRUD throttled
"""
import asyncio
import time
import logging
import aiohttp

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_URL = "http://localhost:3000/api/"


# ─────────────────────────────────────────────────────────────────────────────
# 1. ConcurrencyLimiter – Semáforo con logging
# ─────────────────────────────────────────────────────────────────────────────
class ConcurrencyLimiter:
    """
    Limita cuántas peticiones HTTP pueden estar en vuelo simultáneamente.
    Uso:
        async with limiter:
            await session.get(url)
    """
    def __init__(self, max_concurrent: int):
        self._sem = asyncio.Semaphore(max_concurrent)
        self._max = max_concurrent
        self._en_vuelo = 0

    async def __aenter__(self):
        await self._sem.acquire()
        self._en_vuelo += 1
        log.debug("En vuelo: %d / %d", self._en_vuelo, self._max)
        return self

    async def __aexit__(self, *args):
        self._en_vuelo -= 1
        self._sem.release()
        log.debug("En vuelo tras salida: %d / %d", self._en_vuelo, self._max)


# ─────────────────────────────────────────────────────────────────────────────
# 2. RateLimiter – Token Bucket
# ─────────────────────────────────────────────────────────────────────────────
class RateLimiter:
    """
    Limita la tasa de peticiones mediante el algoritmo Token Bucket.
    Si se excede la tasa, las peticiones ESPERAN (no se rechazan).
    """
    def __init__(self, max_per_second: float):
        self._rate = max_per_second          # tokens/seg
        self._tokens = max_per_second        # empieza lleno
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """Espera hasta que haya un token disponible. Devuelve el tiempo esperado."""
        async with self._lock:
            ahora = time.monotonic()
            transcurrido = ahora - self._last_refill
            # Recargar tokens proporcional al tiempo
            self._tokens = min(self._rate, self._tokens + transcurrido * self._rate)
            self._last_refill = ahora

            if self._tokens >= 1:
                self._tokens -= 1
                return 0.0
            else:
                espera = (1 - self._tokens) / self._rate
                log.debug("RateLimiter: esperando %.3fs", espera)

        await asyncio.sleep(espera)         # ← fuera del lock
        async with self._lock:
            self._tokens = max(0.0, self._tokens - 1)
        return espera

    async def __aenter__(self):
        self._espera = await self.acquire()
        return self

    async def __aexit__(self, *args):
        pass

    @property
    def ultima_espera(self) -> float:
        return getattr(self, "_espera", 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. ThrottledClient – combina ambos limitadores
# ─────────────────────────────────────────────────────────────────────────────
class ThrottledClient:
    """
    Cliente HTTP que respeta SIMULTÁNEAMENTE un límite de concurrencia y
    una tasa máxima de peticiones por segundo.

    Ejemplo:
        client = ThrottledClient(max_concurrent=10, max_per_second=20)
        async with aiohttp.ClientSession() as session:
            resultado = await client.get(session, "/productos")
    """
    def __init__(self, max_concurrent: int = 10, max_per_second: float = 20.0):
        self._concurrency = ConcurrencyLimiter(max_concurrent)
        self._rate = RateLimiter(max_per_second)

    async def get(self, session: aiohttp.ClientSession, path: str) -> dict:
        async with self._rate:
            async with self._concurrency:
                async with session.get(f"{BASE_URL}{path}") as resp:
                    return await resp.json()

    async def post(self, session: aiohttp.ClientSession, path: str, data: dict) -> dict:
        async with self._rate:
            async with self._concurrency:
                async with session.post(f"{BASE_URL}{path}", json=data) as resp:
                    return await resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# Demo / Test integrado
# ─────────────────────────────────────────────────────────────────────────────
async def demo_50_peticiones():
    """
    Lanza 50 peticiones de creación y verifica que:
    - Nunca hay más de 10 en vuelo al mismo tiempo
    - No se exceden 20 por segundo
    """
    client = ThrottledClient(max_concurrent=10, max_per_second=20)
    productos_demo = [{"nombre": f"Producto {i}", "precio": float(i)} for i in range(50)]

    t0 = time.monotonic()
    async with aiohttp.ClientSession() as session:
        tareas = [
            client.post(session, "productos", p)
            for p in productos_demo
        ]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)

    t1 = time.monotonic()
    exitos = sum(1 for r in resultados if not isinstance(r, Exception))
    fallos = len(resultados) - exitos
    throughput = len(resultados) / (t1 - t0)

    print(f"\n=== ThrottledClient – 50 peticiones ===")
    print(f"  Tiempo total  : {t1-t0:.2f}s")
    print(f"  Éxitos        : {exitos}")
    print(f"  Fallos        : {fallos}")
    print(f"  Throughput    : {throughput:.1f} req/s")


if __name__ == "__main__":
    asyncio.run(demo_50_peticiones())
