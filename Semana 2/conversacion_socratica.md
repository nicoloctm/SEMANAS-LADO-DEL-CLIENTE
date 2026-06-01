# Diálogo Socrático - Semana 2: Consumo de APIs y Validación de Respuestas

**Institución:** Universidad Autónoma de Nayarit (UAN)  
**Curso:** Programación Distribuida del Lado del Cliente  
**Programa:** Licenciatura en Sistemas Computacionales  
**Estudiante:** Angel Adriel Soria Macias  
**Tutor:** IA (Asistente de Aprendizaje)

Este documento registra la conversación socrática en la que el estudiante, con ayuda del tutor, descubre y comprende los conceptos clave de la programación defensiva al consumir APIs REST.

---

## 1. Comprende: El dilema de actualizar datos (PUT vs PATCH)

*   **Estudiante:** Hola, estoy programando el catálogo de EcoMarket. La verdad me confunde que existan dos verbos para actualizar: `PUT` y `PATCH`. ¿No es lo mismo? En ambos casos le digo al servidor que cambie algo.
*   **Tutor IA:** Es una duda muy común cuando estás empezando. Imagina que tienes un producto en EcoMarket: `{"id": 42, "nombre": "Miel", "precio": 150.0, "categoria": "miel"}`. Si quieres cambiar el precio a 160.0 usando `PUT`, ¿qué datos deberías enviarle al servidor en el cuerpo de la petición?
*   **Estudiante:** Pues supongo que solo el nuevo precio: `{"precio": 160.0}`.
*   **Tutor IA:** Ese es el detalle. Si haces eso con `PUT`, la especificación dice que el servidor debe **reemplazar** todo el recurso. O sea, el producto se actualizaría a: `{"id": 42, "nombre": null, "precio": 160.0, "categoria": null}`. ¿Qué pasó con el nombre y la categoría?
*   **Estudiante:** ¡Ah! ¡Se borraron! O sea que con `PUT` tengo que mandar el objeto completo con todos sus campos aunque solo quiera cambiar una cosa.
*   **Tutor IA:** Exacto. Ahora, ¿cómo crees que funciona `PATCH` en este mismo caso si solo le mandas `{"precio": 160.0}`?
*   **Estudiante:** Con `PATCH` el servidor solo modifica el precio y deja el nombre y la categoría tal como estaban. Es como un "parche".
*   **Tutor IA:** ¡Perfecto! Lo has entendido muy bien. `PUT` es para reemplazo completo y `PATCH` para cambios parciales. Usar el equivocado puede causar pérdida de datos.

---

## 2. Comprende: ¿Por qué validar si el servidor "siempre tiene la razón"?

*   **Estudiante:** Estoy haciendo una función en Python para recibir los productos del servidor. Si el servidor ya los tiene guardados, ¿para qué necesito validarlos en el cliente? Se supone que la base de datos no guarda basura.
*   **Tutor IA:** En un mundo ideal, sí. Pero, ¿qué pasa si el servidor se cae y en lugar de JSON te responde con una página HTML de error (como un error 502 de Nginx)? Si tu código hace `response.json()` inmediatamente, ¿qué crees que ocurrirá?
*   **Estudiante:** Creo que mi programa va a explotar con un error raro de sintaxis porque no puede leer HTML como si fuera un JSON.
*   **Tutor IA:** Así es. ¿Y qué pasa si un programador del backend cambia el nombre de un campo (por ejemplo, cambia `precio` por `costo`) y se le olvida avisarte?
*   **Estudiante:** Mi interfaz va a intentar mostrar el precio pero saldrá vacío o `undefined` y el usuario no podrá comprar.
*   **Tutor IA:** Exacto. Por eso un "cliente paranoico" nunca confía en lo que manda el servidor. Valida que el código sea correcto (2xx), que el tipo de contenido sea `application/json`, y que los datos tengan la estructura y los tipos correctos antes de usarlos.

---

## 3. Aplica: Construcción de URLs seguras

