# Conversación Socrática - Decisiones de Diseño (Semana 5)

**Alumno Inexperto:** ¡Hola! Estoy revisando mi cliente del Hito 1 antes del examen práctico. Soy estudiante de segundo semestre y necesito entender por qué hice lo que hice. ¿Me ayudas preguntándome una por una sobre mis decisiones?

**IA (Arquitecto Senior):** ¡Hola! Claro, vamos a revisar tu arquitectura como si estuviéramos en una revisión técnica real. Aquí va la primera pregunta: 
1. ¿Qué timeout configuraste para las peticiones HTTP de tu cliente y por qué elegiste ese valor? ¿Qué pasa en tu cliente si el timeout es demasiado corto? ¿Y si es demasiado largo?

**Alumno Inexperto:** Puse un timeout de 10 segundos. Si es demasiado corto (como 1 segundo), cualquier demora pequeña en la red haría que mi cliente aborte peticiones que sí iban a funcionar. Si es muy largo (como 60 segundos), mi cliente se quedaría "congelado" esperando una respuesta que tal vez nunca llegue, y la UI se vería trabada.

**IA:** ¡Buena respuesta! Has captado el equilibrio perfecto. 
2. Cuando tu cliente recibe un error 5xx, ¿qué hace? ¿Reintenta inmediatamente o espera? ¿Cuántas veces reintenta y por qué ese número?

**Alumno Inexperto:** Si recibo un 5xx, mi cliente sabe que es culpa del servidor. No reintenta inmediatamente porque si el servidor está caído, bombardearlo lo empeora. Espera usando un "backoff" (duplicando el tiempo de espera). Puse un límite de 3 reintentos para no quedarme intentando para siempre, porque si falla 3 veces, probablemente el servidor necesite mantenimiento.

**IA:** Exacto, el backoff evita el efecto "thundering herd" que tumba servidores. 
3. En tu Monitor de Inventario (polling), ¿elegiste short polling o long polling? ¿Por qué esa elección y no la otra? ¿Qué le haría tu decisión a la batería de un dispositivo móvil que ejecute tu cliente?

**Alumno Inexperto:** Usé short polling adaptativo. Elegí short polling porque es más simple de implementar con HTTP estándar y no requiere mantener la conexión abierta del lado del servidor todo el tiempo como el long polling. Pero, en un móvil, despertar la antena cada 5 segundos para hacer peticiones gasta mucha batería. Por eso lo hice adaptativo, para que si no hay cambios, el tiempo suba hasta 60s y ahorre energía.

**IA:** Muy buen análisis del impacto en el cliente físico. 
4. ¿Cuántos observadores implementaste en el Observer? Si mañana necesitas agregar un cuarto observador que envíe notificaciones por email, ¿qué líneas de tu código tendrías que modificar?

**Alumno Inexperto:** Implementé 3 observadores (UI, alertas y logs). Si agrego un cuarto para email, ¡no modificaría ninguna línea de `ServicioPolling`! Solo crearía la nueva clase `ObservadorEmail` y agregaría una línea `monitor.suscribir(ObservadorEmail())` en mi función principal (el `main`).

**IA:** ¡Excelente! Ese es el corazón del desacoplamiento.
5. Si mirases tu código hoy, después de 4 semanas del curso, ¿qué es lo primero que cambiarías o mejorarías? ¿Por qué eso específicamente?

**Alumno Inexperto:** Creo que mejoraría cómo ejecuto los observadores. Ahorita `_notificar()` los llama uno por uno de forma síncrona. Si el observador de logs tarda en escribir al disco, retrasa todo el ciclo de polling. Cambiaría eso para que se disparen como tareas asíncronas con `asyncio.create_task()`.

**IA:** ¡Perfecto! Resumo nuestras 5 decisiones de diseño:
1. **TIMEOUT**: 10s → Trade-off: Evita congelamientos largos vs. abortar prematuramente. Decisión: Balance adecuado para no bloquear UI.
2. **REINTENTOS 5xx**: 3 con backoff → Trade-off: Tolerancia a fallos temporales vs. retraso en notificar error final. Decisión: Protege al servidor y evita loops infinitos.
3. **POLLING**: Short polling adaptativo → Trade-off: Facilidad técnica vs. consumo de batería/red. Decisión: Mitigado con el backoff progresivo (hasta 60s).
4. **OBSERVADORES**: 3 (desacoplados) → Trade-off: Agrega estructura/capas vs. llamar funciones directo. Decisión: Permite escalabilidad sin tocar la lógica core.
5. **MEJORA FUTURA**: Callbacks asíncronos → Trade-off: Complejidad en el event loop vs. velocidad. Decisión: Necesario para evitar que observadores lentos retrasen el ciclo.
