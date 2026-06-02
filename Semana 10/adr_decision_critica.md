# Registro de Decisión Arquitectónica (ADR) — Semana 10

## Título: Exclusión de Endpoints de Autenticación de la Protección del Circuit Breaker

* **Estado:** Aceptado
* **Contexto:** En el desarrollo de un cliente robusto para EcoMarket, el Circuit Breaker (CB) se encarga de abrir el circuito y rechazar peticiones de red inmediatamente si se alcanza un umbral de fallos en el servidor. Sin embargo, el cliente requiere un token JWT válido (gestionado por `TokenManager`) para realizar peticiones autenticadas. Si el token expira y los endpoints de autenticación (como `/auth/login` o un hipotético `/auth/refresh`) estuvieran protegidos por el mismo Circuit Breaker, su apertura impediría cualquier intento de refrescar credenciales.
* **Decisión:** Decidimos excluir explícitamente las llamadas de autenticación y refresco de tokens de la envoltura del Circuit Breaker principal, permitiendo que el `TokenManager` realice peticiones directas de login/refresco sin pasar por la lógica del disyuntor HTTP.

### Consecuencias Positivas (Ventajas)

1. **Evita el Deadlock de Autenticación (Auth-Breaker Deadlock):** Si el servidor de EcoMarket se recupera pero el cliente se quedó con un token expirado y el circuito abierto, el cliente podrá refrescar el token libremente en lugar de ser rechazado por fail-fast, permitiendo que la petición de prueba en estado SEMIABIERTO lleve credenciales válidas y cierre con éxito el circuito.
2. **Separación Limpia de Responsabilidades (SRP):** El Circuit Breaker se mantiene puramente enfocado en la disponibilidad de los servicios de negocio (inventario, precios, etc.) y es agnóstico del protocolo de autenticación, mientras que el `TokenManager` gestiona el ciclo de vida del JWT de manera autónoma.

### Consecuencias Negativas (Desventajas)

1. **Mayor Carga de Autenticación ante Caída del Servidor de Autenticación:** Si el servidor se cae específicamente en el módulo de autenticación, el cliente seguirá haciendo peticiones de login sin mitigación por parte de este Circuit Breaker (se podría mitigar con un Circuit Breaker secundario exclusivo para la autenticación).
2. **Peticiones concurrentes redundantes de refresh si falla el patrón singleton:** Si falla la coordinación del refresh en el `TokenManager`, múltiples hilos de ejecución podrían intentar refrescar el token concurrentemente contra la red al mismo tiempo bajo presión de fallos, empeorando el estado del servidor.

### Escenario Adverso — ¿Cuándo fallaría esta decisión?

Esta decisión sería incorrecta si el servicio de autenticación y el servicio de productos compartieran el mismo backend monolítico saturado y la caída del sistema fuera provocada por una sobrecarga en la base de datos de usuarios. En ese escenario, permitir que el cliente siga intentando hacer peticiones de refresco de tokens sin el freno del Circuit Breaker empeorará la saturación del servidor, retrasando su recuperación en comparación con tener un disyuntor global que también frenara las peticiones de autenticación.
