# 💬 Conversación Socrática – Semana 4
## Polling, Patrón Observer y Patrones de Comunicación
### Alumno: Estudiante de Sistemas (2do semestre) | IA: Instructora

---

> *La conversación cubre los Retos 1, 2 y 3 de la Semana 4: desde el primer contacto con el problema de datos desactualizados hasta el diseño socrático de las decisiones de trade-off.*

---

## 🎬 Reto 1 – Traza del Flujo de Polling (README conceptual)

---

**🧑‍💻 Alumno:**
Leí el escenario y entendí el problema: el dashboard muestra precios viejos. Pero no entiendo exactamente qué significa "polling". ¿Es como hacer F5 en el navegador?

**🤖 IA:**
Buena analogía para empezar. Ahora dime: cuando haces F5, ¿quién decide cuándo actualizar?

**🧑‍💻 Alumno:**
Yo, el usuario.

**🤖 IA:**
¿Y si el usuario olvidara hacerlo? ¿Los datos se actualizarían solos?

**🧑‍💻 Alumno:**
No... quedarían viejos. ¡Ah, entonces polling es como un F5 automático que hace el código cada cierto tiempo!

**🤖 IA:**
Exacto. Y ahora la pregunta más importante: si tienes 500 clientes abiertos a la vez y cada uno hace polling cada segundo, ¿cuántas peticiones llegan al servidor por minuto?

**🧑‍💻 Alumno:**
500 × 60 = 30,000 peticiones por minuto. Eso es mucho...

**🤖 IA:**
¿Y si en vez de cada segundo fuera cada 5 segundos, pero sólo aceleraras cuando detectas que hubo cambios?

**🧑‍💻 Alumno:**
¡Eso sería más inteligente! Pregunto poco cuando está tranquilo, y más rápido cuando cambian cosas. Eso es el "adaptativo".

---

### 📊 Traza manual del flujo (Reto 1)

```
CLIENTE                    SERVIDOR                     TIEMPO
   │                           │
   │  GET /productos            │
   │  (If-None-Match: null)    │ ──────────────────►  t=0s
   │                           │◄── 200 OK {datos}
   │  notificar(datos_actualizados)               t≈0.1s
   │  intervalo_actual = 5s    │
   │                           │
   │  [espera 5s]              │                     t=5s
   │                           │
   │  GET /productos            │
   │  (If-None-Match: etag-1)  │ ──────────────────►  t=5s
   │                           │◄── 304 Not Modified
   │  intervalo_actual = 7.5s  │                     t≈5.1s
   │  (backoff ×1.5)           │
   │                           │
   │  [espera 7.5s]            │                     t=12.6s
   │                           │
   │  GET /productos            │ ──────────────────►  t=12.6s
   │                           │◄── 200 OK {nuevos datos}
   │  notificar(datos_actualizados)               t≈12.7s
   │  intervalo_actual = 5s    │  ← RESET porque hubo cambio
```

**Clave entendida:** El `ETag` permite que el servidor responda `304 Not Modified` sin enviar el body completo, ahorrando ancho de banda. El cliente solo llama a `notificar()` cuando realmente hubo un cambio.

---

## ⭐ Reto 2 – Construcción del ServicioPolling (guiado por la IA)

---

**🧑‍💻 Alumno:**
Tengo la clase `Observable` del material. Ahora tengo que construir `ServicioPolling` encima. Por dónde empiezo con `_consultar()`?

**🤖 IA:**
Antes de escribir código, predice: ¿qué debería pasar si `/api/productos` responde con `304 Not Modified`?

**🧑‍💻 Alumno:**
Que los datos no cambiaron, entonces no debo notificar a los observadores, y debo aumentar el intervalo porque es inútil preguntar tan seguido.

**🤖 IA:**
Perfecto. ¿Y si responde con `200` pero el `ETag` es el mismo que el anterior?

**🧑‍💻 Alumno:**
Igual, no hubo cambio real. Aunque... ¿cómo sé si el ETag es el mismo si el servidor mandó `200`?

**🤖 IA:**
Buena pregunta. ¿Qué podrías comparar además del ETag para detectar si los datos realmente cambiaron?

**🧑‍💻 Alumno:**
Un hash del JSON. Si el hash es igual al anterior, los datos son iguales aunque el servidor no mande 304.

**🤖 IA:**
Exacto. Eso es lo que se llama "fallback": si el servidor no soporta ETag, tú calculas el hash del body. ¿Eso lo vas a guardar en la sesión o en la instancia de ServicioPolling?

