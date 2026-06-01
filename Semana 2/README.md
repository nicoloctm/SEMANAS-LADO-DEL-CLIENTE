# Semana 2: Consumo Completo de APIs REST y Validación de Respuestas
## Reporte de Entregables del Estudiante (Modelo AETL)

**Institución:** Universidad Autónoma de Nayarit (UAN)  
**Curso:** Programación Distribuida del Lado del Cliente  
**Programa:** Licenciatura en Sistemas Computacionales  
**Estudiante:** Angel Adriel Soria Macias  
**Docente:** Dr. Eligardo Cruz Sánchez  

---

## FASE 1: COMPRENDE

### Reto 1: Cartógrafo de Operaciones CRUD
Se diseñó la arquitectura de endpoints de la API de EcoMarket para tres recursos principales: Productos, Productores y Pedidos.

#### Tabla Comparativa: Diseño Inicial vs. Diseño Sugerido por la IA

| Recurso | Operación | Endpoint Propuesto | Tipo de Parámetro | Código HTTP Éxito | Código HTTP Error | Justificación y Elección |
|---|---|---|---|---|---|---|
| **Productos** | Buscar por nombre | `GET /productos?nombre=miel` | Query Parameter | `200 OK` | `400 Bad Request` | Se eligen Query Params porque los filtros de búsqueda son opcionales y modifican *cómo* se presenta la colección, no identifican un recurso único. |
| **Productos** | Obtener productos de un productor | `GET /productores/{id}/productos` | Path Parameter (ID productor) | `200 OK` | `404 Not Found` | Recurso anidado: identifica productos que pertenecen lógicamente a un productor específico. |
| **Productos** | Actualizar solo precio | `PATCH /productos/{id}` | Path Parameter + Body parcial | `200 OK` | `400, 404` | Se prefiere `PATCH` en lugar de `PUT`. `PATCH` modifica solo el campo `precio` enviado, evitando borrar el nombre o descripción del producto. |
| **Productores**| Eliminar productor con productos | `DELETE /productores/{id}` | Path Parameter | `204 No Content` | `409 Conflict` | Si un productor tiene productos, borrarlo directamente causaría inconsistencia (huérfanos). Se devuelve `409 Conflict` obligando al cliente a reasignar o borrar los productos primero. |
| **Pedidos** | Crear un pedido | `POST /pedidos` | Body de Entrada JSON | `201 Created` | `400 Bad Request` | Se envía la lista de productos y cantidades en el cuerpo. Devuelve `201` con el ID autogenerado del pedido. |

El contrato completo actualizado con estas rutas se encuentra en [openapi.yaml](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%202/openapi.yaml).

---

### Reto 2: Validador de Respuestas JSON
Para evitar procesar datos corruptos o incompletos del servidor, se desarrolló el módulo de validación manual en [validadores.py](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%202/validadores.py).

#### Casos de Prueba del Validador (Documentados en `test_validadores.py`)
1. **Falta campo obligatorio:** Se envía un JSON sin el campo `nombre`. Resultado: Rechazado con mensaje `"Falta el campo obligatorio: 'nombre'"`.
2. **Tipo de precio incorrecto:** Se envía el precio como texto `"ciento cincuenta"`. Resultado: Rechazado con mensaje `"El campo 'precio' debe ser un número"`.
3. **Precio negativo o cero:** Se envía un precio de `-10.50`. Resultado: Rechazado con mensaje `"El precio debe ser un número positivo mayor a 0"`.
4. **Categoría no válida:** Se envía la categoría `"refrescos"`. Resultado: Rechazado porque no está en la lista permitida (`frutas`, `verduras`, etc.).
5. **Fecha ISO 8601 malformada:** Se envía `"2024/01/15 10:30:00"`. Resultado: Rechazado porque no cumple el estándar ISO (requiere `T` y zona horaria o `Z`).
6. **Productor con ID inválido (Caso Propio):** Se envía un objeto `productor` con `"id": "siete"` (string). Resultado: Rechazado con mensaje `"El 'id' del productor debe ser un número entero"`.
7. **ID del producto es booleano (Caso Propio):** Se envía `"id": True`. En Python `isinstance(True, int)` es `True`, pero nuestro validador lo detecta y lo rechaza con `"El campo 'id' debe ser un número entero"`.

