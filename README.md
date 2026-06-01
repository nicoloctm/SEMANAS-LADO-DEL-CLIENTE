# Semana 1: Arquitectura Cliente-Servidor y Fundamentos HTTP
## Reporte de Entregables del Estudiante (Modelo AETL)

**Institución:** Universidad Autónoma de Nayarit (UAN)  
**Curso:** Programación Distribuida del Lado del Cliente  
**Programa:** Licenciatura en Sistemas Computacionales  
**Estudiante:** Angel Adriel Soria Macias 
**Docente:** Dr. Eligardo Cruz Sánchez  

---

## FASE 1: COMPRENDE

### Reto 1: Explorador de Anatomía HTTP

#### 1. Diálogo Socrático con la IA (Tutor de Redes)

*   **Tutor Socrático (IA):** Hola. Veo que estás trabajando en la API de "EcoMarket". Empecemos por entender la anatomía de HTTP. ¿Sabrías decirme qué diferencia hay entre los headers de request (petición) y response (respuesta) usando ejemplos de tu dominio?
*   **Estudiante (Aprendiz):** Creo que los headers de request son metadatos que el cliente le envía al servidor, por ejemplo, para identificarse o decir qué formato espera. Y los de response los manda el servidor de vuelta con información sobre la respuesta.
*   **Tutor Socrático (IA):** ¡Exacto! Los has definido muy bien. En el contexto de EcoMarket, cuando un productor añade un producto:
    *   **Request Header:** `Authorization: Bearer eyJhbGci...` (para verificar tu identidad) y `Accept: application/json` (le dices: "quiero que me respondas en JSON").
    *   **Response Header:** `Content-Type: application/json` (el servidor te confirma: "aquí tienes los datos formateados en JSON") y `Content-Length: 350` (indica el tamaño exacto en bytes de la respuesta).
*   **Tutor Socrático (IA):** Ahora, hablemos de los métodos HTTP. Si elegimos mal un método para interactuar con EcoMarket, podemos tener problemas graves de red o de negocio. Te planteo dos preguntas socráticas para descubrir más:
    1. Si el servidor te responde con un JSON de productos pero no incluye el header `Content-Type: application/json` (o dice `Content-Type: text/plain`), ¿cómo sabrá tu cliente (como `fetch()`) cómo interpretar esa respuesta de forma segura?
    2. Si tu cliente intenta crear un producto usando `POST` pero no le envías el header `Content-Type: application/json`, ¿cómo sabrá el servidor qué tipo de datos viajan en el cuerpo del mensaje?

#### 2. Respuestas a las Preguntas Socráticas
1. **Respuesta a la pregunta 1:** Si el servidor no envía `Content-Type: application/json` y en su lugar envía `text/plain`, al intentar ejecutar `response.json()` en el código JavaScript frontend, el navegador no sabrá con certeza si el formato es un JSON válido o texto plano. Además, si el formato real fuera HTML debido a un fallo del servidor, el código intentará parsearlo como JSON a ciegas, arrojando una excepción de parseo críptica (`Unexpected token <`) que congelará la ejecución de la UI si no está atrapado en un try/catch.
2. **Respuesta a la pregunta 2:** Si el cliente hace una petición `POST` con un cuerpo JSON sin el header `Content-Type: application/json`, el framework del servidor (el backend) no sabrá cómo deserializar el flujo de bytes entrante. Pensará que es texto crudo (`text/plain`) o datos de un formulario URL-encoded. Como consecuencia, el backend no inyectará las propiedades en el objeto de la petición, interpretará el cuerpo como vacío y devolverá un error `400 Bad Request` o fallará en las validaciones de campos obligatorios como el nombre o precio.

#### 3. Escenarios de Uso Incorrecto de Métodos HTTP en EcoMarket
*   **Escenario 1: GET en lugar de POST para el Registro/Inicio de Sesión (Seguridad)**
    *   *Problema:* Si el cliente envía las credenciales del productor a través de un endpoint como `GET /api/login?usuario=productor42&pass=secreto123`, los datos sensibles se incrustan en la URL de la petición.
    *   *Consecuencia:* Las credenciales quedan guardadas de forma permanente en el historial del navegador del usuario, en los logs del servidor proxy de red, en los registros del servidor web y en las herramientas de analítica, permitiendo que cualquier persona con acceso al sistema comprometa la cuenta del productor.
