# 💬 Conversación Socrática – Semana 3
## Programación Asíncrona y Concurrencia en el Cliente
### Alumno: Estudiante de Sistemas (poca experiencia) | IA: Instructora

---

> *Esta conversación simula la interacción real entre un estudiante que está comenzando a entender la programación asíncrona en Python y una IA instructora que lo guía con preguntas socráticas a través de todos los retos de la Semana 3.*

---

## 🎬 Contexto de partida

---

**🧑‍💻 Alumno:**
Hola, estoy en la Semana 3 y honestamente no entendí nada del escenario. Dice que mi cliente se "congela" cuando hace peticiones... pero mi código sí funciona, yo lo probé y sí me devuelve los productos. ¿Cuál es el problema?

**🤖 IA:**
Me alegra que lo hayas probado. Ahora dime: cuando lo ejecutaste, ¿cuántos endpoints consultaste al mismo tiempo?

**🧑‍💻 Alumno:**
Pues uno... `/productos`. ¿Por qué?

**🤖 IA:**
Exacto. ¿Y qué crees que pasaría si necesitaras consultar `/productos`, `/categorias`, `/perfil` y `/notificaciones` *a la vez*, y cada uno tardara 500ms en responder?

**🧑‍💻 Alumno:**
Pues... los llamaría uno tras otro, ¿no? Primero productos, luego categorias... ah espera, ¿eso sería 2 segundos en total?

**🤖 IA:**
Correcto. Ahora una pregunta más importante: ¿tienen esas 4 peticiones alguna dependencia entre sí? ¿Necesitas el resultado de productos para poder pedir categorías?

**🧑‍💻 Alumno:**
No, son independientes. Son datos distintos...

**🤖 IA:**
Entonces, si son independientes, ¿por qué esperarías a que una termine para lanzar la siguiente?

**🧑‍💻 Alumno:**
¡Ah! Entendí. Las podría lanzar todas a la vez y el servidor las procesa al mismo tiempo, y yo solo espero a que lleguen las respuestas. ¡Eso ahorraría tiempo!

**🤖 IA:**
Exactamente. Eso se llama **concurrencia**. Y ahí empieza el Reto 1.

---

## ⭐ Reto 1: Cartógrafo de Modelos de Concurrencia

---

**🧑‍💻 Alumno:**
Ok, el reto dice que compare callbacks, futures y async/await. Pero yo nunca he usado ninguno de esos en Python. Solo sé `requests.get()`. ¿Por dónde empiezo?

**🤖 IA:**
Antes de ver código, dime: ¿qué crees que significa que una función sea "bloqueante"?

**🧑‍💻 Alumno:**
¿Qué... bloquea algo? No sé exactamente.

**🤖 IA:**
Piénsalo así: cuando llamas a `requests.get("url")`, ¿tu programa puede hacer *otra cosa* mientras espera la respuesta?

**🧑‍💻 Alumno:**
No... el programa se queda ahí esperando. Ya veo, eso es bloquear. El hilo no puede hacer nada más.

**🤖 IA:**
Perfecto. Ahora, ¿puedes imaginar una forma de lanzar la petición y decirle a Python "avísame cuando llegue la respuesta, mientras tanto yo hago otra cosa"?

**🧑‍💻 Alumno:**
Sería como... dejar un mensaje y esperar que me llamen. Tipo callback.

**🤖 IA:**
Exacto. Eso es el modelo de **callbacks**. El problema es: ¿qué pasa si necesitas hacer 5 cosas en secuencia, cada una dependiendo de la anterior?

**🧑‍💻 Alumno:**
Tendría un callback dentro de un callback dentro de otro callback... eso se ve horrible.

**🤖 IA:**
Se llama "callback hell". Por eso evolucionó a **Futures/Promises**: en lugar de pasar una función, recibes un objeto que *representa el resultado futuro* y puedes encadenar operaciones. ¿Cuál ves más legible?

**🧑‍💻 Alumno:**
El de futures. Pero el reto dice que async/await es el mejor...

**🤖 IA:**
¿Por qué crees que async/await mejoró a los Futures?

**🧑‍💻 Alumno:**
Porque... ¿se ve como código normal? Sin el `.then()` y `.catch()` encadenados.

**🤖 IA:**
Correcto. Es la misma mecánica por debajo, pero con sintaxis síncrona. Ahora ya puedes responder el reto: ¿qué modelo elegirías para EcoMarket y por qué?

