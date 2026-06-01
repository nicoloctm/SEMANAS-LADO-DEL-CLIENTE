# ADR: Decisiones de Concurrencia – Cliente EcoMarket
## Semana 3 – Reto 6: Crítico de Decisiones de Concurrencia

---

## ADR-001: Uso de `asyncio.gather()` con `return_exceptions=True`

| Campo | Detalle |
|-------|---------|
| **Fecha** | Semana 3 |
| **Estado** | Aceptado |

### Contexto
El dashboard de EcoMarket necesita cargar 4 fuentes de datos simultáneamente: productos, categorías, perfil y notificaciones. La primera versión usaba `gather()` sin `return_exceptions`, lo que causaba que un fallo en notificaciones cancelara los otros 3 resultados ya obtenidos.

### Decisión
Usar `asyncio.gather(*tareas, return_exceptions=True)` como estrategia principal de coordinación.

### Alternativas consideradas
| Alternativa | Razón de descarte |
|-------------|-------------------|
| `gather()` sin `return_exceptions` | Cancela todas las tareas si una falla |
| `wait(FIRST_EXCEPTION)` | Útil solo para flujos donde 1 error invalida todo |
| `as_completed()` | Mejor para UI progresiva, más complejo para dashboard simple |

### Consecuencias
- ✅ Un fallo en notificaciones no pierde productos, categorías ni perfil
- ✅ El código es simple y legible
- ⚠️ El dashboard siempre espera a la petición más lenta antes de mostrar cualquier dato

---

## ADR-002: Una sola `ClientSession` por grupo de peticiones

| Campo | Detalle |
|-------|---------|
| **Fecha** | Semana 3 |
| **Estado** | Aceptado |

### Contexto
El código inicial creaba una `aiohttp.ClientSession` dentro de cada función CRUD. Esto desperdicia conexiones TCP (una nueva por petición) y consume file descriptors innecesariamente.

### Decisión
Crear **una sola `ClientSession`** por operación de grupo (dashboard, creación masiva) y pasarla como parámetro a las funciones CRUD.

### Alternativas consideradas
| Alternativa | Razón de descarte |
|-------------|-------------------|
| Sesión global (singleton) | Race conditions en entornos multi-event-loop |
| Sesión por petición | Desperdicio de recursos TCP |
| Sesión por función CRUD | Mismo problema que sesión por petición |

### Consecuencias
- ✅ Reutilización de conexiones TCP (keep-alive)
- ✅ Control explícito del ciclo de vida de la sesión
- ⚠️ Las funciones CRUD no son auto-suficientes: requieren que el llamador gestione la sesión
- ⚠️ Si se necesitan headers distintos por petición, se deben pasar explícitamente

---

## ADR-003: Semáforo de 5 para creación masiva

| Campo | Detalle |
|-------|---------|
| **Fecha** | Semana 3 |
| **Estado** | En revisión |

### Contexto
`crear_multiples_productos()` puede recibir listas de 100+ productos. Sin límite, lanzar 100 peticiones POST simultáneas puede sobrecargar el servidor o agotar file descriptors del cliente.

### Decisión
Usar `asyncio.Semaphore(5)` como valor inicial conservador para la creación masiva.

### Alternativas consideradas
| Alternativa | Razón de descarte |
|-------------|-------------------|
| Sin semáforo | Puede saturar el servidor |
| Semáforo de 1 (secuencial) | Anula el beneficio de la asincronía |
| Semáforo de 20 | Puede exceder límites del servidor según su configuración |
| Rate limiter (token bucket) | Más preciso pero más complejo; implementado en `throttle.py` |

### Consecuencias
- ✅ Protege el servidor de sobrecarga
- ✅ Configurable mediante constante `MAX_CONCURRENCIA`
- ⚠️ El valor 5 es arbitrario; debería ajustarse con métricas reales del servidor
- ⚠️ No controla la tasa (peticiones/segundo), solo la concurrencia puntual

---

## Fortalezas del diseño actual
1. Los validadores de Semana 2 se reutilizan sin modificación
2. El manejo de errores es por petición individual, no global
3. La sesión siempre se cierra con `async with`, previniendo resource leaks

## Debilidades y próximos pasos
1. No hay reintentos automáticos (se implementarán en Semana 4)
2. El timeout global del dashboard no existe aún (cada petición tiene su propio timeout, pero el usuario podría esperar indefinidamente si las 4 peticiones van lentas)
3. El semáforo de 5 necesita ajuste basado en métricas del servidor real
