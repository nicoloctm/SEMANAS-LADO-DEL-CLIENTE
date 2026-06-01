# Diseño: Integración SSE + Autenticación (Reto 7 - Profundiza)

Esta es la propuesta arquitectónica para integrar una conexión persistente `ClienteSSEMultiplex` (Semana 7) con el `TokenManager` (Semana 8) cuando el servidor de EcoMarket elige la **Opción B** (cierra la conexión cuando el token expira).

## 1. Análisis: Opción A vs Opción B
- **Opción A (No verificar tras abrir):** Es lo más simple para el cliente, abre la conexión SSE y se olvida de la expiración. A los auditores de seguridad no les gusta porque un empleado despedido podría mantener una pestaña abierta durante días recibiendo eventos clasificados si su token expiró pero la conexión persistente no se cortó activamente.
- **Opción B (Cortar conexión activa en expiración):** Obliga al cliente a reconectar autenticado periódicamente. Es mucho más seguro, pero más complejo de programar para nosotros en el frontend/cliente, ya que el cliente debe discernir entre un corte por "se cayó mi WiFi" y "mi token expiró".

## 2. Mecanismo de Auth al abrir la conexión SSE (Python)
Dado que en Python (Ruta A) construimos las requests HTTP manualmente (usando `httpx` o `aiohttp`), tenemos total control sobre los cabeceros. No estamos limitados como en la API `EventSource` del navegador que no permite custom headers.
Por lo tanto, la elección correcta es enviar el access_token en el **Header Authorization (Opción A)**. Evitamos pasar el token en query params (`?token=`) porque los tokens de acceso quedarían registrados en texto plano en los logs del proxy (Nginx/Apache), lo cual es una vulnerabilidad grave y un anti-patrón.

## 3. Flujo de Reconexión Autenticada (Pseudocódigo)
El cliente SSE ahora inyectará el `TokenManager` como dependencia y actuará inteligentemente ante cierres de conexión.

```python
class ClienteSSEMultiplexAutenticado:
    def __init__(self, token_manager, url):
        self.tm = token_manager
        self.url = url
        self.last_event_id = None
        
    async def escuchar_eventos(self):
        while True:
            # 1. Antes de conectar, asegurarnos de que el token es fresco
            if self.tm.is_expiring_soon():
                await self.tm.refresh_access_token()
                
            headers = self.tm.get_auth_header()
            headers["Accept"] = "text/event-stream"
            if self.last_event_id:
                headers["Last-Event-ID"] = self.last_event_id
                
            try:
                # 2. Iniciar conexión de stream
                response = await http_client.stream("GET", self.url, headers=headers)
                
                # 3. Detectar cierre por expiración (Opción B)
                if response.status_code == 401:
                    print("Conexión de eventos rechazada por expiración.")
                    await self.tm.refresh_access_token()
                    continue # Reintentar el loop con el token nuevo y reconectar
                    
                # Si conecta ok, leer chunks...
                async for chunk in response.iter_lines():
                    # Parsear data, actualizar self.last_event_id
                    pass
                    
            except Exception as e:
                # 4. Error regular de red (caída de wifi, timeout de TCP)
                print("Caída de red, aplicando backoff antes de reconectar...")
                await asyncio.sleep(3)
```

Este diseño respeta todos los invariantes de seguridad de la Semana 8 y permite reconexiones automáticas (como en la Semana 6/7) que sean completamente transparentes para el usuario de EcoMarket.