*   **Escenario 2: POST en lugar de PATCH para Actualizar Inventario (Duplicidad por falta de idempotencia)**
    *   *Problema:* Un productor desea actualizar el inventario disponible de manzanas orgánicas de 10 a 15 kg. Si implementamos el endpoint como `POST /api/productos/12/actualizar-stock` enviando `{"incrementar": 5}`, y el cliente sufre un retraso de red, el usuario desesperado dará click varias veces al botón "Guardar".
    *   *Consecuencia:* Como `POST` no es un método idempotente, cada petición se procesará de forma independiente en el servidor. El servidor incrementará el stock 5 veces de forma acumulativa, dejando el inventario final en 35 kg en lugar de los 15 kg correctos. Lo correcto sería usar `PATCH` o `PUT` enviando el stock final absoluto: `{"stock": 15}`.
*   **Escenario 3: GET en lugar de DELETE para Eliminar del Catálogo (Inconsistencia y automatización destructiva)**
    *   *Problema:* Diseñar el endpoint de borrado de un producto como `GET /api/productos/12/eliminar`.
    *   *Consecuencia:* Como `GET` es por definición un método seguro que no debe alterar el estado del servidor, los navegadores precargan enlaces en segundo plano para acelerar la navegación, y los motores de búsqueda (como Googlebot) rastrean automáticamente todos los enlaces del sitio. Al entrar un robot indexador al panel del productor, recorrerá todos los enlaces de eliminación en segundo plano, borrando accidentalmente todo el catálogo de productos sin interacción humana directa.

#### 4. Reflexión sobre el Diálogo con la IA
El diálogo con la IA me permitió comprender que los protocolos web no son reglas arbitrarias de sintaxis, sino un contrato lógico formal entre el cliente y el servidor. Aprendí que elegir el método correcto según su semántica (seguro e idempotente) previene catástrofes de seguridad y duplicación de datos en producción. Finalmente, asimilé la importancia de los headers como el Content-Type, los cuales actúan como instrucciones de lectura para que ambas partes sepan cómo interpretar la carga de bytes compartida.

### Reto 2: Decodificador de Códigos de Estado

#### 1. Tabla de Referencia Rápida de Códigos de Estado en EcoMarket

| # | Escenario de Negocio | Código de Estado Recomendado | Razón Técnica (¿Por qué este y no otro?) | Acción del Cliente (Frontend) | Predicción Inicial |
|---|---|---|---|---|---|
| **1** | El usuario intenta crear un producto pero el JSON está mal formado. | `400 Bad Request` | Indica que el servidor no puede procesar la petición debido a un error de sintaxis del cliente. No se debe usar `422` porque este último es para errores semánticos (datos legibles pero no válidos). | Detener la petición, alertar al usuario sobre el fallo del sistema al estructurar los datos y **no** reintentar automáticamente. | `400 Bad Request` |
| **2** | El usuario intenta ver un producto que fue eliminado ayer. | `404 Not Found` | El recurso solicitado ya no existe en el servidor. No se debe usar `410 Gone` a menos que queramos indicar de forma permanente que el recurso no volverá jamás (generalmente `404` es el estándar). | Informar al usuario que el producto no existe o ya no está disponible, y redirigirlo al catálogo principal. | `404 Not Found` |
| **3** | El usuario intenta actualizar el precio de un producto pero su sesión expiró. | `401 Unauthorized` | La petición requiere autenticación del usuario. No se usa `403 Forbidden` porque `403` es cuando el usuario está autenticado pero no tiene permisos para esa acción. | Guardar el estado actual en memoria local, redirigir al productor a la pantalla de inicio de sesión (Login) para renovar el token JWT. | `401 Unauthorized` |
| **4** | El servidor de base de datos está sobrecargado temporalmente. | `503 Service Unavailable` | El servidor no está listo para manejar la petición de forma temporal. No se usa `500` porque `503` especifica que es una condición temporal y que se puede intentar más tarde. | Mostrar un indicador de carga lento, notificar que hay problemas temporales de conexión y activar la lógica de reintentos automáticos tras una breve espera (backoff). | `503 Service Unavailable` |
| **5** | El usuario intenta crear un producto con un SKU que ya existe. | `409 Conflict` | La petición no se pudo completar debido a un conflicto con el estado actual del recurso en el servidor (violación de restricción de clave única). | Notificar al usuario detalladamente que el SKU ya está en uso y permitirle editar el campo para volver a intentarlo de forma manual. | `409 Conflict` |

