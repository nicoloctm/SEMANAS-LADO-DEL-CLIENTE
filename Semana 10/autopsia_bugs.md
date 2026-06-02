# Autopsia de Bugs - Semana 10
## Sistema: Cliente EcoMarket con Circuit Breaker

---

## Bug A — Violación del Principio de Responsabilidad Única (SRP)

**Archivo afectado:** `circuit_breaker.py`  
**Invariante violada:** INV-A1 — *El CircuitBreaker solo gestiona estados de conectividad.*

### ¿Qué estaba mal?

El `CircuitBreaker` original tenía código para leer y decodificar tokens JWT dentro del método `ejecutar()`. Eso está mal porque el CircuitBreaker **no debería saber nada de autenticación**; su único trabajo es decidir si abrir o cerrar el circuito según los fallos de red.

```python
# ANTES (con el bug)
def ejecutar(self, fn, token=None):
    if token:
        partes = token.split('.')
        # … decodificaba el JWT aquí dentro …
```

### ¿Cuál fue el impacto?

- Si el formato del token cambiaba, el CircuitBreaker también se rompía.
- Era imposible probar el CircuitBreaker sin un token válido.
- Violaba el principio de que cada clase hace **una sola cosa**.

### ¿Cómo se corrigió?

Se eliminó todo el código relacionado con tokens del `CircuitBreaker`. Ahora solo recibe una función (`fn`) y la ejecuta; nada más.

```python
# DESPUÉS (corregido)
async def ejecutar(self, fn):
    # Solo decide si ejecutar según su estado interno
    # No sabe nada de tokens JWT
    resultado = await fn()
    ...
```

---

## Bug B — Exposición de Token en Logs

**Archivo afectado:** `circuit_breaker.py` / cualquier logger del sistema  
**Invariante violada:** INV-B1 — *Los tokens nunca se exponen en logs.*

### ¿Qué estaba mal?

El código original imprimía los primeros 40 caracteres del token en los logs para depuración:

```python
# ANTES (con el bug)
print(f"Token usado: {token[:40]}")
```

### ¿Cuál fue el impacto?

- Un atacante con acceso a los logs podía reconstruir o reutilizar el token.
- Los tokens son credenciales de seguridad; exponerlos aunque sea parcialmente es un **riesgo grave**.

### ¿Cómo se corrigió?

Se eliminó completamente cualquier impresión del token en los logs. Si se necesita depurar, se registra solo el estado del sistema, nunca el token.

```python
# DESPUÉS (corregido)
print(f"[TokenManager] Token refrescado correctamente.")
# El token nunca aparece en los logs
```

---

## Bug C — Fallos No Se Resetean al Cerrar el Circuito

**Archivo afectado:** `circuit_breaker.py`  
**Invariante violada:** INV-A3 — *Al cerrar el circuito, el contador de fallos se resetea a 0.*

### ¿Qué estaba mal?

Cuando el circuito se cerraba (luego de una petición exitosa en estado SEMIABIERTO), el contador de fallos `_fallos` **no se ponía en cero**. Quedaba con el valor anterior.

```python
# ANTES (con el bug)
def _on_exito(self):
    self.estado = EstadoCircuito.CERRADO
    # ¡Faltaba resetear _fallos!
```

### ¿Cuál fue el impacto?

- Si el sistema tuvo, por ejemplo, 4 fallos antes de cerrarse, el próximo fallo único abría el circuito inmediatamente (umbral = 5, pero ya tenía 4 acumulados).
- El sistema nunca "olvidaba" los fallos antiguos, volviéndose **hipersensible** a fallos posteriores.

### ¿Cómo se corrigió?

Se añadió `self._fallos = 0` dentro de `_on_exito()`:

```python
# DESPUÉS (corregido)
def _on_exito(self):
    self.estado = EstadoCircuito.CERRADO
    self._fallos = 0  # ← INV-A3: resetear siempre al cerrar
    self._peticion_de_prueba_en_curso = False
    self._tiempo_apertura = None
```

---

## Resumen

| Bug | Causa raíz | Invariante | Riesgo | Estado |
|-----|-----------|------------|--------|--------|
| A | CircuitBreaker procesaba JWT | INV-A1 (SRP) | Alto | ✔ Corregido |
| B | Token impreso en logs | INV-B1 (Seguridad) | Crítico | ✔ Corregido |
| C | Fallos no se reseteaban | INV-A3 (Correctitud) | Alto | ✔ Corregido |
