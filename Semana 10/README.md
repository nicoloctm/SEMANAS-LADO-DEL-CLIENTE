# README — Semana 10: Grand Deploy
## Examen Práctico 2 + Hito 2
### Sistema: Cliente Robusto EcoMarket con Circuit Breaker

---

## ¿Qué hace este proyecto?

Este proyecto implementa un **cliente HTTP robusto** para conectarse al mercado EcoMarket.
"Robusto" significa que el cliente puede manejar situaciones difíciles:

- Si el servidor falla repetidamente, **abre el circuito** y deja de intentar (fail-fast).
- Gestiona los **tokens de autenticación** de forma segura y eficiente.
- Se recupera automáticamente cuando el servidor vuelve a estar disponible.

---

## Archivos del proyecto

| Archivo | Descripción |
|---------|-------------|
| `circuit_breaker.py` | El disyuntor: controla cuándo se permiten peticiones |
| `token_manager.py` | Gestión de tokens JWT con refresco seguro |
| `cliente_robusto.py` | Integra los dos componentes anteriores |
| `mock_ecomarket.py` | Servidor falso para pruebas locales |
| `cliente_integrado.py` | Demo completa del sistema |
| `test_circuit_breaker.py` | Pruebas automatizadas |

### Documentación
| Archivo | Descripción |
|---------|-------------|
| `autopsia_bugs.md` | Análisis de los 3 bugs corregidos |
| `checklist_invariantes.md` | Las 8 reglas del sistema y su cumplimiento |
| `tc_cross_regression.md` | Casos de prueba cruzada y regresión |
| `bitacora_ia.md` | Registro del uso de la IA |
| `conversacion_socratica.md` | Diálogo socrático del aprendizaje |

---

## Requisitos

```
Python 3.8 o superior
aiohttp
```

Instalar dependencias:
```bash
pip install aiohttp
```

---

## Cómo ejecutar

### Demo completa (recomendado para empezar)
```bash
python cliente_integrado.py
```
Este script levanta el servidor mock y ejecuta 4 escenarios automáticamente.

### Solo el servidor mock
```bash
python mock_ecomarket.py
```

### Pruebas automatizadas
```bash
python test_circuit_breaker.py
```

---

## Los 3 Bugs Corregidos

| Bug | Problema | Invariante |
|-----|----------|------------|
| A | CircuitBreaker procesaba tokens JWT (violaba SRP) | INV-A1 |
| B | El token aparecía en los logs (riesgo de seguridad) | INV-B1 |
| C | El contador de fallos no se reseteaba al cerrar | INV-A3 |

Para ver el análisis completo: [`autopsia_bugs.md`](./autopsia_bugs.md)

---

## Los 4 Estados del Sistema (Circuit Breaker)

```
CERRADO ──(3 fallos)──► ABIERTO ──(5s timeout)──► SEMIABIERTO
   ▲                                                     │
   └──────────────(petición exitosa)────────────────────┘
```

- **CERRADO:** Todo funciona. Las peticiones pasan normalmente.
- **ABIERTO:** Muchos fallos. Rechaza peticiones sin tocar el servidor.
- **SEMIABIERTO:** Probando recuperación. Solo pasa una petición de prueba.

---

## Evidencia de Funcionamiento

Al ejecutar `cliente_integrado.py`, se verá una salida como:

```
  Mock EcoMarket activo en http://localhost:8080

═══════════════════════════════════════════════════════
  DEMO - Cliente Robusto EcoMarket
═══════════════════════════════════════════════════════

  [1] Petición normal (circuito CERRADO)
      ✔ Recibidos 3 productos. Circuito: CERRADO

  [2] Activando modo falla en el servidor...
      ✘ Intento 1: ConnectionError - Error del servidor: 500
      Estado circuito: CERRADO
      ✘ Intento 2: ConnectionError - Error del servidor: 500
      Estado circuito: CERRADO
      [CircuitBreaker] CERRADO → ABIERTO
      ✘ Intento 3: ConnectionError - Error del servidor: 500
      Estado circuito: ABIERTO

  [3] Petición con circuito ABIERTO (debe fallar rápido)
      ✘ CircuitOpenError: Circuito abierto. Reintente en 4s

  [4] Desactivando modo falla y esperando timeout (6s)...
      [CircuitBreaker] ABIERTO → SEMIABIERTO
      [CircuitBreaker] SEMIABIERTO → CERRADO
      ✔ ¡Recuperado! 3 productos. Circuito: CERRADO

═══════════════════════════════════════════════════════
  FIN DE LA DEMO
═══════════════════════════════════════════════════════
```

---

## Arquitectura del sistema

```
ClienteRobusto
├── TokenManager  (solo gestiona autenticación)
│   ├── is_expiring_soon()
│   ├── refresh_access_token()  ← Singleton async
│   └── get_auth_header()
└── CircuitBreaker  (solo gestiona conectividad)
    ├── estado: CERRADO/ABIERTO/SEMIABIERTO
    ├── ejecutar(fn)
    └── on_state_change callback
```

Cada componente tiene **una sola responsabilidad**. No se mezclan.
