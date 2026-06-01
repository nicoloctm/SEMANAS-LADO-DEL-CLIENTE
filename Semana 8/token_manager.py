import asyncio
import time
import base64
import json
from typing import Optional

class TokenManager:
    """
    Gestiona el ciclo de vida de los JWT del cliente EcoMarket.
    """
    def __init__(self):
        # DECISIÓN DE DISEÑO: Almacenamiento en memoria del proceso
        # El access_token se guarda en memoria porque solo debe durar 15 min.
        # Si el proceso muere, el token se pierde, lo cual es seguro.
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        
        # DECISIÓN DE DISEÑO: Mecanismo de singleton
        # Usamos asyncio.Lock porque estamos en un contexto de co-rutinas asíncronas
        # en el mismo hilo. Protege contra el problema de "thundering herd".
        self._refresh_lock = asyncio.Lock()
        self._refresh_endpoint = "http://localhost:8080/api/auth/refresh"

    def decode_payload(self, token: str) -> dict:
        """
        Decodifica el payload de un JWT sin verificar firma.
        DECISIÓN DE DISEÑO: Validar que el token tenga 3 partes antes de
        procesarlo para evitar un IndexError crudo.
        """
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Token malformado: debe tener 3 partes")
        
        payload_b64 = parts[1]
        padded = payload_b64.replace('-', '+').replace('_', '/') + '=='
        return json.loads(base64.b64decode(padded))

    def is_expiring_soon(self, margin_seconds: int = 300) -> bool:
        """
        Retorna True si el access_token expirará en menos de margin_seconds segundos.
        DECISIÓN DE DISEÑO: Margin de 300s (5 min). Permite manejar clock skew y 
        da tiempo suficiente para renovar sin interrumpir al usuario bruscamente.
        """
        if not self._access_token:
            return True
        
        try:
            payload = self.decode_payload(self._access_token)
        except Exception:
            return True # Token inválido, asume expirado
            
        exp = payload.get("exp")
        if not exp:
            return True # Sin exp asume expirado por seguridad
            
        ahora_unix = time.time()
        tiempo_restante = exp - ahora_unix
        return tiempo_restante < margin_seconds

    def store_tokens(self, access_token: str, refresh_token: str) -> None:
        """Almacena los tokens recibidos del servidor al hacer login o refresh."""
        self._access_token = access_token
        self._refresh_token = refresh_token

    def get_auth_header(self) -> dict:
        """Retorna el header Authorization listo para adjuntar a una petición."""
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}

    async def refresh_access_token(self) -> bool:
        """
        Realiza el refresh del access_token usando el refresh_token.
        Maneja el patrón Singleton.
        """
        if not self._refresh_token:
            return False
            
        async with self._refresh_lock:
            # Comprobación crucial del singleton:
            # Si entramos al lock y el token ya no está a punto de expirar,
            # significa que otra corrutina ya lo renovó mientras esperábamos en el lock.
            if not self.is_expiring_soon():
                return True
                
            print("[TokenManager] 🔄 Iniciando refresh singleton...")
            
            try:
                # Simulación latencia de red (POST _refresh_endpoint)
                await asyncio.sleep(1)
                
                if self._refresh_token == "refresh_token_invalido":
                    print("[TokenManager] ❌ Refresh falló (401)")
                    self.logout()
                    return False
                
                print("[TokenManager] ✅ Refresh exitoso, nuevo token recibido")
                # Simulamos nuevo token con expiración lejana
                self._access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTcxNDAwMH0.new_token"
                return True
            except Exception as e:
                print(f"[TokenManager] ❌ Error de red durante refresh: {e}")
                return False

    def logout(self) -> None:
        """Limpia todos los tokens del estado del cliente."""
        print("[TokenManager] 🚪 Ejecutando logout limpio")
        self._access_token = None
        self._refresh_token = None


# ==========================================
# RETO 4: Interceptor HTTP
# ==========================================
class EcoMarketClient:
    def __init__(self, token_manager: TokenManager):
        self.tm = token_manager
        
    async def auth_request(self, endpoint: str) -> dict:
        """
        Intercepta y adjunta token. Si falla 401, reintenta UNA vez.
        DECISIÓN DE DISEÑO: No iterar infinitamente para evitar un loop de 401.
        """
        headers = self.tm.get_auth_header()
        print(f"[Interceptor] 🚀 GET {endpoint} con headers {headers}")
        
        # Simulación de respuesta 401 para probar el reintento
        status = 401 if "force_401" in endpoint and self.tm._access_token != "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTcxNDAwMH0.new_token" else 200
        
        if status == 401:
            print("[Interceptor] ⚠️ 401 Unauthorized. Intentando refresh...")
            exito = await self.tm.refresh_access_token()
            if exito:
                headers = self.tm.get_auth_header()
                print(f"[Interceptor] 🚀 REINTENTO GET {endpoint} con headers {headers}")
                return {"status": 200, "data": "exito tras refresh"}
            else:
                self.tm.logout()
                return {"status": 401, "data": "login requerido"}
                
        return {"status": 200, "data": "exito directo"}

async def demostracion():
    tm = TokenManager()
    
    print("\n--- 1. Login Simulado ---")
    tm.store_tokens("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTcxNDAwMH0.firma", "valid_refresh")
    
    print("\n--- 2. Parseo y Expiración ---")
    payload = tm.decode_payload(tm._access_token)
    print(f"Payload decodificado: {payload}")
    print(f"¿Expira pronto? {tm.is_expiring_soon()}")
    
    print("\n--- 3. Petición Autenticada con 401 Simulado y Singleton ---")
    client = EcoMarketClient(tm)
    
    # Lanzamos 3 peticiones concurrentes para probar el singleton del refresh
    peticiones = [
        client.auth_request("/api/ecomarket/precios?force_401=true"),
        client.auth_request("/api/ecomarket/precios?force_401=true"),
        client.auth_request("/api/ecomarket/precios?force_401=true")
    ]
    resultados = await asyncio.gather(*peticiones)
    print("\nResultados de las peticiones concurrentes:")
    for i, res in enumerate(resultados):
        print(f" Req {i}: {res}")

if __name__ == "__main__":
    asyncio.run(demostracion())
