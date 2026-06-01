# Semana 4: Cliente Polling y Observables - EcoMarket

Esta carpeta contiene los entregables para los retos de la Semana 4.

## Archivos

1. **`monitor.py`**: Implementación de la clase `ServicioPolling` y `Observable`, manejando peticiones HTTP simuladas, intervalos de backoff y notificaciones a múltiples observadores (Reto 2). También contiene en la cabecera los docstrings documentando los **trade-offs** y decisiones de diseño (Reto 3).
2. **`conversacion_socratica.md`**: Un archivo con una discusión socrática (Reto 3 y Reto de IA) donde el alumno inexperto razona las decisiones de diseño junto con la IA.
3. **`validacion.log`**: La salida de consola y resultados de la validación frente a los casos de error (Reto 4).

## Traza del Reto 1 (Conceptos)
- Se comprendió la diferencia fundamental entre el modelo Pull (el cliente pregunta) y el Push (el servidor avisa).
- Se implementó un ciclo de Short Polling adaptativo, donde el tiempo de espera crece si no hay cambios.
- El patrón Observer logró separar completamente la lógica de realizar peticiones, de la lógica de reaccionar a la nueva información (UI, logs, alertas).