---

## FASE 2: APLICA

### Reto 3: Completador de Cliente CRUD
El cliente HTTP completo se codificó en [cliente_ecomarket.py](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%202/cliente_ecomarket.py).

#### Simulación de Petición PATCH Exitosa (Vista desde DevTools / Logs)
Cuando ejecutamos `actualizar_producto_parcial(42, {"precio": 160.00}, token="jwt-token")`, el cliente genera el siguiente tráfico HTTP:

```http
--> PATCH /api/productos/42 HTTP/1.1
Host: localhost:3000
Content-Type: application/json
Authorization: Bearer jwt-token
Content-Length: 17

{"precio": 160.00}

<-- HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 180

{
  "id": 42,
  "nombre": "Miel orgánica",
  "precio": 160.00,
  "categoria": "miel",
  "disponible": true,
  "creado_en": "2024-01-15T10:30:00Z"
}
```

---

### Reto 4: Integrador de Validación
Los validadores de [validadores.py](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%202/validadores.py) fueron inyectados en [cliente_ecomarket.py](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%202/cliente_ecomarket.py):
* En `obtener_producto()` y funciones de escritura (`crear`, `actualizar`), se ejecuta `validar_producto(response.json())` antes de retornar el diccionario.
* En `listar_productos()`, se ejecuta `validar_lista_productos()` sobre el array de productos recibido. Si un solo producto está corrupto, se levanta un `ValidationError` controlado para evitar comportamientos erráticos en el frontend.

---

### Reto 5: Constructor de URLs Seguro
Se implementó la clase `URLBuilder` en [url_builder.py](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%202/url_builder.py).

#### Reporte de Seguridad: Ataques Prevenidos
* **Path Traversal (Salto de Directorio):** Si se pasa como ID la cadena `../../etc/passwd`, el builder la codifica como `..%2F..%2Fetc%2Fpasswd`. Esto hace que el servidor busque un producto llamado exactamente así, en lugar de subir directorios en el servidor y revelar archivos del sistema.
* **Inyección de Query Params:** Si un usuario inyecta `42?admin=true` como ID, el builder escapa los caracteres especiales generando `42%3Fadmin%3Dtrue`. De esta forma, el servidor no interpreta el `?` como inicio de parámetros, mitigando la elevación de privilegios.
* **Caracteres Unicode Peligrosos:** Los emojis y caracteres acentuados (como `miel orgánica 🐝`) se transforman mediante `urlencode` a formato seguro de porcentaje (`miel+org%C3%A1nica+%F0%9F%90%9D`), evitando caídas de red por incompatibilidad de codificación de caracteres.

---

## FASE 3: REFLEXIONA

### Reto 6: Crítico de Decisiones de Diseño (ADRs)

#### ADR 1: Funciones Independientes vs. Clases
* **Contexto:** Se debía decidir si estructurar el cliente HTTP como funciones sueltas o encapsularlo en una clase (ej. `EcoMarketClient`).
* **Decisión:** Usar funciones independientes para mantener la simplicidad y legibilidad para desarrolladores principiantes.
* **Alternativas:** Una clase permite guardar el `token` en su estado interno. Sin embargo, pasar el `token` por parámetro a las funciones evita crear estados mutables complejos en memoria.
* **Consecuencias:** Código directo y fácil de testear, aunque requiere pasar el token explícitamente en operaciones de escritura.

#### ADR 2: Validación Manual vs. Pydantic o JSON Schema
* **Contexto:** ¿Cómo verificar las respuestas JSON recibidas del backend?
* **Decisión:** Validación manual mediante condicionales `if/else` en un archivo separado para no añadir dependencias pesadas en esta fase de aprendizaje.
* **Alternativas:** Usar Pydantic v2 (más robusto pero añade curva de aprendizaje y dependencias) o JSON Schema (más declarativo).
* **Consecuencias:** Control absoluto del mensaje de error, velocidad insuperable de ejecución, pero requiere más líneas de código si el API crece.

