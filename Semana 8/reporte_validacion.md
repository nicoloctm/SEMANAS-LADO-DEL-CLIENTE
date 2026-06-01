# Reporte de Validación (Reto 6)

| Caso de Prueba | Descripción | Resultado Obtenido | ¿Coincide con Esperado? |
|----------------|-------------|--------------------|-------------------------|
| **Caso 1** | is_expiring_soon() usa segundos Unix (payload con expira en 9999999999) | Da False (no expira pronto). No se confunde con ms | ✅ Sí |
| **Caso 2** | is_expiring_soon() reacciona sin access_token | Da True automáticamente. | ✅ Sí |
| **Caso 3** | decode_payload() maneja token de 2 partes (malformado) | `ValueError: Token malformado: debe tener 3 partes` | ✅ Sí |
| **Caso 4** | decode_payload() maneja token sin claim `exp` | El cliente asume que `exp` no existe y asume expiración (True) por seguridad. | ✅ Sí |
| **Caso 5** | Refresh Singleton | 3 peticiones concurrentes simuladas generan solo **1 log** de `Iniciando refresh singleton...`. Las demás entran al lock y ven que ya no es necesario renovar porque el primero lo hizo. | ✅ Sí |
| **Caso 6** | Loop Infinito cortado | Si falla el refresh, interceptor corta en el primer intento y devuelve estado de error 401 en lugar de seguir refrescando. | ✅ Sí |

### Bug Encontrado y Corregido (Durante la Implementación del Caso 5):
**Problema:** Inicialmente, al usar `asyncio.gather()` para lanzar 3 peticiones concurrentes que fallaban con 401, el cliente hacía la petición real al endpoint de refresh 3 veces.
**Causa Raíz:** Dentro de mi bloque `async with self._refresh_lock:`, estaba haciendo el POST sin revisar si el token había sido *ya* renovado por el thread que tuvo el lock justo antes de mí. Es decir, las corrutinas hacían fila pero al final todas ejecutaban la llamada a red.
**Fix aplicado:** Agregué la comprobación `if not self.is_expiring_soon(): return True` **justo después** de adquirir el lock (y antes de imprimir "Iniciando refresh..."). De esta forma, el primer hilo que adquiere el lock renueva el token y actualiza el estado. Los otros hilos que esperaban en la fila del lock, al entrar, evalúan de nuevo y ven que el token ya está fresco, retornando inmediatamente sin hacer peticiones redundantes.
