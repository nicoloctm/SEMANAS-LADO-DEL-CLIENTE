# Semana 6: Server-Sent Events

Entregables de la Fase COMPRENDE, APLICA, REFLEXIONA, VALIDA y PROFUNDIZA de la Semana 6 (Protocolo SSE).

## 1. Traza SSE (Reto 1)
- **Flujo:** 
  1. Cliente realiza `GET /api/alertas` enviando cabecera `Accept: text/event-stream`.
  2. Servidor responde y luego envía periódicamente `event: precio-actualizado`. Cliente procesa cada línea y las ensambla.
  3. Red cae a los 25s por interrupción.
  4. Cliente espera 3s (el *retry_ms* por defecto) y reconecta enviando la cabecera `Last-Event-ID: 3`.
- **Por qué SSE reduce peticiones vacías vs Polling:** SSE usa 1 sola conexión persistente abierta por donde fluyen todos los eventos únicamente cuando hay datos nuevos. El Polling requiere abrir múltiples conexiones completas en donde el 90% del tiempo el servidor contesta que "nada ha cambiado".

## 2. Archivos Entregables
- **`receptor_alertas.py`**: Cliente SSE implementado con parseo manual (Ruta A de Python). Cuenta con docstrings del Trade-off (Reto 3).
- **`conversacion_socratica_semana6.md`**: Conversación socrática aclarando dudas del flujo básico y limitantes.
- **`auditoria_sse.md`**: Análisis de violaciones silenciosas (Reto 4).
- **`receptor_alertas_v2.py`**: Código del Reto 5, que implementa patrón Observer + SSE.
- **`sse_autenticacion.md`**: Reto 6 avanzado, evaluando limitaciones de EventSource con Bearer Tokens.
- **`validacion.log`**: Salida representativa mostrando la conexión y el uso de los Observadores.

### Reto 5: Herencia vs Composición para Observable
En el script `receptor_alertas_v2.py` decidí usar **herencia** (`class ReceptorAlertasV2(Observable)`) en lugar de composición. 
**Argumentación:** Conceptualmente, un cliente de Server-Sent Events *es* intrínsecamente un Emisor u Observable de eventos en el dominio de nuestra UI. Cumple perfectamente la relación "es-un" (is-a). Todo el resto de la aplicación espera suscribirse a él directamente para escuchar notificaciones, por lo que exponer los métodos nativos `suscribir()` heredados tiene un uso mucho más transparente y directo.
