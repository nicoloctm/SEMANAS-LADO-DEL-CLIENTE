"""
test_circuit_breaker.py
=======================
Pruebas automatizadas del CircuitBreaker.
Verifican las invariantes críticas del sistema.

Cómo ejecutar:
  python -m pytest test_circuit_breaker.py -v
  o simplemente:
  python test_circuit_breaker.py
"""

import asyncio
import time
import unittest

from circuit_breaker import CircuitBreaker, CircuitOpenError, EstadoCircuito


# ──────────────────────────────────────────
# Funciones de ayuda para tests asíncronos
# ──────────────────────────────────────────
def run(coro):
    """Ejecuta una corutina de forma sincrónica para los tests.
    Crea un nuevo event loop por cada llamada para compatibilidad con Python 3.10+.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def peticion_ok():
    """Simula una petición exitosa."""
    return "ok"


async def peticion_falla():
    """Simula un error del servidor (500)."""
    raise ConnectionError("Error del servidor: 500")


async def peticion_401():
    """Simula un error de cliente (401 Unauthorized)."""
    raise PermissionError("Acceso denegado: 401")


# ──────────────────────────────────────────
# Casos de prueba
# ──────────────────────────────────────────
class TestCircuitBreakerInvariantes(unittest.TestCase):

    # ── TC-01 ────────────────────────────────
    def test_tc01_estado_inicial_cerrado(self):
        """TC-01: El circuito arranca en estado CERRADO."""
        cb = CircuitBreaker(umbral=3, timeout=5)
        self.assertEqual(cb.estado, EstadoCircuito.CERRADO)
        self.assertEqual(cb._fallos, 0)

    # ── TC-02 ────────────────────────────────
    def test_tc02_fallos_abren_circuito(self):
        """TC-02 (INV-A): 3 fallos consecutivos abren el circuito."""
        cb = CircuitBreaker(umbral=3, timeout=5)
        for _ in range(3):
            with self.assertRaises(ConnectionError):
                run(cb.ejecutar(peticion_falla))
        self.assertEqual(cb.estado, EstadoCircuito.ABIERTO)

    # ── TC-03 ────────────────────────────────
    def test_tc03_circuito_abierto_fail_fast(self):
        """TC-03 (INV-A2): Circuito abierto rechaza sin llamar al servidor."""
        cb = CircuitBreaker(umbral=1, timeout=60)
        with self.assertRaises(ConnectionError):
            run(cb.ejecutar(peticion_falla))
        # Ahora debe fallar inmediatamente sin ejecutar la función
        llamadas = []
        async def funcion_que_no_deberia_ejecutarse():
            llamadas.append(1)
            return "no deberia llegar aqui"
        with self.assertRaises(CircuitOpenError):
            run(cb.ejecutar(funcion_que_no_deberia_ejecutarse))
        self.assertEqual(len(llamadas), 0, "La función NO debería haberse llamado")

    # ── TC-04 ────────────────────────────────
    def test_tc04_inv_a3_reset_fallos_al_cerrar(self):
        """TC-04 (INV-A3): Al cerrar el circuito se resetea el contador de fallos."""
        cb = CircuitBreaker(umbral=3, timeout=0.1)  # timeout muy corto
        # Provocar 2 fallos (sin abrir)
        for _ in range(2):
            with self.assertRaises(ConnectionError):
                run(cb.ejecutar(peticion_falla))
        self.assertEqual(cb._fallos, 2)
        # Esperar a que expiren y recuperar con éxito
        time.sleep(0.2)
        run(cb.ejecutar(peticion_ok))  # Este debería cerrar el circuito
        # Después del éxito, fallos vuelven a 0 (INV-A3)
        self.assertEqual(cb._fallos, 0, "Fallos deben resetearse al cerrar el circuito")

    # ── TC-05 ────────────────────────────────
    def test_tc05_inv_a4_errores_cliente_no_cuentan(self):
        """TC-05 (INV-A4): Los errores 401/403 NO deben incrementar el contador de fallos."""
        cb = CircuitBreaker(umbral=3, timeout=5)
        # Provocar muchos errores de cliente
        for _ in range(10):
            with self.assertRaises(PermissionError):
                run(cb.ejecutar(peticion_401))
        # El circuito debe seguir CERRADO
        self.assertEqual(cb.estado, EstadoCircuito.CERRADO,
                         "Errores de cliente no deben abrir el circuito")
        self.assertEqual(cb._fallos, 0,
                         "El contador de fallos debe seguir en 0")

    # ── TC-06 ────────────────────────────────
    def test_tc06_callback_on_state_change(self):
        """TC-06: El callback on_state_change se llama al cambiar de estado."""
        cb = CircuitBreaker(umbral=1, timeout=0.1)
        cambios = []
        cb.on_state_change = lambda viejo, nuevo: cambios.append((viejo, nuevo))
        
        with self.assertRaises(ConnectionError):
            run(cb.ejecutar(peticion_falla))
        
        # Debe haber registrado el cambio CERRADO → ABIERTO
        self.assertTrue(len(cambios) > 0, "El callback debería haberse llamado")
        self.assertEqual(cambios[0][0], EstadoCircuito.CERRADO)
        self.assertEqual(cambios[0][1], EstadoCircuito.ABIERTO)

    # ── TC-07 ────────────────────────────────
    def test_tc07_recovery_after_timeout(self):
        """TC-07: Tras el timeout, el circuito pasa a SEMIABIERTO y luego a CERRADO si hay éxito."""
        cb = CircuitBreaker(umbral=1, timeout=0.2)  # timeout muy corto para el test
        with self.assertRaises(ConnectionError):
            run(cb.ejecutar(peticion_falla))
        self.assertEqual(cb.estado, EstadoCircuito.ABIERTO)
        
        time.sleep(0.3)  # Esperar a que expire el timeout
        
        # La primera petición exitosa debe cerrar el circuito
        resultado = run(cb.ejecutar(peticion_ok))
        self.assertEqual(resultado, "ok")
        self.assertEqual(cb.estado, EstadoCircuito.CERRADO)

    # ── TC-08 ────────────────────────────────
    def test_tc08_inv_a1_circuit_breaker_no_procesa_tokens(self):
        """TC-08 (INV-A1): El CircuitBreaker no tiene métodos ni atributos relacionados con tokens JWT."""
        cb = CircuitBreaker()
        atributos = dir(cb)
        palabras_prohibidas = ["token", "jwt", "auth", "bearer", "decode", "payload"]
        for palabra in palabras_prohibidas:
            coincidencias = [a for a in atributos if palabra in a.lower()]
            self.assertEqual(coincidencias, [],
                             f"El CircuitBreaker NO debe tener nada relacionado con '{palabra}': {coincidencias}")


# ──────────────────────────────────────────
# Ejecución directa
# ──────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print(" Pruebas automatizadas - CircuitBreaker (INV A)")
    print("=" * 55)
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromTestCase(TestCircuitBreakerInvariantes)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n  Pruebas ejecutadas : {result.testsRun}")
    print(f"  Errores            : {len(result.errors)}")
    print(f"  Fallos             : {len(result.failures)}")
    if result.wasSuccessful():
        print("  [OK] TODAS LAS PRUEBAS PASARON")
    else:
        print("  [FAIL] ALGUNAS PRUEBAS FALLARON")
