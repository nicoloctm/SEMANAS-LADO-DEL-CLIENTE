# Conversación Socrática con la IA
## Semana 10 — Examen Práctico 2 + Hito 2
### Tema: Circuit Breaker, Tokens JWT y Resiliencia en Sistemas Distribuidos

---

> **Nota:** Esta es una conversación educativa entre el estudiante y la IA,
> siguiendo el método socrático: la IA guía con preguntas y el estudiante
> construye el conocimiento paso a paso.

---

## Parte 1: Entendiendo el Circuit Breaker

**IA:** Antes de ver el código, dime: si llamas a un amigo por teléfono y no contesta,
¿cuántas veces intentarías antes de rendirte?

**Estudiante:** Mmm... como 3 o 4 veces. Después de eso ya espero un rato.

**IA:** Exacto. ¿Por qué no seguirías llamando infinitamente?

**Estudiante:** Porque es un gasto de tiempo y batería. Si no contesta, algo pasó.

**IA:** Muy bien. El Circuit Breaker hace exactamente eso con las peticiones de red.
¿Se te ocurre por qué se llama "circuit breaker"?

**Estudiante:** Como los disyuntores eléctricos de la casa, ¿no? Cuando hay un cortocircuito, cortan la luz.

**IA:** ¡Perfecto! ¿Y cuándo vuelve la luz?

**Estudiante:** Cuando alguien va y resetea el disyuntor, o cuando pasa cierto tiempo.

**IA:** Exacto. Ahora mira el código del CircuitBreaker que tienes. ¿Cuántos estados tiene?

**Estudiante:** Tiene tres: CERRADO, ABIERTO y SEMIABIERTO.

**IA:** ¿Qué crees que significa que esté "SEMIABIERTO"?

**Estudiante:** Que... ¿está probando a ver si el servidor ya volvió? ¿Como cuando reseteas el disyuntor con cuidado?

**IA:** Exactamente. ¿Y por qué solo deja pasar una petición en ese estado?

**Estudiante:** Para no sobrecargar al servidor si todavía está débil.

**IA:** Perfecto. Ya entendiste el estado SEMIABIERTO sin que yo te lo explicara directamente.
¿Ves el poder del método socrático?

---

## Parte 2: Encontrando el Bug A

**IA:** Mira el código original del `CircuitBreaker`. ¿Qué te llama la atención sobre sus responsabilidades?

**Estudiante:** Hay código que lee el token JWT dentro del método `ejecutar`... eso me parece raro.

**IA:** ¿Por qué te parece raro?

**Estudiante:** Porque el CircuitBreaker debería saber solo si el servidor está caído o no.
Los tokens son para otra cosa.

**IA:** Exacto. Si yo te pido que cuides la puerta de entrada, ¿es tu trabajo también
revisar los carnés de identidad de las personas?

**Estudiante:** No, eso sería de otra persona. El portero solo cuida que no entre nadie sin permiso de otro.

**IA:** Eso se llama "Principio de Responsabilidad Única". Cada componente hace **una sola cosa**.
¿Qué consecuencias tendría que el CircuitBreaker manejara tokens?

**Estudiante:** Si cambian el formato del token, el CircuitBreaker también se rompe aunque él no haga nada malo.

**IA:** ¡Muy bien! ¿Y cómo lo arreglarías?

**Estudiante:** Sacando todo lo de tokens del CircuitBreaker y poniendo eso en otro lugar.

**IA:** ¿En cuál?

**Estudiante:** En un `TokenManager` quizás. Algo que solo sepa de tokens.

**IA:** Exacto. ¿Ves cómo llegaste tú mismo a la solución?

---

## Parte 3: El Bug de Seguridad

**IA:** Supón que anotas tu contraseña bancaria en un papel y lo dejas en la oficina.
¿Qué podría pasar?

**Estudiante:** Alguien la vería y podría entrar a mi cuenta.

**IA:** Los logs del sistema son como esos papeles. Si el código imprime el token en los logs,
¿qué riesgo hay?

**Estudiante:** Que alguien que lea los logs robe el token y lo use para hacerse pasar por el usuario.

**IA:** Exacto. ¿Qué información mínima necesitas en los logs para saber que el sistema funciona?

**Estudiante:** Solo algo como "token refrescado OK". No necesito ver el token en sí.