**🧑‍💻 Alumno:**
En la instancia, como `self._ultimo_hash`. Así sobrevive entre ciclos de polling.

**🤖 IA:**
Ahora, una pregunta de verificación antes de pasar a `iniciar()`: ¿qué pasa si el timeout es de 10s y `_consultar()` no tiene ningún bloque `try/except`?

**🧑‍💻 Alumno:**
El `asyncio.TimeoutError` propagaría hasta `iniciar()` y rompería el ciclo `while`, matando el polling por completo. Necesito capturarlo dentro de `_consultar()`.

**🤖 IA:**
Correcto. Una excepción no capturada en `_consultar()` no debe matar el ciclo principal. ¿Ahora puedes implementar `iniciar()`?

**🧑‍💻 Alumno:**
Sí: `self._activo = True`, luego `while self._activo: await self._consultar(); await asyncio.sleep(self.intervalo_actual)`.

**🤖 IA:**
Hay un caso borde: ¿qué pasa si `detener()` se llama durante el `asyncio.sleep()`?

**🧑‍💻 Alumno:**
`asyncio.sleep()` termina en el tiempo configurado, y en la siguiente iteración del `while` revisa `self._activo` que ya es `False`, entonces sale limpiamente sin forzar cancelación.

---

## ⭐ Reto 3 – Discusión Socrática de Trade-offs

---

**🧑‍💻 Alumno:**
Tengo `ServicioPolling` con short polling, backoff hasta 60s, ETag, 3 observadores y timeout de 10s. Me haría las 4 preguntas una a una.

**🤖 IA:**
Primera pregunta: Tu Observable ejecuta los callbacks **síncronamente**. Si el observador de logs tarda 2 segundos en escribir a disco, ¿qué le pasa al intervalo de polling? ¿Cómo lo detectarías como desarrollador del cliente?

**🧑‍💻 Alumno:**
Si el callback tarda 2s y mi `intervalo_actual` es 5s, el ciclo real es 7s (5s sleep + 2s callback). Lo detectaría porque los timestamps en consola mostrarían diferencias de 7s en vez de 5s, aunque el intervalo configurado sea 5.

**🤖 IA:**
Perfecto. ¿Y cómo lo arreglarías sin cambiar la clase Observable?

**🧑‍💻 Alumno:**
Haría el callback asíncrono y cambiaría `cb(datos)` por `await cb(datos)` en `notificar()`. O crearía una tarea separada: `asyncio.create_task(cb(datos))`.

**🤖 IA:**
Segunda pregunta: Tu cliente lleva **20 consultas** recibiendo 503. Con backoff hasta 60s, ¿cuánto tiempo pasa hasta llegar al máximo? ¿Tiene forma de "rendirse" limpiamente?

**🧑‍💻 Alumno:**
Empiezo en 5s: 5→10→20→40→60→60→60... Llego al máximo en el 4to error. A partir de ahí queda en 60s para siempre porque el `while _activo:` no tiene límite de intentos.

**🤖 IA:**
¿Eso es un bug o una decisión de diseño?

**🧑‍💻 Alumno:**
Decisión de diseño para EcoMarket: siempre queremos datos frescos eventualmente. Pero si fuera crítico no desperdiciar recursos, agregaría un `max_intentos` y llamaría a `detener()` al alcanzarlo.

**🤖 IA:**
Tercera pregunta: Si decides cambiar a long polling, ¿qué tres cosas concretas cambian en el código de TU cliente?

**🧑‍💻 Alumno:**
1. Elimino `asyncio.sleep(self.intervalo_actual)` porque la "espera" la hace el servidor al retener la conexión.
2. Aumento el timeout de 10s a ~30s porque en long polling es normal que el servidor tarde.
3. Cuando recibo respuesta, lanzo la siguiente petición inmediatamente (sin sleep), simplificando el ciclo.

**🤖 IA:**
Excelente. Última pregunta: Agregas un 4° observador que tarda 500ms (animación en pantalla). ¿Puede afectar al observador de alertas críticas? ¿Cómo protege tu código a los rápidos de los lentos?

**🧑‍💻 Alumno:**
Si la animación está antes que las alertas en la lista `_observadores["datos_actualizados"]`, las alertas tardan 500ms más en ejecutarse. El `try/except` protege de *crashes* pero no de *lentitud*. Para proteger de lentitud necesito callbacks asíncronos con `asyncio.create_task()`.