#### 2. Reflexión de Aprendizaje de Códigos de Estado
Esta actividad me ayudó a ver los códigos de estado como parte de la lógica de negocio y no solo como errores de red. Aprender la diferencia entre errores del cliente (`4xx`) y errores del servidor (`5xx`) permite que el frontend tome decisiones inteligentes de UX: si es `5xx` podemos reintentar automáticamente la petición para solucionar problemas temporales de red; si es `4xx`, reintentar es inútil y debemos guiar al usuario para que corrija sus datos o vuelva a iniciar sesión.

---


## FASE 2: APLICA

### Reto 3: Co-Diseñador de Contrato OpenAPI

Se ha diseñado el contrato formal utilizando la especificación OpenAPI 3.0. El archivo completo se encuentra guardado en el espacio de trabajo en [openapi.yaml](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%201/openapi.yaml).

#### Mejoras propuestas e implementadas en el Contrato:
1.  **Paginación en `GET /productos` (Parámetros `page` y `limit`):** Por defecto, traer todo el inventario de productores locales saturaría la red y la memoria del navegador. Al agregar `page` y `limit` (máximo 50 productos), garantizamos que el cliente cargue la información de manera segmentada e incremental, mejorando la velocidad de carga de la demo.
2.  **Restricciones de longitud (`minLength` / `maxLength`):** En el esquema del producto, se definieron longitudes límite para el `nombre` (entre 3 y 50 caracteres) y la `descripcion` (máximo 500 caracteres). Esto impide que usuarios malintencionados o descuidos guarden textos vacíos o envíen párrafos infinitos que desborden las celdas de la interfaz de usuario en el frontend o provoquen desbordamientos en la base de datos.

---

### Reto 4: Constructor de Cliente HTTP

El cliente HTTP base ha sido programado y optimizado en JavaScript en el archivo [cliente_http.js](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%201/cliente_http.js).

#### Cómo se inyectan las cabeceras personalizadas de negociación:
En la función base de comunicación `apiRequest(path, options)`, se inyectan de forma centralizada tanto las cabeceras de formato como la versión del cliente:

```javascript
const requestHeaders = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-Client-Version': CONFIG.CLIENT_VERSION, // Envía '1.0'
    ...options.headers
};
```
Esto garantiza que cada petición (ya sea obtener el catálogo o registrar un producto) le declare al backend que el frontend de EcoMarket opera en la versión `1.0` y que únicamente procesa e intercambia datos bajo el estándar `application/json`.

---

## FASE 3: REFLEXIONA

### Reto 5: Analista de Decisiones Arquitectónicas (ADRs)

#### ADR 1: Configuración Centralizada en Objeto `CONFIG`
*   **Contexto:** Los valores de conexión, como la URL base de la API, el token de sesión y las configuraciones de reintentos, suelen cambiar entre el entorno de desarrollo local (Mock Server) y el de producción de TechNova. Tener estos valores distribuidos a lo largo del código dificulta el mantenimiento.
*   **Decisión:** Centralizar todas las constantes críticas del cliente HTTP en una sola estructura global `CONFIG` al principio de [cliente_http.js](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%201/cliente_http.js).
*   **Alternativas Consideradas:** Hardcodear las URLs directamente en las llamadas fetch, o usar variables de entorno (las cuales añaden complejidad de configuración en el frontend junior).
*   **Consecuencias:** Cambio rápido de entorno modificando una sola línea de código. Facilita la portabilidad del código para el equipo de desarrollo.

