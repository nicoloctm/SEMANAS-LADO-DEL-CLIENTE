# Semana 5: Evaluación y Consolidación

Entregables del simulacro de examen práctico y de las reflexiones de la Semana 5.

## Archivos
1. **`monitor_pedidos.py`**: Simulacro (Reto 2) aplicando programación asíncrona, polling adaptativo y el patrón Observer para EcoMarket.
2. **`conversacion_socratica_semana5.md`**: Conversación donde se justifican las decisiones de diseño del cliente (Reto 3).

## Decisiones de Diseño Destacadas
- Manejo asíncrono y Timeouts para no bloquear la aplicación.
- Backoff progresivo ante fallos del servidor y respuestas 304 para mitigar carga.
- Patrón Observer implementado para separar las acciones de las consultas periódicas de datos.
