# Bitácora de Uso de la IA
## Proyecto: Cliente Robusto EcoMarket — Semana 10

Esta bitácora registra cómo se usó la IA como herramienta de apoyo
durante el desarrollo de los entregables de esta semana.

---

## ¿Para qué se usó la IA?

La IA se usó como un **asistente de programación**, similar a tener un tutor
que explica los conceptos y ayuda a escribir el código cuando el estudiante
no sabe cómo empezar.

---

## Registro de sesiones

### Sesión 1 — Entender el problema

**Fecha:** Semana 10  
**Preguntas hechas a la IA:**

- "¿Qué es un Circuit Breaker y para qué sirve?"
- "¿Por qué el código del Circuit Breaker original está mal?"
- "¿Qué significa 'Principio de Responsabilidad Única'?"

**Lo que aprendí:**
La IA me explicó que el Circuit Breaker es como un "disyuntor" eléctrico:
cuando hay demasiados fallos, "abre" el circuito para no seguir intentando
conectar a un servicio caído. Aprendí que mezclar la lógica de tokens
dentro del CircuitBreaker era un error porque hacía que el código fuera
más difícil de entender y probar.

**Código generado con ayuda de la IA:** `circuit_breaker.py` (corrección de bugs A y C)

---

### Sesión 2 — Implementar el TokenManager

**Preguntas hechas a la IA:**

- "¿Qué es un JWT y cómo se decodifica?"
- "¿Por qué hay que restaurar el padding de Base64?"
- "¿Qué es un Singleton y por qué lo necesito aquí?"

**Lo que aprendí:**
Un JWT tiene tres partes separadas por puntos. La del medio (payload)
está codificada en Base64URL, que es como Base64 normal pero sin los
caracteres `+` y `/`. Para decodificarlo hay que "restaurar" caracteres
de relleno (`=`) que se omiten para ahorrar espacio.

El Singleton para el refresco evita que si 5 partes del código piden
un token nuevo al mismo tiempo, se hagan 5 peticiones al servidor.
Con `asyncio.Task`, todas esperan el mismo resultado.

**Código generado con ayuda de la IA:** `token_manager.py`

---

### Sesión 3 — Integrar todo en el ClienteRobusto

**Preguntas hechas a la IA:**

- "¿Cómo junto el CircuitBreaker y el TokenManager sin que se mezclen?"
- "¿Qué pasa si el token expira mientras se hace una petición?"

**Lo que aprendí:**
La forma correcta es que el `ClienteRobusto` llame primero al `TokenManager`
para obtener los headers, y luego pase solo la petición de red al `CircuitBreaker`.
Así cada clase hace su trabajo y no saben nada una de la otra.

**Código generado con ayuda de la IA:** `cliente_robusto.py`

---

### Sesión 4 — Escribir pruebas automatizadas

**Preguntas hechas a la IA:**

- "¿Cómo escribo un test unitario en Python?"
- "¿Cómo simulo un fallo de red en un test sin un servidor real?"
- "¿Qué es una prueba de regresión?"

**Lo que aprendí:**
Un test unitario en Python usa `unittest.TestCase`. Para simular fallos
se pueden crear funciones asíncronas que simplemente lanzan una excepción.
Una prueba de regresión verifica que un bug que ya se corrigió no vuelva a aparecer.

**Código generado con ayuda de la IA:** `test_circuit_breaker.py`

---

### Sesión 5 — Documentación y reportes

**Preguntas hechas a la IA:**

- "¿Cómo explico un bug de forma técnica pero entendible?"
- "¿Qué es una invariante en programación?"

**Lo que aprendí:**
Una "invariante" es una regla que el sistema SIEMPRE debe cumplir.
Es como una promesa del código: "no importa qué pase, esto siempre será verdad".

**Documentos generados con ayuda de la IA:** `autopsia_bugs.md`, `checklist_invariantes.md`, `tc_cross_regression.md`

---

## Evaluación del uso de la IA

| Aspecto | Evaluación |
|---------|------------|
| ¿La IA explicó los conceptos claramente? | ✔ Sí, con ejemplos simples |
| ¿Entendí el código antes de usarlo? | ✔ La IA siempre explicó por qué |
| ¿Usé la IA para copiar sin entender? | ✗ No, siempre pedí explicaciones |
| ¿Pude hacer preguntas de seguimiento? | ✔ Sí, la conversación fue iterativa |

---

## Reflexión final

Usar la IA como asistente me permitió avanzar en conceptos que de otra forma
habrían tardado más semanas en entenderse. Lo más importante es que no usé la IA
para que "hiciera el trabajo": la usé para aprender cómo hacerlo y después
aplicar ese conocimiento. La IA es como un tutor disponible en cualquier momento.