**🧑‍💻 Alumno:**
Async/await, porque es más legible y tiene `gather()` para lanzar todo en paralelo. Además Python moderno ya lo soporta bien.

---

### 📊 Tabla entregable – Reto 1

| Modelo | Legibilidad | Manejo de errores | Composición paralela | Elección |
|--------|------------|-------------------|----------------------|----------|
| Callbacks | ⭐ | Difícil (por callback) | Manual | ❌ |
| Futures/ThreadPool | ⭐⭐⭐ | `as_completed` + try/except | `concurrent.futures` | ✅ Para I/O con hilos |
| Async/Await (asyncio) | ⭐⭐⭐⭐⭐ | `try/except` normal | `asyncio.gather()` | ✅ **Elegido para EcoMarket** |

**Justificación:** Para EcoMarket con 4+ peticiones independientes y requisito de baja latencia, `async/await` con `aiohttp` es la opción más legible, eficiente y mantenible. La transición desde `requests` es directa: misma lógica de negocio, solo cambia el motor de transporte.

---

## ⭐ Reto 2: Anatomista del Event Loop

---

**🧑‍💻 Alumno:**
Ahora tengo que entender qué pasa "por debajo" con `asyncio.run()`. Honestamente no entiendo para qué sirve ese `await` antes de `asyncio.gather()`.

**🤖 IA:**
Interesante. Cuando escribes `resultado = await algo()`, ¿qué le estás diciendo a Python?

**🧑‍💻 Alumno:**
¿Espera aquí hasta que `algo()` termine?

**🤖 IA:**
Eso es lo que *parece*. Pero hay algo más. Cuando haces `await`, ¿el hilo se bloquea o puede hacer otra cosa?

**🧑‍💻 Alumno:**
Ahh... ¿puede hacer otra cosa? Por eso es asíncrono. O sea, `await` no es "espera aquí parado", sino "cede el control al event loop para que haga otra tarea mientras".

**🤖 IA:**
Exacto. `await` es un **punto de cesión**. Ahora, cuando ejecutas `asyncio.gather(tarea1, tarea2)`, ¿cuántas tareas se están ejecutando al mismo tiempo *realmente*?

**🧑‍💻 Alumno:**
Una sola, porque es un solo hilo. Pero el event loop las intercala cuando una cede con `await`.

**🤖 IA:**
Correcto. Entonces, si `/categorias` llega antes que `/productos`, ¿qué hace el event loop?

**🧑‍💻 Alumno:**
Procesa `/categorias` primero, aunque yo las haya lanzado en ese orden. El orden de procesamiento depende de cuál llegue primero, no de cómo las escribí.

---

### 📐 Diagrama temporal – Reto 2 (redibujado con palabras propias)

```
t=0ms    asyncio.run() crea el event loop
t=1ms    gather() registra: tarea_productos (ESPERANDO) + tarea_categorias (ESPERANDO)
t=2ms    event loop envía petición HTTP /productos → queda ESPERANDO
t=3ms    event loop envía petición HTTP /categorias → queda ESPERANDO
t=103ms  ← llega respuesta de /categorias (100ms de latencia)
t=103ms  event loop activa tarea_categorias → ejecuta resp.json() → COMPLETADA
t=200ms  ← llega respuesta de /productos (200ms de latencia)
t=200ms  event loop activa tarea_productos → ejecuta resp.json() → COMPLETADA
t=201ms  gather() retorna [datos_productos, datos_categorias]
t=202ms  asyncio.run() finaliza y cierra el event loop
```

**Concepto corregido:** Antes creía que `await` significaba "el hilo espera bloqueado". Ahora entiendo que es un punto donde el hilo *cede el control* y puede atender otras tareas mientras la I/O está en progreso.

---

## ⭐ Reto 3: Constructor del Cliente Asíncrono

---

**🧑‍💻 Alumno:**
Tengo que convertir el cliente síncrono de Semana 2 a asíncrono. Empecé con `listar_productos` pero me da error: `RuntimeWarning: coroutine 'listar_productos' was never awaited`. ¿Qué significa eso?

**🤖 IA:**
Antes de buscar la solución, dime: si una función es `async def`, ¿qué devuelve cuando la llamas sin `await`?

**🧑‍💻 Alumno:**
¿Un objeto coroutine? No los datos reales...

