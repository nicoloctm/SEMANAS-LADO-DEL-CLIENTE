# Conversación Socrática - Server-Sent Events (Semana 6)

**Alumno Inexperto:** ¡Hola! Esta semana estamos viendo Server-Sent Events (SSE). ¿Me puedes ayudar a entenderlo? En la Semana 4 vimos Polling y sentí que lo dominaba, pero ahora el servidor toma la iniciativa y me confunde un poco.

**IA (Ingeniero Senior):** ¡Hola! Claro que sí. Para entenderlo rápido: imagina que Polling es como estar llamando por teléfono a un restaurante cada 5 minutos para preguntar "¿ya está mi comida?". La mayoría de las veces te dirán "No". SSE, en cambio, es como dejarles tu número y decirles "llámenme ustedes en cuanto esté lista". Mantienes tu teléfono encendido (la conexión HTTP abierta) y ellos te avisan solo cuando hay novedades.

**Alumno Inexperto:** ¡Ah, ya veo! Entonces con SSE el cliente abre una sola petición y el servidor va mandando las respuestas cuando quiere. ¿Y qué pasa si mi internet falla o se cae la conexión?

**IA:** Excelente pregunta. Aquí es donde entra la magia de SSE. El servidor le asigna un `id` a cada evento. Si tu internet falla, tu cliente recordará el último `id` que recibió. Al reconectarse, tu cliente le dirá al servidor: `Last-Event-ID: 45`. Así el servidor sabe desde dónde tiene que reenviarte los datos que te perdiste. 

**Alumno Inexperto:** ¡Qué listo! ¿Y cómo diferencio si es una alerta de stock o un cambio de precio?

**IA:** En el mensaje de texto que te envía el servidor, hay un campo llamado `event:`. Si dice `event: stock-critico`, tu cliente lee esa línea y ya sabe cómo procesar el campo `data:` que viene a continuación. Si no lo reconoces, simplemente lo ignoras sin crashear.

**Alumno Inexperto:** Comprendo. Pero tengo una duda: ¿Por qué no usar SSE para todo entonces? Por ejemplo, si el cliente también necesita enviarle cosas frecuentemente al servidor.

**IA:** Porque SSE es *unidireccional*. Es una carretera de un solo sentido: del servidor a ti. Si tú necesitas enviarle mucha información en tiempo real, necesitarías usar WebSockets (que veremos más adelante). Además, los navegadores (en HTTP/1.1) solo te dejan tener 6 conexiones abiertas al mismo tiempo por dominio. ¡Si abres muchas pestañas con SSE, bloquearás otras peticiones porque consumirás esos espacios!

**Alumno Inexperto:** Wow, eso es súper útil para mi examen práctico. Entendido: usar SSE cuando necesitamos actualizaciones del servidor en tiempo real y en un solo sentido. ¡Gracias por la paciencia!