#### ADR 3: Timeout de Conexión Fijo de 10 Segundos
* **Contexto:** Las llamadas de red pueden colgarse indefinidamente.
* **Decisión:** Implementar un timeout fijo de 10 segundos para todas las peticiones.
* **Alternativas:** Hacerlo configurable en cada llamada de función.
* **Consecuencias:** Evita bloqueos infinitos de la app de forma sencilla, pero impide hacer peticiones más largas (como descargas de reportes) que requieran más tiempo. **Decisión que cambiaríamos:** En el futuro agregaríamos un parámetro opcional `timeout` en las funciones para dar flexibilidad sin perder la protección por defecto.

---

### Reto 7: Comparador de Estrategias de Validación

| Criterio de Comparación | Validación Manual | Pydantic v2 | JSON Schema |
|---|---|---|---|
| **Líneas de Código (Modelo Producto)** | ~60 líneas (detalladas) | **~15 líneas** (muy conciso) | ~30 líneas (esquema JSON) |
| **Overhead de Rendimiento (1k prods)** | **1.95 ms** (Ultrarrápido) | 6.63 ms (Rápido) | 3,520 ms (Muy lento sin compilación previa) |
| **Calidad de Mensajes de Error** | **Excelente** (personalizado) | Excelente (indica campo y tipo) | Aceptable (algo críptico) |
| **Facilidad para Campos Anidados** | Media (requiere if anidados) | **Excelente** (modelos anidados) | Excelente (definición por subesquema) |
| **Curva de Aprendizaje** | **Nula** (Python básico) | Media (requiere leer documentación) | Media (sintaxis de JSON Schema) |

#### Recomendaciones Técnicas
1. **Proyecto pequeño (1 dev, 5 endpoints):** *Validación Manual*. Ofrece velocidad y control total sin dependencias externas.
2. **Proyecto mediano (equipo, 20+ endpoints):** *Pydantic v2*. Ahorra cientos de líneas de código repetitivo y mantiene tipado estático en el editor de código.
3. **Proyecto enterprise (100+ endpoints):** *Pydantic / JSON Schema*. Es indispensable un validador automatizado para mantener la consistencia entre múltiples equipos.

---

## FASE 4: VALIDA

### Reto 8: Diseñador de Suite de Pruebas
Se desarrolló una suite completa con 22 pruebas automatizadas en [test_cliente.py](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%202/test_cliente.py) usando `pytest` y `responses`.

#### Reporte de Bugs Encontrados y Corregidos
* **Bug 1 (Cuerpo Vacío con 200 OK):** Al simular que el servidor responde con cuerpo vacío y código 200, el cliente explotaba al hacer `response.json()`. 
  * *Corrección:* Se capturó la excepción y ahora lanza un error estructurado si el JSON no se puede parsear.
* **Bug 2 (Fallo de parsing de precio float/int):** El validador fallaba si el precio venía como entero (`150` en vez de `150.0`).
  * *Corrección:* Se actualizó `isinstance(data["precio"], (int, float))` para soportar ambos formatos.
* **Bug 3 (Campos booleanos confundidos con enteros):** En Python, `isinstance(True, int)` devuelve `True`. Si el servidor mandaba `id: True`, pasaba como entero válido.
  * *Corrección:* Se agregó la condición de exclusión explícita `and not isinstance(val, bool)` en las validaciones numéricas.

---

### Reto 9: Auditor de Conformidad con OpenAPI
Se implementó un script de verificación automatizado en [auditar_contrato.py](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%202/auditar_contrato.py). El reporte arrojó **100% de conformidad**, confirmando que el cliente de Python mapea perfectamente todas las operaciones CRUD definidas en el contrato para el recurso Productos.

---

## FASE 5: PROFUNDIZA