#### ADR 2: Implementación de Timeouts con `AbortController`
*   **Contexto:** La función `fetch()` nativa de JavaScript no incluye una opción de límite de tiempo para cancelar peticiones. Si la red móvil de un usuario es inestable, una petición podría quedarse colgada indefinidamente.
*   **Decisión:** Integrar `AbortController` atado a un temporizador `setTimeout` establecido en 3 segundos (`CONFIG.TIMEOUT_MS`). Si el servidor no responde en este lapso, la petición se cancela mediante `controller.abort()`.
*   **Alternativas Consideradas:** Dejar las peticiones sin límite de tiempo o importar la librería Axios exclusivamente por su funcionalidad de timeout.
*   **Consecuencias:** El cliente es robusto y se asegura de informar al usuario rápidamente ante caídas de red, evitando bloqueos visuales en la interfaz de EcoMarket.

#### ADR 3: Validación Obligatoria del `Content-Type` de la Respuesta
*   **Contexto:** Ante un error 502/504, Nginx suele devolver páginas de error formateadas en HTML en lugar del JSON esperado. Ejecutar `response.json()` sobre código HTML lanza un error fatal de sintaxis.
*   **Decisión:** Validar que la cabecera `Content-Type` de la respuesta incluya la cadena `application/json` antes de deserializar los datos.
*   **Alternativas Consideradas:** Encapsular la llamada `.json()` en un `try/catch` simple.
*   **Consecuencias:** Permite arrojar excepciones personalizadas con códigos controlados (ej. `422 Unprocessable`), aislando fallos de infraestructura y facilitando un diagnóstico limpio.

---

### Reto 6: Comparador de Enfoques de Comunicación

Para implementar la visualización de cambios de inventario en tiempo real para inversionistas, se comparan las siguientes tres tecnologías de red:

| Criterio de Comparación | REST con Polling Corto | WebSockets | Server-Sent Events (SSE) | Mi Evaluación (Perspectiva del Estudiante) |
|---|---|---|---|---|
| **Complejidad Cliente** | ⭐ (1/5) - Solo requiere un bucle temporal `setInterval`. | ⭐⭐⭐⭐ (4/5) - Requiere implementar API WebSocket y reconexiones manuales. | ⭐⭐ (2/5) - Implementación muy sencilla mediante la API nativa `EventSource`. | Polling es insuperable en simplicidad para un junior; SSE es un paso intermedio ideal; WebSocket es excesivo para esta demo. |
| **Uso en Servidor (1k users)** | ❌ Muy alto - 1,000 usuarios haciendo peticiones cada 5s saturan el hilo de la API. | 🟢 Bajo - Mantiene sockets persistentes con mínimo intercambio de cabeceras. | 🟢 Bajo - Conexión de streaming unidireccional abierta de bajo peso. | Para la demo (1-5 usuarios) el costo es nulo, pero en producción el polling tumbaría el servidor; ahí es donde SSE brilla. |
| **Latencia de Cambios** | ❌ Alta (Retraso promedio de 2.5 a 5 segundos). | 🟢 Casi nula (Transmisión instantánea bidireccional). | 🟢 Casi nula (Transmisión instantánea del servidor al cliente). | 5 segundos de retraso son tolerables para validar la idea de negocio, aunque SSE/WebSocket darían una sensación más "en vivo". |
| **Desconexión Temporal** | 🟢 Resiliencia automática - Se reanuda en la siguiente petición del ciclo. | ❌ Frágil - Requiere programar reintentos con retraso exponencial de forma manual. | 🟢 Resiliencia nativa - El navegador se reconecta automáticamente sin intervención. | SSE es la opción más robusta para redes móviles inestables por su autoreconexión nativa de HTTP. |
| **Dificultad con Mock Server** | 🟢 Muy fácil - No requiere configuración adicional. | ❌ Difícil - Obliga a configurar un servidor de sockets simulados paralelo. | 🟡 Media - Requiere configurar cabecera de stream en las respuestas mock. | Poder simular polling sin configurar servidores complejos nos ahorra días de trabajo para la demo del viernes. |