**🤖 IA:**
Exacto. Una coroutine es como una receta: describe qué hacer, pero no lo hace hasta que el event loop la ejecuta. ¿Dónde crees que olvidaste el `await`?

**🧑‍💻 Alumno:**
En donde la llamo. Escribí `resultado = listar_productos(session)` en vez de `resultado = await listar_productos(session)`.

**🤖 IA:**
Correcto. Ahora otra pregunta: ¿Por qué pasamos `session` como parámetro en vez de crear una nueva dentro de cada función?

**🧑‍💻 Alumno:**
Para... ¿no crear muchas sesiones? Supongo que cada sesión usa memoria.

**🤖 IA:**
¿Y qué pasa con las conexiones TCP cuando creas una sesión nueva por cada petición?

**🧑‍💻 Alumno:**
Se establece y rompe una conexión nueva cada vez. Eso es lento y desperdicia recursos. Con una sola sesión reutilizas el keep-alive.

**🤖 IA:**
Y ahora, ¿qué pasa si `gather()` lanza una excepción y no estás usando `return_exceptions=True`?

**🧑‍💻 Alumno:**
Que cancela todas las otras tareas aunque hayan terminado bien... y pierdo su trabajo. Por eso el invariante dice que SIEMPRE hay que usar `return_exceptions=True` cuando las tareas son independientes.

---

El código completo del Reto 3 está en → [cliente_async_ecomarket.py](./cliente_async_ecomarket.py)

---

## ⭐ Reto 4: Ingeniero de Timeouts y Cancelación

---

**🧑‍💻 Alumno:**
No entiendo la diferencia entre el timeout de `aiohttp.ClientTimeout` y usar `asyncio.wait_for()`. ¿No es lo mismo?

**🤖 IA:**
Buena pregunta. Si pones `aiohttp.ClientTimeout(total=10)` en toda la sesión, ¿qué timeout tienen todas tus peticiones?

**🧑‍💻 Alumno:**
10 segundos cada una... igual.

**🤖 IA:**
¿Y si necesitas que `/perfil` tenga 2 segundos pero `/productos` tenga 5? ¿Puedes hacer eso con solo `ClientTimeout`?

**🧑‍💻 Alumno:**
No, sería el mismo para todas. Entonces `asyncio.wait_for()` me permite poner un timeout *diferente* por petición, ¿verdad?

**🤖 IA:**
Exacto. Y hay otra diferencia: `asyncio.wait_for` envuelve *cualquier* awaitable, no solo peticiones HTTP. Ahora, cuando se cancela una tarea con `CancelledError`, ¿debes suprimirlo o manejarlo?

**🧑‍💻 Alumno:**
Manejarlo... para limpiar recursos. Si lo suprimo, la sesión podría quedar abierta.

**🤖 IA:**
Perfecto. Esa es la regla del invariante: `CancelledError` para cleanup, nunca suprimirlo. ¿Por qué cancelas las otras tareas si `/perfil` retorna 401?

**🧑‍💻 Alumno:**
Porque sin autenticación, los datos de los otros endpoints no me sirven de nada. No tiene sentido seguir esperando por productos si no tengo permiso de ver nada.

---

El código completo está en → [coordinador_async.py](./coordinador_async.py)

---

## ⭐ Reto 5: Constructor de Semáforo con Rate Limiting

---

**🧑‍💻 Alumno:**
Entiendo el Semaphore básico, pero ¿qué es un "token bucket"? El nombre suena raro.

**🤖 IA:**
Imagina un cubo con fichas (tokens). Cada segundo, se agregan N fichas al cubo (hasta un máximo). Para hacer una petición, necesitas "tomar" una ficha. Si el cubo está vacío, ¿qué haces?

**🧑‍💻 Alumno:**
Espero a que se llene... o sea, espero a que pase el tiempo necesario para que haya una ficha disponible.

**🤖 IA:**
Correcto. ¿Y la diferencia con simplemente rechazar la petición?

**🧑‍💻 Alumno:**
Con token bucket la petición *espera en cola* en vez de fallar. Eso es mejor para el usuario porque eventualmente sí se hace.

**🤖 IA:**
Exacto. Ahora, si combinas el Semaphore (máx N en vuelo) con el RateLimiter (máx M/segundo), ¿qué límite se aplica primero?

