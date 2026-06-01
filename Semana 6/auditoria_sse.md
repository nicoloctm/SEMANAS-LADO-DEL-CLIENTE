# Auditoría de Errores SSE (Reto 4)

Aquí están los 4 errores sutiles típicos generados por la IA en clientes SSE que violan los invariantes:

## Error 1: Acumular buffer de líneas sin resetearlo
- **Descripción:** El código almacena las líneas del `data:` en un buffer, pero al procesar el mensaje con la línea en blanco (`\n\n`), olvida vaciar el acumulador o resetear las variables.
- **Falla en producción:** El primer evento se procesa bien. El segundo evento trae sus datos *más* los datos del primer evento, causando que el JSON sea inválido o mezclando información.
- **Invariante violado:** "El buffer de líneas debe resetearse completamente después de cada mensaje procesado."

## Error 2: Reconexión infinita sin límite ni backoff (While True puro)
- **Descripción:** En el bloque de `except Exception:`, el código simplemente hace `continue` o un `sleep(1)` fijo sin incrementar un contador de reintentos.
- **Falla en producción:** Si el servidor se cae de verdad, el cliente genera una tormenta de peticiones infinitas cada segundo, actuando como un ataque DDoS sobre un servidor que ya de por sí está débil.
- **Invariante violado:** "Máximo 5 intentos de reconexión con backoff."

## Error 3: No tener un timeout en la conexión inicial o de lectura
- **Descripción:** Se hace la petición a la red (ej. con `httpx.stream`) pero no se especifica el argumento de timeout, dejándolo por defecto en nulo o infinito según la librería.
- **Falla en producción:** Si la red del celular del usuario se "congela" (dropped packets) pero no manda una señal de cierre de conexión al socket TCP, el cliente se queda esperando eventos para siempre y la UI aparenta estar desconectada permanentemente.
- **Invariante violado:** "Timeout configurado en la conexión inicial."

## Error 4: Parsear asumiendo que `data:` siempre es de una sola línea
- **Descripción:** El código hace `if line.startswith("data:"): json.loads(line[6:])` inmediatamente al ver la primera línea `data:`, en lugar de esperar la línea en blanco que señala el fin.
- **Falla en producción:** Los mensajes SSE válidos frecuentemente mandan JSON grandes divididos en múltiples líneas `data:`. Al parsear en la primera ocurrencia, el JSON es incompleto y lanza error fatal.
- **Invariante violado:** "Nunca procesar un mensaje SSE incompleto — esperar siempre la línea en blanco que lo termina."

### Evidencia (Output / Comprobación local)
Al inducir intencionadamente un fallo en el procesamiento de un evento y no rodear la iteración de stream en un bloque `try/except` que se recupere, vimos cómo todo el cliente se terminaba de golpe (violando que un error de un handler no debe cortar el stream entero). Estos errores fueron validados mediante la impresión de logs directos en la consola durante la Etapa 3.