#### Recomendación Final para la Demo de EcoMarket:
Para la demo de inversionistas del viernes, el equipo debe seleccionar **REST con Polling Corto**.  
*Razón:* Contamos con solo una semana de desarrollo y el equipo está compuesto por desarrolladores junior. Polling es directo, no requiere librerías adicionales ni complejidades en la infraestructura y se integra inmediatamente con nuestro mock server actual. Dado que en la demo solo se conectarán de 1 a 5 personas simultáneamente, el impacto en recursos del servidor será despreciable, asegurando el funcionamiento sin riesgo de fallos en producción durante la presentación.  
*Nota a Futuro:* Si el producto escala a producción para 10,000 usuarios, migraremos a **Server-Sent Events (SSE)**, ya que el inventario solo fluye en una dirección (servidor a cliente) y nos beneficiaremos de la reconexión nativa sin la sobrecarga del polling.

---

## FASE 4: VALIDA

### Reto 7: Auditor de Código Cliente

Se realizó una revisión crítica sobre la implementación inicial de nuestro cliente HTTP, categorizando los hallazgos para su corrección:

1.  **Manejo de Errores Críticos (🔴 Crítico):**
    *   *Hallazgo:* La versión inicial llamaba a `response.json()` inmediatamente tras recibir la respuesta, lo cual provocaba caídas fatales de la aplicación si el servidor devolvía una página de error HTML (código 502/500).
    *   *Solución:* Se agregó un condicional que inspecciona `response.headers.get('content-type')`. Si este no contiene `application/json`, se interrumpe y se lanza un error semántico controlado.
2.  **Seguridad de Credenciales en Depuración (🔴 Crítico):**
    *   *Hallazgo:* Al loguear las cabeceras en el logger de desarrollo (`Logger.debug`), el token JWT del header `Authorization` se imprimía completo en texto plano.
    *   *Solución:* Se programó una rutina de sanitización en el `Logger` que busca el header `Authorization` y reemplaza el token con la cadena de texto `Bearer *****[REDACTED]*****` antes de mostrarlo en consola.
3.  **Falta de Límites de Tiempo (🔴 Crítico):**
    *   *Hallazgo:* Si el servidor web se congelaba sin cerrar la conexión socket, la llamada fetch quedaba a la espera para siempre, consumiendo memoria y bloqueando al cliente.
    *   *Solución:* Se incorporó `AbortController` al fetch para cancelar la conexión tras 3 segundos.

---

### Reto 8: Simulador de Escenarios de Fallo (Pruebas de Caos)

Utilizando el simulador de caos integrado en el archivo `cliente_http.js`, se expuso al cliente HTTP a condiciones de red extremas y fallos de infraestructura. Los resultados se detallan a continuación:

| # | Escenario de Caos | Método de Simulación | Resultado Inicial (Antes de Mejoras) | Comportamiento con Mejoras de Resiliencia |
|---|---|---|---|---|
| **1** | **Red Lenta (Latencia de 4s)** | Retraso artificial de 4000ms en el simulador superando los 3000ms de configuración. | La petición se quedaba cargando indefinidamente hasta el timeout por defecto del navegador (90 segundos). | El cliente aborta a los 3000ms usando el `AbortController`, realiza 3 intentos automáticos y finalmente devuelve un código `408 Timeout` controlado. |
| **2** | **Servidor Intermitente (503)** | El simulador responde con código 503 excepto a peticiones que son múltiplo de 3. | La petición fallaba inmediatamente al primer error 503, mostrando una alerta de error en pantalla al usuario. | El cliente captura el 503, advierte al desarrollador, espera 1 segundo e intenta de nuevo. En el tercer intento la petición se completa con éxito y el usuario no nota la interrupción. |
| **3** | **Respuesta HTML de Error** | El simulador devuelve un código 200 pero con cuerpo en HTML simulando un error de Gateway. | El parseador fallaba con un error de JavaScript (`SyntaxError: Unexpected token '<'`) rompiendo la interfaz. | El cliente detecta la ausencia de `application/json`, cancela el parseo y arroja un error controlado `422` con mensaje legible. |
| **4** | **Timeout del Servidor (60s)** | Servidor se cuelga procesando una consulta pesada por 10 segundos. | El navegador del cliente se congelaba esperando la respuesta. | La petición es abortada a los 3 segundos, logueando el error `408` sin bloquear la aplicación. |
| **5** | **SKU Duplicado (409 Conflict)** | Petición POST enviando un producto especial marcado como duplicado en BD. | El cliente intentaba reintentar la creación de forma infinita al detectar un fallo. | El cliente identifica que 409 es un error del cliente (4xx) no transitorio y cancela de inmediato la petición para evitar ciclos infinitos, notificando el conflicto. |