---

### 📋 Resumen de 5 puntos (Reto 3)

1. **`INTERVALO_BASE = 5s`**: Los callbacks síncronos alargan el ciclo efectivo. Si `log_errores` tarda 2s, el ciclo real es 7s aunque `intervalo_actual` sea 5s.
2. **`INTERVALO_MAX = 60s`**: Se alcanza en el 4to error (5→10→20→40→60). Después el cliente sigue intentando cada 60s indefinidamente — decisión aceptable para EcoMarket.
3. **`detener()` con bandera `_activo`**: No cancela tareas a la fuerza; espera al siguiente `await asyncio.sleep()`. Garantiza que no queden peticiones en vuelo (invariante ✓).
4. **Migración a long polling**: Requiere eliminar `asyncio.sleep()`, aumentar `timeout` HTTP y lanzar petición inmediatamente tras cada respuesta.
5. **Protección de observadores**: El `try/except` en `notificar()` evita crashes en cascada, pero no retraso en cadena. Para observadores lentos → `asyncio.create_task(cb(datos))`.

> **Nota crítica al resumen de la IA:** La IA dijo que el backoff "reduce la carga del servidor". Lo que importa aquí es que protege el **ciclo de eventos del CLIENTE** de ejecutarse en bucle vacío constante. La reducción de carga en el servidor es un efecto secundario, no el objetivo principal desde la perspectiva del código cliente.

---

## 🚀 Reto 5 – Diseño de Migración a WebSocket

---

**🧑‍💻 Alumno:**
Mi arquitectura actual es: `Observable` (base) → `ServicioPolling` (hereda Observable) → observadores (funciones). ¿Qué métodos deben ser idénticos en `ServicioWebSocket` para que los observadores no cambien ni una línea?

**🤖 IA:**
Define la interfaz desde la perspectiva del código cliente. ¿Qué métodos llama tu código principal hoy?

**🧑‍💻 Alumno:**
```python
monitor = ServicioPolling(url, intervalo)
monitor.suscribir("datos_actualizados", actualizar_ui)
monitor.suscribir("error_servidor",     log_errores)
await monitor.iniciar()
monitor.detener()
```

**🤖 IA:**
¿Cuál de esos métodos cambiaría en `ServicioWebSocket`?

**🧑‍💻 Alumno:**
El constructor: ya no necesita `intervalo_seg` porque no hay polling. Pero `suscribir()`, `desuscribir()`, `iniciar()` y `detener()` deben ser idénticos. Esa sería la interfaz común.

**🤖 IA:**
Olvidaste un método. ¿Qué pasa cuando la conexión WebSocket se cae en medio de una sesión?

**🧑‍💻 Alumno:**
Necesito un método `reconectar()` o al menos un evento `"conexion_perdida"` para que la UI muestre "modo degradado". En polling no existe porque cada petición es independiente.

**🤖 IA:**
Exacto. Ese es el nuevo estado interno que `ServicioWebSocket` necesita que `ServicioPolling` no tenía.

---

### 🔄 Diagrama de estados del cliente WebSocket

```
         ┌─────────────┐
         │ Desconectado│◄──── detener()
         └──────┬──────┘
                │ iniciar()
                ▼
         ┌─────────────┐
         │  Conectando │
         └──────┬──────┘
          éxito │  falla
                ▼    └──────────────► Degradado (polling de respaldo)
         ┌─────────────┐                    │
         │  Conectado  │  conexión caída     │ servidor disponible
         └──────┬──────┘◄────────────────────┘
                │ desconexión detectada
                ▼
         ┌─────────────┐
         │  Degradado  │ → usa polling mientras reconecta
         └─────────────┘
```

### ✅ Lo que NO cambia gracias al Observer

| Componente | Cambia con WebSocket |
|------------|---------------------|
| `actualizar_ui()` | ❌ No — misma firma |
| `alerta_agotados()` | ❌ No — misma firma |
| `log_errores_servidor()` | ❌ No — misma firma |
| `Observable.suscribir()` | ❌ No — mismo método |
| `Observable.notificar()` | ❌ No — mismo método |
| `ServicioPolling` | ✅ Reemplazado por `ServicioWebSocket` |
| Constructor del monitor | ✅ Cambia (sin `intervalo_seg`) |
| Estado interno (ciclos, etag) | ✅ Cambia (añade estado conexión) |