**🧑‍💻 Alumno:**
El RateLimiter... porque controla cuántas por segundo entran al pipeline. Y luego el Semaphore controla cuántas están activas simultáneamente. Son dos controles distintos.

---

El código completo está en → [throttle.py](./throttle.py)

---

## ⭐ Reto 6: Crítico de Decisiones de Concurrencia

---

**🧑‍💻 Alumno:**
La IA me pidió que justificara por qué usé `gather()` en vez de `wait()`. Honestamente lo usé porque lo vi en el código base del reto... ¿eso está mal?

**🤖 IA:**
No está mal empezar así. Pero ahora que lo implementaste, ¿puedes explicar *cuándo* `gather()` sería peor que `wait(FIRST_COMPLETED)`?

**🧑‍💻 Alumno:**
Si el usuario quiere ver datos *conforme van llegando* en la UI, `gather()` lo hace esperar a que *todo* esté listo antes de mostrar algo. Con `wait(FIRST_COMPLETED)` podría mostrar productos apenas lleguen.

**🤖 IA:**
Muy bien. ¿Y qué sacrificas con `wait(FIRST_COMPLETED)`?

**🧑‍💻 Alumno:**
Más complejidad en el código... hay que manejar el loop, el `pendientes` set, procesar cada tarea conforme llega. Con `gather` es una línea.

**🤖 IA:**
¿Y el semáforo de 5? ¿Por qué 5 y no 10 o 20?

**🧑‍💻 Alumno:**
Honestamente... lo puse porque el código de ejemplo decía 5. No tengo una justificación real.

**🤖 IA:**
Esa es una respuesta honesta. ¿Qué necesitarías para elegir el número correcto?

**🧑‍💻 Alumno:**
Métricas del servidor: cuántas conexiones simultáneas puede manejar, cuál es su límite de rate, pruebas de carga. Sin eso, cualquier número es arbitrario.

---

Las decisiones de arquitectura están documentadas en → [ADR_concurrencia.md](./ADR_concurrencia.md)

---

## 🚀 Reto 7: Comparador de Estrategias de Coordinación

---

**🧑‍💻 Alumno:**
El resultado del benchmark de `comparacion_coordinacion.py` me sorprendió. La estrategia 4 (`FIRST_EXCEPTION`) fue la MÁS rápida con 0.2 segundos... ¿eso es bueno?

**🤖 IA:**
¿Por qué crees que fue tan rápida?

**🧑‍💻 Alumno:**
Porque en cuanto llegó `/categorias` con error (era la más rápida, 0.1s), abortó todo. Las demás se cancelaron.

**🤖 IA:**
Entonces, ¿esa velocidad es una ventaja o un problema para el dashboard?

**🧑‍💻 Alumno:**
¡Un problema! Canceló `/productos` y `/perfil` que venían bien. O sea, fue "rápido" porque hizo menos trabajo, no porque fuera más eficiente. Velocidad sin utilidad no sirve.

**🤖 IA:**
Excelente razonamiento. ¿Cuándo sería correcto usar `FIRST_EXCEPTION`?

**🧑‍💻 Alumno:**
Cuando las 4 peticiones tienen dependencia entre sí y si una falla las demás ya no sirven. Por ejemplo, si primero autentico y si falla la auth, no tiene sentido pedir los datos protegidos.

---

Los resultados completos están en → [comparacion_coordinacion.py](./comparacion_coordinacion.py)

---

## ⭐ Reto 8: Diseñador de Suite de Pruebas Asíncronas

---

**🧑‍💻 Alumno:**
Los tests me dan error: `RuntimeError: no running event loop`. ¿Qué está pasando?

**🤖 IA:**
¿Cómo definiste tus funciones de test? ¿Como `def test_...` o como `async def test_...`?

**🧑‍💻 Alumno:**
Como `def` normal...

**🤖 IA:**
Si tu función de test no es `async`, ¿puede hacer `await` en su interior?

**🧑‍💻 Alumno:**
No. Entonces tengo que poner `async def test_...` y el decorador `@pytest.mark.asyncio` para que pytest sepa cómo correrlo.

**🤖 IA:**
Exacto. Y en el archivo de configuración, ¿qué necesitas para que pytest-asyncio funcione automáticamente sin decorar cada test?

**🧑‍💻 Alumno:**
El `pytestmark = pytest.mark.asyncio` al inicio del archivo, que aplica el marker a todos los tests del módulo.

