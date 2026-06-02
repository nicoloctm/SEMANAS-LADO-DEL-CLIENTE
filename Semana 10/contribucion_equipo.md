# Reporte de Contribución del Equipo — Hito 2

## Información del Equipo
* **Materia:** Programación Distribuida del Lado del Cliente
* **Unidad:** IV - Cierre (Semana 10)
* **Proyecto:** Grand Deploy — EcoMarket Cliente Seguro y Resiliente
* **Integrantes:** 
  1. Ingeniero A (Diseño de Resiliencia y Pruebas)
  2. Ingeniero B (Gestión de Estado de Tokens e Integración)

---

## División del Trabajo y Aportes Individuales

### Ingeniero A (Diseño de Resiliencia y Pruebas)
* **Rol:** Responsable de la lógica de control del disyuntor y de la validación del sistema.
* **Aportaciones específicas:**
  - Implementación original del `CircuitBreaker` en `circuit_breaker.py`, incluyendo las transiciones de estado (`CERRADO`, `ABIERTO`, `SEMIABIERTO`) y el soporte de timeouts.
  - Diseño y desarrollo de la suite de pruebas unitarias (`test_circuit_breaker.py`) cubriendo los casos de prueba del TC-01 al TC-08.
  - Redacción de la autopsia de bugs (`autopsia_bugs.md`) y el checklist de invariantes de seguridad (`checklist_invariantes.md`).

### Ingeniero B (Gestión de Estado de Tokens e Integración)
* **Rol:** Responsable de la autenticación segura, concurrencia y orquestación del cliente.
* **Aportaciones específicas:**
  - Desarrollo del `TokenManager` con decodificación Base64URL segura y la lógica del refresco singleton (`refresh_access_token()`).
  - Implementación de `ClienteRobusto` orquestando la interacción desacoplada de `TokenManager` y `CircuitBreaker` sin violar el SRP.
  - Integración del script `cliente_integrado.py` contra el backend simulado en `mock_ecomarket.py` y control de la visibilidad de estado en consola.
  - Redacción de las decisiones arquitectónicas (`adr_decision_critica.md`).

---

## Conflicto Técnico Resuelto

### El Conflicto: Event Loop Sync vs. Async en Tests Unitarios
Durante el desarrollo de las pruebas en `test_circuit_breaker.py`, el Ingeniero A implementó un helper sincrónico `run(coro)` que cerraba el event loop después de cada prueba. Sin embargo, el Ingeniero B observó que al ejecutar pruebas concurrentes complejas (como el refresh singleton del `TokenManager` o el comportamiento concurrente en `SEMIABIERTO`), el cierre repetido del loop causaba excepciones del tipo `RuntimeError: Event loop is closed` en hilos de background de `aiohttp`.

### La Resolución:
Tras debatir las alternativas, decidimos:
1. Re-diseñar el helper `run(coro)` para asegurar que se cree un nuevo loop limpio (`asyncio.new_event_loop()`) para cada invocación del test y establecerlo en el hilo activo de forma aislada.
2. Utilizar mocks puros basados en variables en memoria en lugar de realizar llamadas de red de `aiohttp` reales dentro de los tests unitarios del `CircuitBreaker` y `TokenManager`, garantizando que no se queden sockets abiertos que dependan de un loop cerrado.
3. Esta resolución mantuvo las pruebas rápidas e independientes (por debajo de 0.6 segundos) sin ensuciar el hilo de ejecución principal.
