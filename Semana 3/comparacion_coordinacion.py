"""
comparacion_coordinacion.py  –  Semana 3  –  Reto 7
=====================================================
Compara las 4 estrategias de coordinación de tareas asíncronas:
  1. asyncio.gather()                         – esperar a TODAS
  2. asyncio.wait(FIRST_COMPLETED) + loop     – procesar conforme llegan
  3. asyncio.as_completed()                   – iterar por orden de llegada
  4. asyncio.wait(FIRST_EXCEPTION)            – abortar ante primer error

Escenario simulado:
  productos=200ms, categorías=100ms, perfil=500ms, notificaciones=TIMEOUT(2s)
"""
import asyncio
import time
import logging
from typing import Any

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ─── Simulación de peticiones con delay ──────────────────────────────────────
async def _simular_peticion(nombre: str, delay_s: float, falla: bool = False) -> dict:
    await asyncio.sleep(delay_s)
    if falla:
        raise TimeoutError(f"Timeout simulado en '{nombre}' ({delay_s}s)")
    return {"fuente": nombre, "datos": f"datos de {nombre}"}

def _crear_tareas() -> dict:
    """Crea las 4 coroutines del escenario de prueba."""
    return {
        "productos":      _simular_peticion("productos",      0.2),
        "categorias":     _simular_peticion("categorias",     0.1),
        "perfil":         _simular_peticion("perfil",         0.5),
        "notificaciones": _simular_peticion("notificaciones", 2.0, falla=True),
    }


# ─── Estrategia 1: asyncio.gather ────────────────────────────────────────────
async def estrategia_gather() -> tuple[dict, float]:
    """Espera a que TODAS las tareas completen (o fallen)."""
    t0 = time.monotonic()
    tareas = _crear_tareas()

    resultados_raw = await asyncio.gather(*tareas.values(), return_exceptions=True)
    elapsed = time.monotonic() - t0

    resultado = {}
    for nombre, r in zip(tareas.keys(), resultados_raw):
        resultado[nombre] = r if not isinstance(r, Exception) else {"error": str(r)}

    print(f"\n[gather] Tiempo total: {elapsed:.2f}s")
    print(f"[gather] Primer dato disponible: al finalizar TODO ({elapsed:.2f}s)")
    return resultado, elapsed


