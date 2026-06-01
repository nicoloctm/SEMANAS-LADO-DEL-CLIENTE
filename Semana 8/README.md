# Semana 8: Autenticación JWT desde el Cliente

Entregables de la Fase APLICA, REFLEXIONA, VALIDA y PROFUNDIZA correspondientes a la Semana 8 (Gestión de Tokens JWT).

## Archivos Entregables

- **`token_manager.py` (Retos 3 y 4):**
  - Contiene la clase `TokenManager` responsable del ciclo de vida del JWT, parseo manual del Payload en Base64URL, detección de expiración y patrón Singleton del `refresh_access_token`.
  - Contiene el Interceptor HTTP (`auth_request`) que envuelve las peticiones añadiendo el Header de Autorización y atajando errores 401.
  - Al final del archivo se encuentra un Script de Prueba (`demostracion()`) que valida todo el ciclo.
- **`decisiones_seguridad.md` (Reto 5):**
  - Justificación de almacenamiento, tiempo de refresh y análisis del modelo de amenazas ante XSS/CSRF adaptado a un entorno de cliente/proceso.
- **`reporte_validacion.md` (Reto 6):**
  - Tabla comprobando la resiliencia del cliente ante fallas como payloads malformados, desajuste de exp, el caso "thundering herd" resuelto con locks, y loops infinitos de red.
- **`diseno_sse_auth.md` (Reto 7):**
  - Profundización en arquitectura sobre cómo reconectar y proveer tokens en un streaming SSE de larga duración que atraviese periodos de expiración y validación `401 Unauthorized`.
