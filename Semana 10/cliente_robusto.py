"""
cliente_robusto.py
==================
Cliente HTTP robusto para el mercado EcoMarket.
Integra el CircuitBreaker y el TokenManager de forma desacoplada
cumpliendo el Principio de Responsabilidad Única (SRP).

Invariantes que garantiza:
  - INV-A1: El CircuitBreaker nunca toca tokens JWT.
  - INV-B3: El refresco de tokens es singleton (no se duplican peticiones).
  - INV-C1: Cada petición lleva header Authorization correcto.
  - INV-C2: Si el token está por expirar, se refresca antes de la petición.
"""

import aiohttp
from circuit_breaker import CircuitBreaker, CircuitOpenError
from token_manager import TokenManager


class ClienteRobusto:
    def __init__(self, base_url="http://localhost:8080", umbral=3, timeout=5):
        self.base_url = base_url
        # El CircuitBreaker solo sabe de fallos de red, nada de tokens
        self.circuit_breaker = CircuitBreaker(umbral=umbral, timeout=timeout)
        # El TokenManager solo sabe de autenticación
        self.token_manager = TokenManager(auth_url=f"{base_url}/auth/login")

        # Conectar el callback para mostrar los cambios de estado del circuito
        self.circuit_breaker.on_state_change = self._on_circuit_state_change

    def _on_circuit_state_change(self, viejo, nuevo):
        """Muestra en consola cuando el circuito cambia de estado."""
        print(f"  [CircuitBreaker] {viejo.value} → {nuevo.value}")

    async def _preparar_headers(self):
        """
        Prepara los headers HTTP.
        Si el token está por expirar o no existe, lo refresca primero.
        Garantiza INV-C2.
        """
        if self.token_manager.is_expiring_soon():
            print("  [TokenManager] Token por expirar, refrescando...")
            await self.token_manager.refresh_access_token()
        return self.token_manager.get_auth_header()

    async def get(self, ruta):
        """
        Realiza una petición GET protegida por el CircuitBreaker.
        La lógica de tokens es completamente externa al CircuitBreaker.
        """
        headers = await self._preparar_headers()

        async def _peticion():
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{ruta}"
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    # Los errores 4xx (cliente) no deben abrir el circuito (INV-A4)
                    if resp.status in (401, 403):
                        raise PermissionError(f"Acceso denegado: {resp.status}")
                    if resp.status >= 500:
                        raise ConnectionError(f"Error del servidor: {resp.status}")
                    return await resp.json()

        # El circuit breaker envuelve solo la petición de red
        return await self.circuit_breaker.ejecutar(_peticion)

    async def post(self, ruta, datos):
        """
        Realiza una petición POST protegida por el CircuitBreaker.
        """
        headers = await self._preparar_headers()

        async def _peticion():
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{ruta}"
                async with session.post(url, json=datos, headers=headers, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    if resp.status in (401, 403):
                        raise PermissionError(f"Acceso denegado: {resp.status}")
                    if resp.status >= 500:
                        raise ConnectionError(f"Error del servidor: {resp.status}")
                    return await resp.json()

        return await self.circuit_breaker.ejecutar(_peticion)

    def estado_circuito(self):
        """Retorna el estado actual del circuito como texto."""
        return self.circuit_breaker.estado.value
