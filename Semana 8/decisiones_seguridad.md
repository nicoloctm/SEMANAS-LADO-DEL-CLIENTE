# Reflexiones de Seguridad (Reto 5 - Ruta Python)

A continuación, respondo a las preguntas de auditoría del equipo de EcoMarket sobre mis decisiones de diseño en el `TokenManager` (aplicación Python).

**1. Almacenamiento: access_token y refresh_token en memoria.**
- *Auditor: ¿Qué pasa si otro proceso en el mismo equipo hace kill -9 a tu proceso mientras tienes el access_token en memoria? ¿Dónde está el refresh_token en ese momento?*
- **Respuesta:** En mi implementación actual, ambos tokens residen puramente en la memoria RAM asignada al proceso de Python. Si el proceso recibe un `kill -9`, toda la memoria se destruye y el estado se pierde. Esto protege contra lectura por otros procesos, pero obliga al usuario a re-autenticarse tras un reinicio. Para producción, el access_token (corta vida) está bien en memoria, pero el `refresh_token` debería almacenarse en el llavero seguro del SO (como `keyring` en Python) de forma cifrada para sobrevivir reinicios de manera segura. Si usara un archivo plano, tendría vulnerabilidades ante lecturas de otros usuarios locales (compromiso de sistema de archivos).

**2. Margin de refresh proactivo de 300 segundos (5 minutos).**
- *Auditor: ¿Por qué elegiste este margin de refresh de 300 segundos y no 60 segundos o 10 minutos?*
- **Respuesta:** Si el access_token dura 15 minutos, elegir 10 minutos provocaría un refresh casi de inmediato tras el login, duplicando la carga del servidor (renovando tokens que aún tienen 2/3 de vida). Si elijo 60 segundos, el margen es muy corto y nos hace susceptibles al problema del *clock skew* (si el reloj de la máquina del cliente está adelantado por 2 minutos, el token será invalidado por el servidor antes de que el cliente decida renovarlo proactivamente, cortando conexiones activas). 5 minutos es un balance ideal que absorbe desincronizaciones razonables sin sobrecargar el servidor de Auth.

**3. Manejo de refresh singleton con asyncio.Lock.**
- *Auditor: ¿Tu asyncio.Lock protege el refresh si hay múltiples workers o procesos (no solo co-rutinas)? ¿Qué mecanismo necesitarías para escenarios multi-proceso?*
- **Respuesta:** El `asyncio.Lock` **solo** protege entre múltiples co-rutinas (`async def`) dentro del *mismo hilo* y del *mismo proceso*. Si desplegamos este cliente usando `gunicorn` con 4 workers, o múltiples instancias en contenedores, cada worker tendrá su propio Lock y su propia instancia en memoria. Por tanto, 4 peticiones 401 simultáneas (una por worker) desencadenarían 4 refreshes al backend, resultando en un "thundering herd" que el servidor podría rechazar. En un escenario multi-proceso, necesitaríamos un lock distribuido (por ejemplo usando Redis `SETNX`) para garantizar el singleton a nivel global.

**4. Comportamiento ante refresh fallido (reintento único y logout).**
- *Auditor: Si guardas el refresh_token en un archivo en disco, ¿qué permisos debe tener ese archivo y por qué? Y sobre el loop: ¿qué hace tu cliente cuando el refresh_token también devuelve 401?*
- **Respuesta:** Si guardara en disco, el archivo debe tener permisos estrictos `chmod 600` para que solo el usuario dueño del proceso pueda leerlo, protegiendo contra usuarios locales sin privilegios. Respecto al refresh, si mi `auth_request` intercepta el 401 del endpoint de refresh, en lugar de intentar refrescar el refresh, limpio la memoria llamando a `logout()` inmediatamente y corto la cadena de reintentos. Esto detiene loops infinitos que de lo contrario realizarían miles de peticiones al servidor en segundos.