*   **Estudiante:** En mi código de la semana pasada construía las URLs sumando textos, algo como: `url = "productos/" + str(id)`. Me dijeron que esto es inseguro. ¿Cómo va a ser inseguro si el ID solo lo pongo yo?
*   **Tutor IA:** Piensa en esto: ¿qué pasa si el `id` viene de un buscador donde el usuario escribe lo que sea? Si un usuario malintencionado escribe `../../etc/passwd` como ID de producto, ¿cómo quedaría tu URL final?
*   **Estudiante:** Quedaría como `productos/../../etc/passwd`. ¡Oye! Los `..` significan "subir de carpeta". ¡Estaría intentando entrar a los archivos del sistema del servidor!
*   **Tutor IA:** Exactamente. Eso se llama *Path Traversal* (salto de directorio). Y si escribe algo como `42?admin=true` como ID, ¿qué pasaría con la petición?
*   **Estudiante:** Se añadiría un parámetro `admin=true` que el servidor podría interpretar como si yo fuera administrador.
*   **Tutor IA:** Así es. Por eso no debemos concatenar texto plano para armar URLs. Usar funciones como `quote` o una clase `URLBuilder` codifica esos caracteres peligrosos: el `/` se convierte en `%2F` y el `?` en `%3F`, por lo que el servidor los interpreta como texto plano seguro, no como comandos de ruta.

---

## 4. Valida: Pruebas con Mocks en lugar de peticiones reales

*   **Estudiante:** Quiero hacer pruebas de mi cliente HTTP. ¿Por qué usamos la librería `responses` para simular (mockear) la API en lugar de prender el mock server de Node y probar directamente contra él?
*   **Tutor IA:** Es una gran pregunta. Imagina que tienes 100 pruebas. Si cada petición real tarda 0.2 segundos, tu suite tardará 20 segundos. Con mocks tarda menos de 1 segundo. Pero hay una razón de resiliencia más importante: ¿cómo probarías que tu cliente maneja correctamente un error 503 (Servicio no disponible) o un timeout de red usando el servidor real?
*   **Estudiante:** Uff, sería muy difícil. Tendría que apagar el servidor a la mitad del test o modificar el código del backend para que devuelva un error a propósito.
*   **Tutor IA:** Exacto. Con `responses` puedes decirle al test: "Cuando mi cliente intente hacer GET a `/productos/42`, finge que el servidor tardó 15 segundos o devolvió un 503". Así podemos probar todos los casos de error fácilmente sin tocar el backend.

---

## 5. Profundiza: ¿Por qué no reintentar inmediatamente? (Backoff y Jitter)

*   **Estudiante:** Si mi cliente detecta un error 503 (servidor saturado), le puse un bucle para que vuelva a intentar la petición de inmediato. ¿Está bien?
*   **Tutor IA:** Imagina que una tienda está cerrada por mantenimiento y hay una fila de 1,000 personas. Si la tienda abre la puerta un milímetro, y las 1,000 personas empujan al mismo tiempo de forma desesperada, ¿qué pasará?
*   **Estudiante:** Se va a hacer un caos y probablemente tiren la puerta o la vuelvan a trabar.
*   **Tutor IA:** Eso mismo le pasa al servidor saturado. Si 1,000 clientes HTTP reintentan de inmediato y sin parar (*thundering herd*), el servidor nunca se recuperará. Por eso usamos *Exponential Backoff* (esperar 1s, luego 2s, luego 4s...) para darle un respiro.
*   **Estudiante:** Entiendo. ¿Y qué es eso de *Jitter*?
*   **Tutor IA:** Si todos los clientes esperan exactamente 1 segundo, volverán a chocar al mismo tiempo. *Jitter* añade una pequeña variación aleatoria (por ejemplo, uno espera 0.9s y otro 1.1s). Así se desincronizan y entran uno por uno.
*   **Estudiante:** ¡Qué inteligente! Le da orden al tráfico de red cuando hay problemas.

---

## Conclusión del Estudiante
Esta conversación me ayudó a entender que escribir código no es solo lograr que funcione en mi computadora cuando todo va bien (el *happy path*). Un programador de sistemas debe prepararse para los fallos: que la red falle, que el servidor mande datos corruptos o que personas intenten inyectar código en las URLs. Validar las respuestas y construir URLs seguras no es opcional, es lo que separa a un programa de juguete de uno profesional.
