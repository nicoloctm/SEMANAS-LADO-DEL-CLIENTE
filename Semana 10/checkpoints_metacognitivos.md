# Respuestas a Checkpoints Metacognitivos — Semana 10

Este documento contiene las reflexiones del equipo sobre los aprendizajes de la Semana 10, evaluadas bajo la micro-rúbrica de calidad (nivel Transferible).

---

### Pregunta 1: ¿Puedo explicar verbalmente, en 2 minutos, qué hace el `ClienteRobusto` sin mencionar ningún lenguaje de programación?

**Respuesta (Nivel Analítico/Transferible):**
Sí. El `ClienteRobusto` actúa como un **mayordomo inteligente** de las comunicaciones entre nuestra aplicación de inventario y el servidor principal. Su trabajo consiste en asegurar que las peticiones se realicen de forma segura y ordenada.
1. Antes de enviar cualquier mensaje al servidor, verifica si nuestro **pase de entrada** (el token de acceso) sigue siendo válido. Si está por vencer, va al mostrador de seguridad y lo renueva antes de hacer la llamada real, asegurándose de que una sola persona del equipo haga la fila de renovación si varios lo necesitan al mismo tiempo.
2. Si el servidor empieza a fallar repetidamente, el mayordomo levanta una **barrera protectora** (abre el circuito) y le dice a nuestra aplicación inmediatamente "el servidor no está disponible" sin ir a tocar la puerta del servidor, dándole tiempo de recuperarse.
3. Cada cierto tiempo, el mayordomo deja pasar **una sola petición de prueba** para verificar si el servidor ya está de vuelta. Si responde bien, quita la barrera y todo vuelve a la normalidad; si falla, la vuelve a poner.

*Acción concreta para WebSocket:* Al migrar a canales en tiempo real, el mayordomo ya no medirá errores de "peticiones individuales fallidas", sino la calidad y persistencia del canal completo (desconexiones repentinas, falta de respuesta/ping).

---

### Pregunta 2: ¿Usé la IA para generar código en algún reto sin entender el problema primero? Si sí: ¿cuál fue el costo? ¿Qué parte del código no puedo explicar con mis palabras hoy?

**Respuesta (Nivel Analítico/Transferible):**
No, no se utilizó la IA para generar código a ciegas. Sin embargo, sí recurrimos a la IA en las Semanas 8 y 9 para entender la teoría del **padding en Base64URL** (restauración del carácter `=`) y el funcionamiento de la tarea compartida en Python (`asyncio.create_task` para el refresco singleton).
El costo de investigar estos conceptos sin IA habría sido horas de lectura dispersa en especificaciones RFC. Hoy podemos explicar cada línea del código:
- La decodificación del JWT toma el segundo segmento del token, calcula el residuo de su longitud módulo 4, agrega los caracteres `=` faltantes para cumplir con el estándar Base64 clásico, y luego lo decodifica usando un mapeo seguro de caracteres URL (`-` y `_`).
- El refresco singleton guarda la referencia de la corutina asíncrona activa en `self._refresh_task`. Si otra petición entra mientras se ejecuta, simplemente espera el mismo objeto (`await self._refresh_task`), evitando peticiones duplicadas.

*Acción concreta para mejorar:* Implementaremos pruebas de estrés de concurrencia locales utilizando simuladores de peticiones simultáneas para comprobar visualmente que nunca se duplican peticiones HTTP al endpoint de login.

---

### Pregunta 3: Si mañana el CTO de EcoMarket me pregunta "¿por qué el Circuit Breaker no abre con errores 401?", ¿tengo una respuesta de 30 segundos que un no-programador pueda seguir?

**Respuesta (Nivel Analítico/Transferible):**
"CTO, un error 401 significa 'Acceso denegado'. Esto es el equivalente a que un cliente intente entrar a nuestra tienda con una contraseña incorrecta. No significa que las cajas registradoras o el servidor estén rotos; simplemente significa que las credenciales del cliente no sirven.
El Circuit Breaker es un interruptor de seguridad de red: solo debe saltar si el servidor se cae, si hay problemas de red o si el servidor está sobrecargado (errores 500 o de timeout). Si apagáramos el sistema entero (abrir el circuito) cada vez que un usuario escribe mal su contraseña, un atacante o un error simple de un usuario bloquearía el uso de la aplicación a todos los demás operadores."

*Acción de diseño:* Esta distinción evita el "Hard Gate de Seguridad". Si el disyuntor reaccionara a errores 4xx, una clave expirada provocaría que todo el cliente entrara en fail-fast injustificado.

---

### Pregunta 4: ¿Estoy listo para la Semana 11 (WebSocket)? ¿Qué concepto de las Semanas 6–9 necesito repasar antes?

**Respuesta (Nivel Transferible):**
Estamos listos a nivel de lógica de arquitectura distribuida, pero necesitamos repasar:
1. **La gestión de eventos asíncronos y colas:** En la Semana 7 (SSE) manejamos un stream unidireccional donde el servidor nos empujaba datos línea a línea. WebSocket será bidireccional, lo que significa que el cliente enviará y recibirá concurrentemente. Necesitamos repasar cómo coordinar la lectura y escritura asíncronas sin bloquear el loop de eventos.
2. **Re-autenticación en conexiones persistentes:** Los JWT expiran cada cierto tiempo. En HTTP, cada petición lleva un header fresco. En WebSocket, una vez establecida la conexión TCP (handshake), no hay nuevos headers HTTP en cada mensaje. Necesitamos repasar y diseñar cómo re-autenticar o refrescar la conexión WebSocket enviando un mensaje especial de autenticación a través del propio canal sin tener que reconectar todo el socket.
