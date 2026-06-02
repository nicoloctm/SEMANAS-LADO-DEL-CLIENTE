# Reporte de Completitud — Semana 10

**Proyecto:** Grand Deploy — Examen Práctico 2 + Hito 2 (AETL)  
**Cobertura:** 14 archivos analizados en `Semana 10/`  
**Estado general: ~65% completado**

---

## ✅ Completado (implementación + documentación presente)

| Componente | Archivo | Estado |
|---|---|---|
| CircuitBreaker (3 estados, transiciones, callbacks, INV-A1 a INV-A4) | `circuit_breaker.py` | ✅ Completo |
| TokenManager (decode JWT, auth header, refresh singleton INV-B3) | `token_manager.py` | ✅ Completo |
| ClienteRobusto (orquestación CB+TM, SRP, PREP headers) | `cliente_robusto.py` | ✅ Completo |
| Servidor mock para pruebas locales | `mock_ecomarket.py` | ✅ Completo |
| Demo de integración ejecutable (login → fallos → fail-fast → recuperación) | `cliente_integrado.py` | ✅ Completo |
| Pruebas automatizadas (8 tests: TC-01 a TC-08, INV-A1 a INV-A4, CB) | `test_circuit_breaker.py` | ✅ Completo |
| Autopsia de 3 bugs (SRP, token en logs, reset de fallos) | `autopsia_bugs.md` | ✅ Completo |
| Checklist de 8 invariantes (A1-A4, B1-B3, C1) con evidencia en código | `checklist_invariantes.md` | ✅ Completo |
| Casos de prueba cruzada y regresión (CX-01 a CX-04, REG-01 a REG-03) | `tc_cross_regression.md` | ✅ Completo |
| Bitácora de uso de IA (5 sesiones documentadas con reflexión) | `bitacora_ia.md` | ✅ Completo |
| Conversación socrática (método guiado de aprendizaje) | `conversacion_socratica.md` | ✅ Completo |
| README del proyecto (requisitos, ejecución, arquitectura) | `README.md` | ✅ Completo |

---

## ❌ Faltante / No completado

### Examen Práctico 2 (12 %)

| Requisito | Reto / XP | Archivo esperado |
|---|---|---|
| Asignación de 5 fragmentos con justificación técnica | **Reto 1** — 8 XP | Sin archivo específico |
| Diagrama de flujo con 5 nodos [?N] completados | **Reto 2** — 7 XP | `diagrama_flujo.txt` |
| ADR Express: decisión arquitectónica documentada | **Reto 5** — 15 XP | `adr_decision_critica.md` |
| Prueba automatizada TC-X2 (token expira en SEMIABIERTO) | **Reto 8** — 6 pts | `test_tc_x2_refresh_semiaabierto.py` |
| Salida de consola / log del Reto 4 (estado observable UI) | **Reto 4** — evidencia | Log de ejecución (no presente) |
| Checkpoints metacognitivos respondidos (4 preguntas) | **Meta** — 10 XP | Sin archivo específico |

### Hito 2 (15 %)

| Requisito | Archivo esperado |
|---|---|
| Repositorio o .zip reproducible con tag `hito2` | URL / .zip |
| Demo log de resiliencia (≥10 peticiones, 3 fases del circuito) | `demo_resiliencia.log` |
| ADR Express (decisión arquitectónica crítica) | `adr_decision_critica.md` |
| Documentación de contribución del equipo | `contribucion_equipo.md` |
| Prueba automatizada TC-X2 (obligatoria) | `test_tc_x2_refresh_semiaabierto.py` |

### Bonus (fuera de taller)

| Requisito | Reto / XP extra |
|---|---|
| Árbitro de Reconexión SSE — 3 estrategias evaluadas | **Reto 6** — +7 XP |
| Postmortem del Hito 2 — retrospectiva de arquitecto | **Reto 9** — +5 XP |
| Preview WebSocket — adaptación del CB | **Reto 10** — +3 XP |

---

## Desglose por fase (base XP del examen — 100 XP)

| Fase | XP base | Obtenido estimado | % |
|---|---|---|---|
| F1: Comprende (Retos 1 + 2) | 15 | 0 | **0 %** |
| F2: Aplica (Retos 3 + 4) | 35 | ~30 | **~86 %** |
| F3: Reflexiona (Reto 5) | 15 | 0 | **0 %** |
| F4: Valida (Retos 7 + 8) | 25 | ~18 | **~72 %** |
| F5: Profundiza (Meta) | 10 | 0 | **0 %** |
| **Total base** | **100** | **~48** | **~48 %** |

**Notas:**
- Reto 3 (autopsia bugs): completo — 20/20
- Reto 4 (integración): código funcional, pero sin log de salida ni evidencia de estado observable UI → ~10/15
- Reto 7 (invariantes): checklist completo con evidencia — 13/13
- Reto 8 (tests cruzada): documentación de casos presente, pero falta prueba automatizada TC-X2 → ~5/12

---

## Resumen Hito 2 (rúbrica — 100 pts base)

| Criterio | Pts | Estimado |
|---|---|---|
| CircuitBreaker: 3 estados + transiciones | 15 | ✅ 15 |
| TokenManager: decode + auth header + refresh singleton | 12 | ✅ 12 |
| ClienteRobusto: orquesta sin duplicar (SRP) | 12 | ✅ 12 |
| Clasificación correcta de errores (401 ≠ fallo servidor) | 12 | ✅ 12 |
| Prueba automatizada reproducible | 12 | ⚠️ 6 (falta TC-X2) |
| Estado observable del cliente (apertura/cierre) | 10 | ✅ 10 |
| Documentación de decisiones y uso de IA | 12 | ⚠️ 6 (falta ADR) |
| Repositorio/README reproducible y trazabilidad | 10 | ⚠️ 5 (README OK, sin repo) |
| Contribución del equipo documentada | 5 | ❌ 0 |
| **Total** | **100** | **~78** |

---

## Recomendaciones (prioridad)

1. **Alta** — Crear `adr_decision_critica.md` (Reto 5, 15 XP + Hito 2)
2. **Alta** — Crear prueba automatizada `test_tc_x2_refresh_semiaabierto.py` (Reto 8, 6 pts + Hito 2)
3. **Alta** — Documentar `diagrama_flujo.txt` con los 5 nodos (Reto 2, 7 XP)
4. **Media** — Generar `demo_resiliencia.log` ejecutando `cliente_integrado.py`
5. **Media** — Crear `contribucion_equipo.md` (Hito 2, 5 pts)
6. **Media** — Responder checkpoints metacognitivos (10 XP)
7. **Baja** — Completar bonus: Reto 6 (+7 XP), Reto 9 (+5 XP), Reto 10 (+3 XP)