# ─── Estrategia 2: asyncio.wait(FIRST_COMPLETED) ─────────────────────────────
async def estrategia_wait_first_completed() -> tuple[dict, float]:
    """Procesa resultados conforme van llegando."""
    t0 = time.monotonic()
    tareas_dict = _crear_tareas()
    tareas_set = {asyncio.create_task(coro, name=n) for n, coro in tareas_dict.items()}
    resultado = {}
    primer_dato_t = None

    pendientes = tareas_set
    while pendientes:
        listas, pendientes = await asyncio.wait(
            pendientes,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for tarea in listas:
            t_llegada = time.monotonic() - t0
            if primer_dato_t is None:
                primer_dato_t = t_llegada
            try:
                resultado[tarea.get_name()] = tarea.result()
                print(f"  [wait:FC] '{tarea.get_name()}' llegó a t={t_llegada:.2f}s")
            except Exception as e:
                resultado[tarea.get_name()] = {"error": str(e)}
                print(f"  [wait:FC] '{tarea.get_name()}' FALLA a t={t_llegada:.2f}s → {e}")

    elapsed = time.monotonic() - t0
    print(f"[wait:FC] Primer dato: {primer_dato_t:.2f}s | Total: {elapsed:.2f}s")
    return resultado, elapsed


# ─── Estrategia 3: asyncio.as_completed ──────────────────────────────────────
async def estrategia_as_completed() -> tuple[dict, float]:
    """Itera futuros en el orden en que completan."""
    t0 = time.monotonic()
    tareas_dict = _crear_tareas()
    tareas_list = [asyncio.create_task(coro, name=n) for n, coro in tareas_dict.items()]
    resultado = {}
    primer_dato_t = None

    for fut in asyncio.as_completed(tareas_list):
        t_llegada = time.monotonic() - t0
        if primer_dato_t is None:
            primer_dato_t = t_llegada
        try:
            r = await fut
            resultado[r["fuente"]] = r
            print(f"  [as_completed] '{r['fuente']}' llegó a t={t_llegada:.2f}s")
        except Exception as e:
            print(f"  [as_completed] ERROR a t={t_llegada:.2f}s → {e}")
            resultado[str(e)] = {"error": str(e)}

    elapsed = time.monotonic() - t0
    print(f"[as_completed] Primer dato: {primer_dato_t:.2f}s | Total: {elapsed:.2f}s")
    return resultado, elapsed


# ─── Estrategia 4: asyncio.wait(FIRST_EXCEPTION) ─────────────────────────────
async def estrategia_wait_first_exception() -> tuple[dict, float]:
    """Aborta y cancela todo en cuanto llega el primer error."""
    t0 = time.monotonic()
    tareas_dict = _crear_tareas()
    tareas_set = {asyncio.create_task(coro, name=n) for n, coro in tareas_dict.items()}
    resultado = {}
    abortado = False

    listas, pendientes = await asyncio.wait(
        tareas_set,
        return_when=asyncio.FIRST_EXCEPTION,
    )

    for tarea in listas:
        try:
            resultado[tarea.get_name()] = tarea.result()
        except Exception as e:
            abortado = True
            resultado[tarea.get_name()] = {"error": str(e)}
            print(f"  [wait:FE] ERROR en '{tarea.get_name()}' → cancelando {len(pendientes)} pendientes")
            for t in pendientes:
                t.cancel()
            await asyncio.gather(*pendientes, return_exceptions=True)

    elapsed = time.monotonic() - t0
    print(f"[wait:FE] Abortado: {abortado} | Completados: {len(listas)} | Cancelados: {len(pendientes)}")
    print(f"[wait:FE] Tiempo total: {elapsed:.2f}s")
    return resultado, elapsed


# ─── Tabla comparativa ────────────────────────────────────────────────────────
async def main():
    print("=" * 60)
    print("  COMPARACIÓN DE ESTRATEGIAS DE COORDINACIÓN ASÍNCRONA")
    print("=" * 60)
    print("Escenario: productos=0.2s, categorías=0.1s, perfil=0.5s, notificaciones=TIMEOUT(2s)")
    print()

    _, t1 = await estrategia_gather()
    _, t2 = await estrategia_wait_first_completed()
    _, t3 = await estrategia_as_completed()
    _, t4 = await estrategia_wait_first_exception()

    print("\n" + "=" * 60)
    print("  TABLA RESUMEN")
    print("=" * 60)
    print(f"{'Estrategia':<30} {'Tiempo (s)':>10} {'Maneja error':>15} {'Parcial':>10}")
    print("-" * 60)
    print(f"{'1. gather(return_exc=True)':<30} {t1:>10.2f} {'✅ Sí':>15} {'❌ No':>10}")
    print(f"{'2. wait(FIRST_COMPLETED)':<30} {t2:>10.2f} {'✅ Sí':>15} {'✅ Sí':>10}")
    print(f"{'3. as_completed()':<30} {t3:>10.2f} {'✅ Sí':>15} {'✅ Sí':>10}")
    print(f"{'4. wait(FIRST_EXCEPTION)':<30} {t4:>10.2f} {'🔴 Aborta':>15} {'❌ No':>10}")
    print()
    print("RECOMENDACIÓN PARA ECOMARKET:")
    print("  → gather(return_exceptions=True) para el dashboard inicial")
    print("    (simplicidad + tolerancia a fallos parciales)")
    print("  → wait(FIRST_COMPLETED) si se quiere UI progresiva")
    print("  → wait(FIRST_EXCEPTION) SOLO para flujos donde 1 fallo invalida todo (ej. auth)")

if __name__ == "__main__":
    asyncio.run(main())
