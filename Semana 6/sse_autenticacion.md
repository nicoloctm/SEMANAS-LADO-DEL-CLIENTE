# SSE con Autenticación (Reto 6)

## Pregunta Central: ¿Soporta EventSource headers custom?
**NO.** La API nativa `EventSource` del navegador en JavaScript *no* permite configurar cabeceras HTTP personalizadas como `Authorization: Bearer TOKEN`. Fue diseñada intencionalmente de manera simple, pensada originalmente para usarse con cookies (`withCredentials`) y sin soporte para manipulación de cabeceras arbitrarias.

## Alternativas para el Contexto B (Navegador)

| Alternativa | Pros | Contras (Desde el cliente) |
|-------------|------|---------------------------|
| **withCredentials (cookies)** | Es el estándar nativo para auth en EventSource. Funciona transparente si el backend maneja sesión con cookies HttpOnly. | Requiere configuración extra en backend y proxy. No aplica si el resto del proyecto usa puramente Bearer Tokens en headers. |
| **Token en query param** (`?token=xyz`) | Funciona directo en `EventSource` sin instalar nada extra. | Pésima práctica de seguridad: el token queda expuesto en las URLs, el historial del navegador, y los logs del proxy/red. |
| **Librerías (@microsoft/fetch-event-source)** | Usa la API `fetch` subyacente que sí soporta headers, permitiendo enviar `Authorization: Bearer`. | Añades una dependencia extra a tu bundle que en realidad simula y procesa bytes crudos de fetch a mano. |
| **Service Worker interceptando** | Súper limpio para la UI, el componente web usa EventSource nativo y el SW le pega el header interceptándolo. | Altísima complejidad de implementación para un proyecto estudiantil o pequeño, sumado a problemas de ciclo de vida. |

### Recomendación para un panel interno corporativo:
Usar la librería **`@microsoft/fetch-event-source`**. Al ser corporativo y probablemente usar Auth0/Cognito (Bearer tokens puros), es mucho más seguro usar fetch por debajo que intentar pasar el JWT en la URL.

## Flujo de Renovación de Token en Python/Node.js (Contexto A)
Al parsear manualmente en Node/Python, la petición es nuestra:

```python
async def conectar_con_auth(self):
    while self.ejecutando:
        headers = {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self.token}"
        }
        try:
            status, stream = await self.hacer_peticion(headers)
            if status == 401:
                print("Token expirado durante conexión o inicio. Renovando...")
                self.token = await self.renovar_token()
                continue # Reintenta de inmediato
            
            await self.procesar_stream(stream)
            
        except Exception as e:
            # Fallo de red
            await asyncio.sleep(self.retry_ms / 1000)
```

## La limitación fundamental de las conexiones persistentes
El principal dolor es que, en **polling**, la conexión se renueva cada "x" segundos, por lo que el token que usas siempre está fresco; si expira, lo renuevas y mandas uno nuevo en el siguiente ciclo. 
En SSE o WebSockets, la conexión se **abre y se queda abierta indefinidamente**. Si el token de acceso dura 1 hora, y tu panel se queda abierto 2 horas, de pronto el servidor te va a soltar un error `401 Unauthorized` a mitad de la lectura y cerrará el socket abruptamente. El cliente debe estar programado no solo para reconectarse, sino para detectar que el corte fue por Auth, detenerse, negociar un token nuevo y abrir una *nueva conexión completa de SSE* desde cero pasándole el nuevo token.