**🤖 IA:**
Correcto. Ahora dime: si un test de concurrencia pasa 9 de 10 veces, ¿es un test válido?

**🧑‍💻 Alumno:**
No... porque depende del timing. Los tests asíncronos deben ser deterministas. Por eso usamos `aioresponses` para mockear las respuestas HTTP en vez de llamar al servidor real.

---

Los 20 tests están en → [test_cliente_async.py](./test_cliente_async.py)

---

## 🚀 Reto 9: Benchmark Síncrono vs. Asíncrono

---

**🧑‍💻 Alumno:**
Ejecuté el benchmark y para latencia 0ms el asíncrono solo fue 1.1x más rápido que el síncrono. Esperaba algo mucho mayor, ¿por qué?

**🤖 IA:**
Piénsalo: si cada petición tarda 0ms, ¿cuánto tiempo "ahorras" al ejecutarlas en paralelo?

**🧑‍💻 Alumno:**
Nada... si no hay espera, no hay nada que aprovechar. El overhead del event loop incluso puede hacerlo un poco más lento.

**🤖 IA:**
Exacto. La asincronía solo gana cuando hay **tiempo de espera de I/O** que aprovechar. ¿En qué latencia fue mayor la diferencia?

**🧑‍💻 Alumno:**
Con 500ms. El speedup fue de 8-10x para 4 peticiones. Porque 4×500ms=2s síncrono vs ~520ms asíncrono.

**🤖 IA:**
¿Y cuál es el punto de cruce según tu benchmark?

**🧑‍💻 Alumno:**
Con 100ms de latencia, asíncrono empieza a ganar claramente desde 3 peticiones en adelante. Con menos de 3, la diferencia no justifica la complejidad.

---

**🧑‍💻 Alumno (reflexión final):**
Ahora entiendo por qué el dashboard de EcoMarket necesita async. Tenemos 4 peticiones, cada una tarda ~200-300ms, y los usuarios son intolerantes a esperas >1s. Síncrono daría ~1200ms, asíncrono da ~350ms. La migración vale completamente la pena.

**🤖 IA:**
Esa conclusión llegó de los datos, no de una intuición. Eso es exactamente lo que busca el reto. ¿Cambiaste alguna decisión de diseño después de ver los resultados?

**🧑‍💻 Alumno:**
Sí. Antes pensaba que el semáforo de 5 era suficiente para todo. Pero el benchmark muestra que para creación masiva de 20 productos con 100ms de latencia, elevar el semáforo a 10 reduce el tiempo a la mitad sin sobrecargar el servidor. Documenté eso en el ADR-003 como "en revisión".

---

## 📊 Resumen de Entregables

| Reto | Archivo | Estado |
|------|---------|--------|
| Reto 1 | Tabla comparativa (en este doc) | ✅ |
| Reto 2 | Diagrama temporal (en este doc) | ✅ |
| Reto 3 | [cliente_async_ecomarket.py](./cliente_async_ecomarket.py) | ✅ |
| Reto 4 | [coordinador_async.py](./coordinador_async.py) | ✅ |
| Reto 5 | [throttle.py](./throttle.py) | ✅ |
| Reto 6 | [ADR_concurrencia.md](./ADR_concurrencia.md) | ✅ |
| Reto 7 | [comparacion_coordinacion.py](./comparacion_coordinacion.py) | ✅ |
| Reto 8 | [test_cliente_async.py](./test_cliente_async.py) | ✅ |
| Reto 9 | [benchmark_sync_vs_async.py](./benchmark_sync_vs_async.py) | ✅ |

---

## 🪞 Reflexión Metacognitiva Final

**Lo que entendía mal antes de esta semana:**
- Creía que `await` bloqueaba el hilo. Ahora sé que es un punto de cesión.
- Creía que concurrencia = paralelismo. Son cosas distintas.
- Creía que `async/await` hacía el código mágicamente rápido. La ganancia depende de cuánto I/O hay que esperar.

**Lo que aprendí que la IA puede fallar:**
- La IA genera `gather()` sin `return_exceptions=True` por defecto (modo optimista).
- La IA puede crear sesiones dentro de cada función en vez de pasarlas como parámetro.
- La IA puede mezclar `requests` (síncrono) dentro de funciones `async` si no se lo indicas.

**Invariante más importante que llevaré a Semana 4:**
> `await` no es "esperar" — es "ceder el control y volver cuando haya algo que hacer".
