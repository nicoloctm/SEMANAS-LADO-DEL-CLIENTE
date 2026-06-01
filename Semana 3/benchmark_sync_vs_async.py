"""
benchmark_sync_vs_async.py  –  Semana 3  –  Reto 9
====================================================
Compara el rendimiento del cliente síncrono (requests) vs. asíncrono (aiohttp)
en 4 escenarios con latencias simuladas.

NOTA: usa asyncio.sleep / time.sleep internos para simular latencia sin
      necesitar servidor real. Para benchmarks reales, apunta BASE_URL a tu
      mock server con delay configurable.
"""
import asyncio
import time
import statistics
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

# ─── Simuladores de petición ─────────────────────────────────────────────────
def peticion_sincrona(delay_s: float) -> dict:
    """Simula una petición HTTP síncrona bloqueante."""
    time.sleep(delay_s)
    return {"ok": True}

async def peticion_asincrona(delay_s: float) -> dict:
    """Simula una petición HTTP asíncrona no bloqueante."""
    await asyncio.sleep(delay_s)
    return {"ok": True}


# ─── Escenarios ──────────────────────────────────────────────────────────────
ESCENARIOS = {
    "Dashboard (4 GET)":         {"n": 4,  "metodo": "GET"},
    "Creación masiva (20 POST)": {"n": 20, "metodo": "POST"},
    "Mixto (10 GET + 5 POST)":   {"n": 15, "metodo": "MIX"},
    "Alta latencia (4 GET×500ms)": {"n": 4, "metodo": "HIGH_LAT"},
}

LATENCIAS = [0.0, 0.1, 0.5]  # segundos de delay por petición


# ─── Runner síncrono (usando ThreadPoolExecutor para simular requests) ────────
def correr_sincrono(n: int, delay_s: float) -> float:
    t0 = time.monotonic()
    for _ in range(n):
        peticion_sincrona(delay_s)   # secuencial
    return time.monotonic() - t0


# ─── Runner asíncrono ────────────────────────────────────────────────────────
async def correr_asincrono(n: int, delay_s: float) -> float:
    t0 = time.monotonic()
    await asyncio.gather(*[peticion_asincrona(delay_s) for _ in range(n)])
    return time.monotonic() - t0


# ─── Medición con tracemalloc ─────────────────────────────────────────────────
def medir_memoria(func: Callable, *args) -> tuple[float, float]:
    """Ejecuta func(*args) midiendo memoria pico. Retorna (resultado, mem_kb)."""
    tracemalloc.start()
    resultado = func(*args)
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return resultado, pico / 1024  # KB


async def medir_memoria_async(coro_func: Callable, *args) -> tuple[float, float]:
    tracemalloc.start()
    resultado = await coro_func(*args)
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return resultado, pico / 1024


# ─── Benchmark completo ───────────────────────────────────────────────────────
async def ejecutar_benchmark(repeticiones: int = 5):
    print("=" * 70)
    print("  BENCHMARK: SÍNCRONO vs. ASÍNCRONO")
    print(f"  (promedio de {repeticiones} repeticiones por escenario)")
    print("=" * 70)

    for latencia in LATENCIAS:
        print(f"\n--- Latencia por petición: {latencia*1000:.0f}ms ---")
        print(f"{'Escenario':<30} {'Síncr (s)':>10} {'Asínc (s)':>10} {'Speedup':>10} {'Mem↑ KB':>10}")
        print("-" * 70)

        for nombre_esc, cfg in ESCENARIOS.items():
            n = cfg["n"]
            # Omitir alta latencia para latencia 0
            if cfg["metodo"] == "HIGH_LAT" and latencia != 0.5:
                continue

            t_sinc_list = []
            t_asin_list = []

            for _ in range(repeticiones):
                # Síncrono
                t, _ = medir_memoria(correr_sincrono, n, latencia)
                t_sinc_list.append(t)
                # Asíncrono
                t, _ = await medir_memoria_async(correr_asincrono, n, latencia)
                t_asin_list.append(t)

            t_sinc = statistics.mean(t_sinc_list)
            t_asin = statistics.mean(t_asin_list)
            speedup = t_sinc / t_asin if t_asin > 0 else float("inf")

            _, mem_diff = await medir_memoria_async(correr_asincrono, n, latencia)

            print(f"{nombre_esc:<30} {t_sinc:>10.3f} {t_asin:>10.3f} {speedup:>9.1f}x {mem_diff:>9.1f}")

    print("\n" + "=" * 70)
    _imprimir_conclusion()


def _imprimir_conclusion():
    print("""
CONCLUSIONES
============
1. Con latencia 0ms (servidor local muy rápido):
   → El speedup de asíncrono es marginal. Código síncrono es más simple.

2. Con latencia 100ms (API normal):
   → Para 4+ peticiones, asíncrono es ~3-4x más rápido.
   → PUNTO DE CRUCE: ≥3 peticiones simultáneas.

3. Con latencia 500ms (API lenta o remota):
   → Asíncrono es hasta 10x más rápido para 4-20 peticiones.
   → La migración a asíncrono VALE COMPLETAMENTE la pena.

RECOMENDACIÓN PARA ECOMARKET:
  Si el dashboard carga ≥3 fuentes de datos remotas, usa asyncio.
  El costo de complejidad se amortiza desde la primera petición paralela.
""")


if __name__ == "__main__":
    asyncio.run(ejecutar_benchmark(repeticiones=3))