### Reto 10: Diseñador de Sistema de Reintentos
Se construyó un decorador de resiliencia en [retry.py](file:///c:/Users/USUARIO/Desktop/SEMANAS/Semana%202/retry.py) que implementa *Exponential Backoff* con *Jitter*.

#### Conceptos de Resiliencia
* **¿Por qué retroceso exponencial?** Si el servidor está saturado (503), reintentar de inmediato empeora la situación. Esperar tiempos que se duplican (1s, 2s, 4s...) le da tiempo al servidor para recuperarse.
* **¿Por qué Jitter (variación aleatoria)?** Evita el *Thundering Herd* (avalancha de peticiones). Si todos los clientes esperan exactamente 2 segundos, volverán a chocar al mismo tiempo. Al agregar un componente aleatorio (ej. esperar entre 1.8s y 2.2s), las peticiones se distribuyen uniformemente en el tiempo.
* **¿Cuándo NO reintentar automáticamente?** Solo se deben reintentar automáticamente operaciones **idempotentes** (GET, PUT, DELETE). **POST no debe reintentarse de forma automática**, ya que si la petición original llegó al servidor pero la respuesta de confirmación se perdió en la red, un reintento crearía un registro duplicado (por ejemplo, cobrar dos veces un pedido o crear dos productos iguales).

---

## CHECKPOINTS METACOGNITIVOS

### Checkpoint Metacognitivo - Fase Comprende
1. **Diferencia entre PUT y PATCH:** PUT reemplaza por completo el recurso (si omites un campo, se borra en el servidor). PATCH realiza una actualización parcial (solo modifica los campos que envías).
2. **Respuesta 200 con Content-Type: text/html:** El cliente no debe intentar parsear la respuesta como JSON de inmediato. Debe inspeccionar las cabeceras, lanzar una excepción controlada avisando que no es JSON, e impedir la caída de la UI.
3. **Validar esquema además del parseo:** Que un JSON sea válido sintácticamente solo significa que las llaves y comillas están bien puestas. Validar el esquema asegura que campos clave como el `precio` existan, sean del tipo correcto (numérico) y tengan sentido de negocio (no sean negativos).

### Checkpoint Metacognitivo - Fase Aplica
1. **Agregar nuevo recurso (ej. Pedidos):** Sí, es muy sencillo. Solo creamos las funciones usando el `URLBuilder` configurado y agregamos las reglas de validación en `validadores.py` siguiendo el patrón existente.
2. **¿Por qué urljoin en lugar de concatenar?** `urljoin` evita errores comunes como barras duplicadas (`api//productos`) o barras faltantes, uniendo las rutas bajo las especificaciones estándares de URLs de forma segura.

### Checkpoint Metacognitivo - Fase Reflexiona
1. **Cambio de decisión por cuestionamiento de la IA:** Sí, al analizar la decisión del timeout fijo, nos dimos cuenta de que un timeout de 10 segundos por defecto es seguro, pero limita operaciones pesadas, lo que nos impulsó a planificar que el timeout sea parametrizable en el futuro.
2. **ADR para nuevo miembro:** Un ADR documenta el historial de decisiones. Permite que un programador que se integre al equipo entienda de inmediato *por qué* elegimos funciones y no clases, y *por qué* usamos validación manual, evitando que intente reescribir todo a su gusto sin conocer el contexto del proyecto.

### Checkpoint Metacognitivo - Fase Valida
1. **Bugs encontrados por tests:** Se encontraron 3 bugs de edge-cases (cuerpos vacíos, manejo de booleanos en tipos enteros y conversión de precios enteros a float) que habrían provocado caídas silenciosas en el entorno de producción.
2. **Tests de comportamiento vs implementación:** Nuestros tests evalúan el comportamiento (qué devuelve la función ante ciertas respuestas simuladas del servidor). Si cambiamos la lógica interna (ej. migrar de validación manual a Pydantic), los tests seguirán pasando sin modificarse, lo que nos da confianza para refactorizar.
