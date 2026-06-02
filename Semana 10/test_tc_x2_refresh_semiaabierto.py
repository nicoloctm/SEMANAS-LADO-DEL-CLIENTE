"""
test_tc_x2_refresh_semiaabierto.py
==================================
Prueba automatizada de regresión cruzada TC-X2.
Verifica que con el Circuit Breaker en SEMIABIERTO y el token por expirar:
1. Se intente primero el refresh del token.
2. Solo se ejecute una petición de red para el refresh (patrón singleton - INV-B3).
3. Solo una petición de prueba pase al servidor mock (INV-A2).
4. Las peticiones concurrentes en SEMIABIERTO se rechacen con CircuitOpenError.
"""

import asyncio
import base64
import json
import time
import unittest
from unittest.mock import patch

from circuit_breaker import CircuitBreaker, CircuitOpenError, EstadoCircuito
from token_manager import TokenManager
from cliente_robusto import ClienteRobusto


# Helper para simular respuestas de aiohttp
class MockResponse:
    def __init__(self, status, json_data):
        self.status = status
        self._json_data = json_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def json(self):
        return self._json_data


def generate_mock_jwt(exp_seconds=30):
    """Genera un JWT falso con expiración relativa para pruebas."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b'=').decode()
    exp = int(time.time()) + exp_seconds
    payload = json.dumps({"sub": "viewer", "exp": exp}).encode()
    payload_b64 = base64.urlsafe_b64encode(payload).rstrip(b'=').decode()
    return f"{header}.{payload_b64}.signature"


def run_async(coro):
    """Helper para correr corutinas en el test loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestTCX2RefreshSemiaabierto(unittest.TestCase):

    @patch('aiohttp.ClientSession.post')
    @patch('aiohttp.ClientSession.get')
    def test_tc_x2_flow(self, mock_get, mock_post):
        """TC-X2: Token expira en SEMIABIERTO. Verifica orden, refresh y fail-fast concurrentes."""
        
        # 1. Configurar cliente robusto
        cliente = ClienteRobusto(base_url="http://localhost:8080", umbral=2, timeout=5)
        
        # 2. Configurar TokenManager con un token expirado/inexistente inicialmente
        # para forzar que is_expiring_soon() sea True.
        cliente.token_manager._access_token = generate_mock_jwt(exp_seconds=-5) # Expiró hace 5s
        
        # 3. Forzar el estado SEMIABIERTO en el Circuit Breaker
        cliente.circuit_breaker.estado = EstadoCircuito.SEMIABIERTO
        cliente.circuit_breaker._peticion_de_prueba_en_curso = False
        cliente.circuit_breaker._fallos = 2 # El umbral es 2
        
        # Variables de control para registrar el orden de ejecución
        call_order = []
        
        # Configurar mocks de manera sincrónica para que devuelvan el manejador de contexto asíncrono
        # sin provocar warnings de corutinas no esperadas.
        def side_effect_post(*args, **kwargs):
            call_order.append("REFRESH_POST")
            # Devuelve un token nuevo que no expira pronto (vigencia de 3600s)
            nuevo_token = generate_mock_jwt(exp_seconds=3600)
            return MockResponse(200, {"access_token": nuevo_token, "refresh_token": "mock.refresh"})
            
        def side_effect_get(*args, **kwargs):
            call_order.append("GET_PRODUCTOS")
            # Simulamos éxito en la petición de prueba
            return MockResponse(200, [{"id": 1, "nombre": "Manzana", "precio": 1.5}])

        mock_post.side_effect = side_effect_post
        mock_get.side_effect = side_effect_get

        # 4. Ejecutar 3 peticiones concurrentes usando asyncio.gather
        async def execute_concurrent_requests():
            # Concurrencia de 3 peticiones GET
            tasks = [
                cliente.get("/productos"),
                cliente.get("/productos"),
                cliente.get("/productos")
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)

        resultados = run_async(execute_concurrent_requests())



        # 5. Verificaciones y Aserciones

        # Aserción 1: Verificar el orden de las llamadas (primero refresh, luego get)
        self.assertEqual(call_order, ["REFRESH_POST", "GET_PRODUCTOS"], 
                         "El flujo debió hacer exactamente un refresh de token primero, y luego una petición GET.")

        # Aserción 2: Solo una petición debió tener éxito (la primera)
        exitosas = [r for r in resultados if not isinstance(r, Exception)]
        errores = [r for r in resultados if isinstance(r, Exception)]

        self.assertEqual(len(exitosas), 1, "Exactamente una petición debió tener éxito.")
        self.assertEqual(len(errores), 2, "Exactamente dos peticiones debieron fallar.")

        # Aserción 3: Las falladas deben ser de tipo CircuitOpenError debido a la restricción en SEMIABIERTO
        for err in errores:
            self.assertIsInstance(err, CircuitOpenError, 
                                  "Las peticiones concurrentes debieron fallar por circuito abierto en SEMIABIERTO (INV-A2).")
            self.assertIn("SEMIABIERTO", str(err), "El mensaje de error debe indicar estado SEMIABIERTO.")

        # Aserción 4: El CircuitBreaker debe haber cerrado el circuito tras la petición de prueba exitosa (SEMIABIERTO -> CERRADO)
        self.assertEqual(cliente.circuit_breaker.estado, EstadoCircuito.CERRADO, 
                         "El circuito debió volver a CERRADO tras el éxito de la petición de prueba.")
        self.assertEqual(cliente.circuit_breaker._fallos, 0, 
                         "El contador de fallos debió resetearse a 0 (INV-A3).")
        
        # Aserción 5: El TokenManager debe haber guardado el nuevo token y su contador de refrescos debe ser 1
        self.assertEqual(cliente.token_manager.refresh_count, 1, 
                         "Debería haberse realizado exactamente una llamada de refresco de red (refresh singleton - INV-B3).")
        self.assertIsNotNone(cliente.token_manager.get_access_token(), 
                             "El token de acceso no debería ser nulo tras el refresco.")


if __name__ == "__main__":
    print("=" * 60)
    print(" Ejecutando TC-X2: Test de Refresco de Token en SEMIABIERTO")
    print("=" * 60)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestTCX2RefreshSemiaabierto)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n  [OK] PRUEBA TC-X2 COMPLETADA CON ÉXITO")
        exit(0)
    else:
        print("\n  [FAIL] PRUEBA TC-X2 FALLIDA")
        exit(1)
