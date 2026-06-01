import time
import json
import base64
import asyncio
import aiohttp

def decode_payload(token: str) -> dict:
    """
    Decodifica el payload de un JWT de forma segura sin verificar la firma.
    Cumple con el estándar de Base64URL restaurando el padding.
    """
    try:
        partes = token.split('.')
        if len(partes) < 2:
            raise ValueError("Token mal formado. Le faltan partes.")
        
        payload_segment = partes[1]
        # Restaurar el padding de Base64URL (Fragmento C)
        padding = 4 - len(payload_segment) % 4
        decoded = base64.urlsafe_b64decode(payload_segment + '=' * padding)
        return json.loads(decoded)
    except Exception as e:
        raise ValueError(f"Error al decodificar token: {e}")

class TokenManager:
    def __init__(self, auth_url="http://localhost:8080/auth/login"):
        self.auth_url = auth_url
        self._access_token = None
        self._refresh_token = None
        self._refresh_task = None # Tarea asíncrona compartida para el refresco singleton (INV-B3)
        self.refresh_count = 0 # Para llevar la cuenta en los tests

    def get_access_token(self):
        return self._access_token

    def get_auth_header(self):
        if not self._access_token:
            return {}
        return {'Authorization': f'Bearer {self._access_token}'}

    def is_expiring_soon(self) -> bool:
        """Determina si el token expirará en los próximos 10 segundos o si no existe."""
        if not self._access_token:
            return True
        try:
            payload = decode_payload(self._access_token)
            exp = payload.get("exp", 0)
            # Retorna True si expira pronto o ya expiró
            return time.time() + 10 >= exp
        except Exception:
            return True

    async def refresh_access_token(self) -> str:
        """
        Refresca el token de acceso asíncronamente.
        Implementa el patrón Singleton (INV-B3): si ya hay un refresco en curso,
        retorna la tarea existente en lugar de hacer otra petición de red.
        """
        if self._refresh_task is None:
            self._refresh_task = asyncio.create_task(self._do_refresh())
        
        try:
            return await self._refresh_task
        finally:
            # Una vez completado o fallado, la tarea se limpia
            # para que futuros refrescos inicien una nueva petición
            pass

    async def _do_refresh(self) -> str:
        """Realiza la petición de red para refrescar el token."""
        self.refresh_count += 1
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.auth_url, json={"username": "viewer"}) as response:
                    if response.status != 200:
                        raise Exception(f"Fallo al autenticar: {response.status}")
                    
                    data = await response.json()
                    self._access_token = data["access_token"]
                    self._refresh_token = data.get("refresh_token")
                    return self._access_token
        finally:
            # Limpiar la tarea para que el próximo refresh cree una nueva
            self._refresh_task = None