**IA:** Perfecto. Esa es exactamente la corrección que hicimos. ¿Cuál es la regla general?

**Estudiante:** Nunca poner credenciales en los logs, aunque sea solo una parte.

---

## Parte 4: El Bug del Contador de Fallos

**IA:** Imagina que tienes un vaso con agua. Lo llenas hasta la mitad y lo vacías.
¿Cuánta agua queda?

**Estudiante:** Ninguna. Queda vacío.

**IA:** Ahora imagina que el CircuitBreaker tiene un "vaso de fallos". Cuando el circuito
se cierra después de una recuperación, ¿debería quedar vacío o seguir con agua?

**Estudiante:** Debería quedar vacío. Si el servidor se recuperó, hay que empezar de cero.

**IA:** ¿Qué pasa si no lo vaciamos?

**Estudiante:** Si ya tenía 4 fallos guardados y el umbral es 5, el próximo fallo abriría el circuito
aunque el servidor esté bien.

**IA:** ¿Se vuelve más o menos estable el sistema?

**Estudiante:** Menos estable. Estaría "nervioso", abriéndose por casi nada.

**IA:** Exacto. ¿Cuál es la solución?

**Estudiante:** Resetear el contador a 0 cuando el circuito se cierra.

**IA:** Y eso es exactamente el Bug C que corregimos. ¿Ves el patrón?

---

## Parte 5: Tokens JWT y el Refresh Singleton

**IA:** Si 10 personas llegan a la recepción al mismo tiempo a pedir turno,
¿el recepcionista debería atenderlos a todos por separado o buscar una forma de atenderlos juntos?

**Estudiante:** Juntos, si puede. Sería más eficiente.

**IA:** El TokenManager tiene el mismo problema. Si 10 partes del código piden un token nuevo
al mismo tiempo, ¿qué pasaría si hace una petición por cada una?

**Estudiante:** Habría 10 peticiones al servidor de autenticación al mismo tiempo. Eso es ineficiente.

**IA:** ¿Cómo lo solucionarías?

**Estudiante:** Haciendo que la primera petición se encargue de pedir el token, y las otras 9 esperen
ese mismo resultado.

**IA:** Eso se llama patrón "Singleton" para el refresh. ¿Puedes ver dónde lo implementamos?

**Estudiante:** Sí, en `refresh_access_token()` con el `asyncio.Task`. Si ya hay una tarea corriendo,
las demás esperan esa misma tarea.

**IA:** ¿Qué pasa si esa tarea falla?

**Estudiante:** Debería limpiar la tarea para que la próxima vez se intente de nuevo.

**IA:** Y eso es exactamente lo que hace el bloque `finally` en `_do_refresh()`.

---

## Parte 6: Reflexión Final

**IA:** Recapitulando, ¿qué aprendiste esta semana?

**Estudiante:** Aprendí que:
1. El Circuit Breaker protege al sistema cuando el servidor falla, como un disyuntor eléctrico.
2. Cada componente debe hacer una sola cosa (SRP), si no se vuelven difíciles de mantener.
3. Las credenciales nunca deben aparecer en logs.
4. Los contadores de estado deben resetearse correctamente para que el sistema sea estable.
5. Si múltiples partes piden lo mismo, es mejor hacer una sola petición y compartir el resultado.

**IA:** ¿Algo te sorprendió?

**Estudiante:** Que muchos de estos conceptos ya los conocía de la vida real.
El Circuit Breaker es un disyuntor, el Singleton es una sola fila en la recepción.
La programación tiene muchas analogías con cosas cotidianas.

**IA:** Esa es la señal de que realmente entendiste. Cuando puedes explicar algo con palabras simples,
lo has aprendido de verdad.

---

## Conceptos Aprendidos en Esta Sesión

| Concepto | Analogía usada |
|----------|---------------|
| Circuit Breaker | Disyuntor eléctrico / llamadas al teléfono |
| Estado SEMIABIERTO | Resetear el disyuntor con cuidado |
| SRP (Responsabilidad Única) | El portero no revisa carnés de identidad |
| Tokens en logs | Anotar la contraseña en un papel público |
| Reset de contadores | Vaciar el vaso al terminar |
| Refresh Singleton | Un recepcionista para todos en lugar de uno por persona |
