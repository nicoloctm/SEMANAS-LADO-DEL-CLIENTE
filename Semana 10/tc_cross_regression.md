# Casos de Prueba: Cross-Testing y Regresión
## Sistema: Cliente Robusto EcoMarket — Semana 10

---

## ¿Qué es un caso de prueba cruzada (Cross-Test)?

Es una prueba donde se verifican **dos componentes juntos** para asegurarse de que
funcionan correctamente en combinación, no solo de forma aislada.

---

## Casos de Prueba Cruzada (CircuitBreaker + TokenManager)

### CX-01 — El CircuitBreaker no interfiere con el refresco de tokens

**Objetivo:** Confirmar que el refresco del token ocurre antes de que el CircuitBreaker
evalúe si ejecutar la petición.

**Pasos:**
1. Crear un `ClienteRobusto` con token expirado.
2. Llamar `cliente.get("/productos")`.
3. Verificar que primero se refresca el token y luego se envía la petición.

**Resultado esperado:**
- El token se refresca antes de la petición.
- El CircuitBreaker solo ve la petición de red, no el proceso de autenticación.

**Estado:** ✔ Verificado manualmente con la demo (`cliente_integrado.py`)

---

### CX-02 — Un error 401 no abre el circuito, pero sí se reporta

**Objetivo:** Confirmar que un error de autorización no daña el estado del CircuitBreaker.

**Pasos:**
1. Configurar el servidor para devolver 401.
2. Hacer 10 peticiones consecutivas.
3. Verificar el estado del circuito.

**Resultado esperado:**
- El circuito permanece en estado CERRADO.
- `_fallos` se mantiene en 0.

**Estado:** ✔ Verificado por TC-05 en `test_circuit_breaker.py`

---

### CX-03 — El CircuitBreaker abre correctamente cuando el servidor falla

**Objetivo:** Confirmar que fallos de red consecutivos abren el circuito.

**Pasos:**
1. Activar modo falla en el mock (`POST /admin/modo_falla {"activo": true}`).
2. Hacer 3 peticiones (umbral = 3).
3. Verificar que el circuito está en ABIERTO.

**Resultado esperado:**
- Circuito en estado ABIERTO después de 3 fallos.

**Estado:** ✔ Verificado por TC-02 en `test_circuit_breaker.py` y por la demo.

---

### CX-04 — El fail-fast no llama al servidor cuando el circuito está abierto

**Objetivo:** Confirmar que el CircuitBreaker no realiza peticiones de red cuando está ABIERTO.

**Pasos:**
1. Abrir el circuito artificialmente.
2. Intentar hacer una petición.
3. Verificar que la función de red nunca se ejecutó.

**Resultado esperado:**
- Se lanza `CircuitOpenError` inmediatamente.
- La función de red (el lambda de aiohttp) nunca se llama.

**Estado:** ✔ Verificado por TC-03 en `test_circuit_breaker.py`

---

## Casos de Prueba de Regresión

Los tests de regresión verifican que los **bugs corregidos no vuelvan a aparecer**.

### REG-01 — Regresión del Bug A (INV-A1)

**Precondición:** Se corrigió que el CircuitBreaker ya no procesa tokens.  
**Verificación:** El método `ejecutar()` solo acepta `fn`, no `fn, token`.  
**Test:** TC-08 — Verifica que no existan atributos relacionados con `token`, `jwt` o `auth`.  
**Estado:** ✔ No regresionado

---

### REG-02 — Regresión del Bug B (INV-B1)

**Precondición:** Se corrigió la exposición de tokens en logs.  
**Verificación:** Buscar en el código que no existan `print(token)` ni slices del token (`token[:40]`).  
**Test:** Revisión manual del código + grep: `grep -rn "token\[:" Semana\ 10/`  
**Estado:** ✔ No regresionado

---

### REG-03 — Regresión del Bug C (INV-A3)

**Precondición:** Se añadió `self._fallos = 0` en `_on_exito()`.  
**Verificación:** Después de un éxito, el contador debe ser 0.  
**Test:** TC-04 — Induce 2 fallos, espera recuperación, verifica `_fallos == 0`.  
**Estado:** ✔ No regresionado

---

## Resumen de cobertura

| ID | Tipo | Componentes | Invariante | Estado |
|----|------|-------------|------------|--------|
| CX-01 | Cross | CB + TM | INV-A1, INV-B2 | ✔ |
| CX-02 | Cross | CB + Server | INV-A4 | ✔ |
| CX-03 | Cross | CB + Server | INV-A (apertura) | ✔ |
| CX-04 | Cross | CB | INV-A2 | ✔ |
| REG-01 | Regresión | CB | INV-A1 | ✔ |
| REG-02 | Regresión | Logs | INV-B1 | ✔ |
| REG-03 | Regresión | CB | INV-A3 | ✔ |