---

## FASE 5: PROFUNDIZA

### Reto 9: Capa de Logging Profesional

Se ha integrado un sistema de logging por niveles en `cliente_http.js`. Esta capa ayuda a los desarrolladores a diagnosticar anomalías en producción de forma ágil y segura.

#### Ejemplo de Salida de Logs en Consola (Censurados):

```bash
# Nivel 1: DEBUG - Registro de inicialización (Muestra metadatos sin filtrar tokens sensibles)
[2026-05-21T07:40:02.124Z] [DEBUG] Iniciando petición POST a /productos (Intento 1/3) | Meta: {"headers":{"Accept":"application/json","Content-Type":"application/json","X-Client-Version":"1.0","Authorization":"Bearer *****[REDACTED]*****"},"body":{"nombre":"Manzana Roja","precio":45,"categoria":"frutas"}}

# Nivel 2: INFO - Petición completada con éxito (Duración y peso del paquete de datos)
[2026-05-21T07:40:02.345Z] [INFO] Petición POST exitosa a /productos | Meta: {"status":201,"durationMs":221,"sizeBytes":145}

# Nivel 3: WARN - Advertencia de reintento por fallo del servidor 503
[2026-05-21T07:40:05.890Z] [WARN] Error del servidor (503) en /productos/1. Reintentando en 1000ms... | Meta: {"duration":205}

# Nivel 4: ERROR - Caída definitiva de conexión tras timeout
[2026-05-21T07:40:10.512Z] [ERROR] Timeout excedido (3000ms) al conectar con /productos | Meta: {"duration":3004}
[2026-05-21T07:40:10.515Z] [ERROR] Error HTTP 408 en /productos: El servidor tardó demasiado en responder (> 3000ms) | Meta: {"duration":3007}
```

#### Propuestas de Mejora para Logging v2.0:
1.  **Envío Asíncrono de Logs de Error (Batching):** En lugar de imprimir logs en la consola del cliente, la v2.0 acumulará los logs de nivel `WARN` y `ERROR` en memoria y los enviará en un lote (batch) mediante una petición en segundo plano a un servicio de agregación de logs en la nube (como Datadog o Sentry) cada 15 segundos, o inmediatamente si ocurre un error crítico.
2.  **Identificador Único de Correlación (`X-Correlation-Id`):** Inyectar en cada request un header con un UUID autogenerado en el frontend. Si la petición falla, este ID se incluirá en el log. Al revisar los logs del servidor backend, los ingenieros de soporte podrán rastrear el camino exacto que recorrió la petición en toda la infraestructura distribuyendo el mismo identificador.

---

### Reflexión Final del Aprendizaje (Metacognición)

A través de las prácticas AETL de esta semana, he pasado de considerar a HTTP como un concepto meramente teórico de "petición y respuesta" a verlo como el esqueleto lógico que soporta la comunicación en sistemas distribuidos.  
La experiencia de auditar mi propio código y someterlo a pruebas de caos me demostró que el "camino feliz" (donde todo funciona bien) representa apenas el 20% del trabajo real de desarrollo. El verdadero reto radica en prepararse para el 80% restante: retardos de red, caídas de base de datos y respuestas mal formateadas.  
Haber interactuado con la IA bajo andamiajes socráticos en lugar de copiar código ciegamente, me dio la capacidad de comprender el propósito de cada cabecera y el porqué detrás del control de timeouts, logrando diseñar un cliente HTTP resiliente que está listo para evolucionar y conectarse con los siguientes retos del curso.
