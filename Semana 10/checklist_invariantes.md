# Checklist de Invariantes del Sistema
## Cliente Robusto EcoMarket — Semana 10

Las **invariantes** son reglas que el sistema siempre debe cumplir, sin importar qué pase.
Aquí se documenta cada una con su estado de cumplimiento y la evidencia del código.

---

## Grupo A — Invariantes del CircuitBreaker

### INV-A1 ✔ — El CircuitBreaker solo gestiona conectividad

> El CircuitBreaker **no procesa, lee ni decodifica** tokens JWT.

**Evidencia en código (`circuit_breaker.py`):**
- El método `ejecutar(fn)` solo recibe una función. No tiene parámetro `token`.
- No hay ningún `import` de `base64`, `json` ni `jwt` en el archivo.
- Verificado por **TC-08** en las pruebas automatizadas.

---

### INV-A2 ✔ — Un solo intento por timeout en estado SEMIABIERTO

> Cuando el circuito está en SEMIABIERTO, solo deja pasar **exactamente una** petición de prueba.
> Las demás fallan rápido hasta que esa prueba termine.

**Evidencia en código (`circuit_breaker.py`):**
```python
if self.estado == EstadoCircuito.SEMIABIERTO:
    if self._peticion_de_prueba_en_curso:
        raise CircuitOpenError("Ya hay una petición de prueba en curso.")
    self._peticion_de_prueba_en_curso = True
```

---

### INV-A3 ✔ — El contador de fallos se resetea al cerrar el circuito

> Cuando el circuito se cierra exitosamente, `_fallos` vuelve a `0`.

**Evidencia en código (`circuit_breaker.py`):**
```python
def _on_exito(self):
    self.estado = EstadoCircuito.CERRADO
    self._fallos = 0  # ← reseteo explícito
    self._peticion_de_prueba_en_curso = False
    self._tiempo_apertura = None
```
**Verificado por:** TC-04 en las pruebas automatizadas.

---

### INV-A4 ✔ — Errores de cliente (4xx) no abren el circuito

> Los errores 401, 403 u otros del cliente son **culpa del cliente**, no del servidor.
> No deben incrementar el contador de fallos del CircuitBreaker.

**Evidencia en código (`circuit_breaker.py`):**
```python
def _es_fallo_servidor(self, error):
    msg = str(error).lower()
    if '401' in msg or '403' in msg or 'unauthorized' in msg or 'forbidden' in msg:
        return False  # No es fallo del servidor
    return '5' in msg or 'timeout' in msg or 'connection' in msg
```
**Verificado por:** TC-05 en las pruebas automatizadas.

---

## Grupo B — Invariantes del TokenManager

### INV-B1 ✔ — Los tokens nunca se exponen en logs

> Ningún log, print ni excepción muestra el contenido del token.

**Evidencia en código (`token_manager.py`):**
- No hay ningún `print(token)`, `log(token)` ni `str(token)` en el archivo.
- Los mensajes de log solo dicen "Token refrescado" sin mostrar el valor.

---

### INV-B2 ✔ — El token se refresca antes de expirar

> Si el token expira en menos de 10 segundos, el cliente lo refresca **antes** de hacer la petición.

**Evidencia en código (`token_manager.py` y `cliente_robusto.py`):**
```python
# token_manager.py
def is_expiring_soon(self) -> bool:
    return time.time() + 10 >= exp  # 10 segundos de margen

# cliente_robusto.py
async def _preparar_headers(self):
    if self.token_manager.is_expiring_soon():
        await self.token_manager.refresh_access_token()
```

---

### INV-B3 ✔ — El refresco del token es singleton (no se duplican peticiones)

> Si múltiples partes del código piden refrescar el token al mismo tiempo,
> solo se hace **una sola petición de red**. Las demás esperan el mismo resultado.

**Evidencia en código (`token_manager.py`):**
```python
async def refresh_access_token(self) -> str:
    if self._refresh_task is None:
        self._refresh_task = asyncio.create_task(self._do_refresh())
    return await self._refresh_task  # Todas esperan la misma tarea
```

---

## Grupo C — Invariantes del ClienteRobusto

### INV-C1 ✔ — Toda petición lleva el header de autorización

> El header `Authorization: Bearer <token>` siempre se incluye.

**Evidencia en código (`cliente_robusto.py`):**
```python
headers = await self._preparar_headers()
# headers = {'Authorization': 'Bearer eyJ...'}
async with session.get(url, headers=headers, ...) as resp:
```

---

## Resumen de cumplimiento

| Invariante | Descripción breve | Cumplida |
|------------|------------------|----------|
| INV-A1 | CircuitBreaker no toca JWT | ✔ |
| INV-A2 | Solo 1 petición en SEMIABIERTO | ✔ |
| INV-A3 | Reset de fallos al cerrar | ✔ |
| INV-A4 | Errores 4xx no abren circuito | ✔ |
| INV-B1 | Tokens no en logs | ✔ |
| INV-B2 | Refresco preventivo | ✔ |
| INV-B3 | Refresh singleton | ✔ |
| INV-C1 | Header Authorization siempre presente | ✔ |

**Estado global: 8/8 invariantes cumplidas ✔**
