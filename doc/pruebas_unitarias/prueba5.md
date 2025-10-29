# PRUEBAS UNITARIAS: BLACKJACK

## PRUEBA 1: Inicio de partida con apuesta válida

### Identificación
- **Nombre**: Inicio de partida con apuesta válida
- **Módulo**: Juego "Blackjack"

### Objetivo
Comprobar que el sistema permite iniciar una partida correctamente cuando el usuario introduce una cantidad válida y que la interfaz se actualiza para mostrar la mesa de juego.

### Alcance
Se evalúa solo la funcionalidad de inicio de partida (no se contemplan acciones de juego posteriores como pedir, plantar o doblar).

### Diseño de la prueba
**Particiones de equivalencia:**
- Parámetro: cantidad de apuesta
  - Clases válidas: valores numéricos positivos ≤ saldo
  - Clases inválidas: 0, negativos, texto, null, undefined, valor > saldo

**Valores límite:**
- Límite inferior: 1
- Límite superior: igual al saldo disponible
  
### Datos de entrada
Apuesta = 50
Saldo = 1000

### Pasos de ejecución
1. Acceder al módulo “Blackjack”.
2. Establecer saldo del usuario en 1000 €.
3. Ingresar la cantidad de apuesta: 50.
4. Ejecutar botón 'Iniciar simulación'
5. Observar el comportamiento de la interfaz:
-Oculta el panel de apuesta.
-Muestra la mesa de juego.
-Muestra las dos cartas iniciales del jugador y una visible del crupier.

### Resultado esperado
- `Saldo = 950´
- El panel de apuesta desaparece.
- Se muestra la mesa de juego con cartas iniciales.

---

## PRUEBA 2: VALIDACIÓN DE APUESTA CON SALDO INSUFICIENTE

### Identificación
- **Nombre**: Validación de apuesta con saldo insuficiente
- **Módulo**: Juego "Blackjack"

### Objetivo
Comprobar que el sistema impide iniciar una partida cuando el jugador intenta apostar una cantidad mayor a su saldo disponible, mostrando el mensaje de error correspondiente y sin alterar el estado del juego.

### Alcance
Se evalúa únicamente la validación previa al inicio del juego, sin ejecutar la simulación ni modificar estadísticas.

### Diseño de la prueba
**Particiones de equivalencia:**
- Parámetro: Cantidad de apuesta
  - Clases válidas: valores ≤ saldo
  - Clases inválidas: valores > saldo

### Datos de entrada
Saldo = 1000
Apuesta = 1500

### Pasos de ejecución
1. Acceder al módulo “Blackjack”.
2. Establecer el saldo del usuario en 1000 €.
3. Introducir en el campo de apuesta el valor 1500.
4. Ejecutar el botón 'iniciar simulación'.

### Resultado esperado
- Aparece una alerta con el mensaje “FONDOS INSUFICIENTES”.
- El saldo no cambia.

---

## PRUEBA 3: BOTONES DE APUESTA RÁPIDA RELLENAN EL INPUT CORRECTAMENTE

### Identificación
- **Nombre**: BOTONES DE APUESTA RÁPIDA RELLENAN EL INPUT CORRECTAMENTE
- **Módulo**: Juego "Blackjack"

### Objetivo
Verificar que los botones de apuesta rápida (25, 50, 100) rellenan el campo de entrada de apuesta con el valor correspondiente y que el valor resultante es válido para iniciar una partida.

### Alcance
Se evalúa únicamente la funcionalidad de los botones de apuesta rápida y la actualización del campo de entrada, sin iniciar la partida ni efectuar cambios en el saldo.

### Diseño de la prueba
**Particiones de equivalencia:**
- Parámetro: Botón de apuesta rápida pulsado
  - Clases válidas: botones existentes
  - Clases inválidas: botones inexistentes

### Datos de entrada
Ninguno en el sentido de parámetros de función; la prueba simula clicks en los botones:
 -Botones objetivo: button con onclick="apuestaRapida(25)", apuestaRapida(50), apuestaRapida(100)
 -Campo de entrada: elemento con id cantidad

### Pasos de ejecución
1. Acceder al módulo “Blackjack”.
2. Asegurarse de que el campo 'Apuesta' existe y tiene un valor inicial
3. Ejecutar la acción asociada al botón de 25
4. Comprobar el valor del input
5. Repetir para los botones 50 y 100

### Resultado esperado
- Tras pular el boton de 25,'Apuesta' = "25".
- Tras pular el boton de 50,'Apuesta' = "50".
- Tras pular el boton de 100,'Apuesta' = "100".

---

## PRUEBA 4: BOTÓN PEDIR AÑADE UNA CARTA Y ACTUALIZA PUNTOS VISIBLES, Y SI AL PEDIR LA MANO SUPERA 21, SE MUESTRA "BUSTED" Y SE DESHABILITAN ACCIONES PARA ESA MANO

### Identificación
- **Nombre**: BOTÓN PEDIR AÑADE UNA CARTA Y ACTUALIZA PUNTOS VISIBLES, y si al pedir la mano supera 21, se muestra mano “busted” y se deshabilitan acciones para esa mano.
- **Módulo**: Juego "Blackjack" 

### Objetivo
Verificar que al pulsar el botón PEDIR, el sistema entrega una nueva carta al jugador, actualiza los puntos mostrados en pantalla y refleja correctamente si el jugador se pasa de 21.

 ### Diseño de la prueba
**Particiones de equivalencia:**
- Parámetro: Botón de apuesta rápida pulsado
  - Clases válidas: Cuando el juego está activo y mano no terminada.
  - Clases inválidas: Cuando el juego no está activo o mano ya terminada.


### Pasos de ejecución
1. Iniciar el Blackjack
2. En el campo “APUESTA”, introducir una cantidad válida (por ejemplo, 10 €) y pulsar “INICIAR SIMULACIÓN”.
3. Esperar a que se repartan las cartas iniciales: El jugador ve dos cartas visibles en su zona y el crupier muestra una carta visible y otra oculta.
4. Pulsar el botón “PEDIR”.
5. Si los puntos del jugador no superan 21, el juego continúa normalmente y los botones siguen activos.
6. Si los puntos del jugador superan 21, el marcador se muestra en color rojo y el jugador no puede seguir pidiendo cartas.

### Resultado esperado
- Al pulsar “PEDIR”, aparece una carta nueva en la zona del jugador.
- El marcador de puntos del jugador se actualiza inmediatamente mostrando el nuevo total.
- Si el total de puntos supera 21, el número aparece en rojo y el jugador pierde automáticamente su turno.
- Si el total no supera 21, los botones de acción (PEDIR, PLANTARSE) siguen disponibles.
- En ningún caso el juego se bloquea ni muestra errores visibles.
- El saldo del jugador permanece igual hasta que la ronda termina.

---

## PRUEBA 5: BOTÓN “PLANTARSE” FINALIZA LA MANO ACTUAL Y PASA AL SIGUIENTE PASO

### Identificación
- **Nombre**: BOTÓN “PLANTARSE” FINALIZA LA MANO ACTUAL Y PASA AL SIGUIENTE PASO
- **Módulo**: Juego "Blackjack"

### Objetivo
Comprobar que al pulsar PLANTARSE el jugador finaliza su turno para la mano activa y el flujo avanza correctamente: bien al turno del crupier o a la siguiente mano del jugador.

### Pasos de ejecución
1. Pulsar el botón PLANTARSE.

### Resultado esperado
- El jugador no puede pedir más cartas para esa mano.
- La carta oculta del crupier se revela y el crupier inicia su turno (se ven las animaciones/robos del crupier).
- Los botones de acción del jugador quedan deshabilitados hasta que la ronda termine.

---

## PRUEBA 6: AL DOBLAR, LA APUESTA SE DUPLICA, SE ROBA UNA CARTA Y LA ACCIÓN SE ACABA.

### Identificación
- **Nombre**: DOBLAR, LA APUESTA SE DUPLICA, SE ROBA UNA CARTA Y LA ACCIÓN SE ACABA.
- **Módulo**: Juego "Blackjack"

### Objetivo
Comprobar, desde la perspectiva del usuario, que al usar la función DOBLAR:
-La apuesta de la mano se duplica descontando el importe adicional del saldo visible,
-El sistema reparte exactamente una carta adicional al jugador,
-La acción termina inmediatamente la mano (no se puede pedir más cartas para esa mano),
-La opción DOBLAR solo está disponible cuando la mano tiene exactamente dos cartas y hay saldo suficiente para igualar la apuesta original,

### Pasos de ejecución
1. Pulsar el botón DOBLAR.

### Resultado esperado
- El saldo visible se reduce inmediatamente por el importe adicional requerido para igualar la apuesta
- La apuesta de la mano queda duplicada o la UI muestra claramente que la mano está doblada.
- Se añade una única carta al conjunto de cartas del jugador (visible inmediatamente).
- El jugador no puede pedir más cartas para esa mano

---

## PRUEBA 7: BOTÓN “SEPARAR (SPLIT)” DIVIDE LA MANO EN DOS, COBRA LA SEGUNDA APUESTA Y REPARTE CARTAS A CADA MANO

### Identificación
- **Nombre**: BOTÓN “SEPARAR (SPLIT)” DIVIDE LA MANO EN DOS, COBRA LA SEGUNDA APUESTA Y REPARTE CARTAS A CADA MANO
- **Módulo**: Juego "Blackjack"

### Objetivo
Verificar que:
-La acción solo está disponible cuando las dos cartas iniciales del jugador tienen el mismo valor.
-El sistema cobra la segunda apuesta (igual a la apuesta inicial) descontándola del saldo visible.
-La mano del jugador se divide en dos manos visibles, cada una con una carta original y una carta adicional repartida automáticamente.
-Las acciones disponibles y el flujo permiten jugar cada mano por separado o quedan deshabilitadas cuando corresponda.

### Pasos de ejecución:
1. Observar las dos cartas iniciales del jugador; comprobar visualmente que tienen el mismo valor.
2. Pulsar el boton SEPARAR.

### Resultado esperado
- El saldo visible disminuye en la cantidad igual a la apuesta inicial.
- La zona del jugador muestra dos manos separadas, cada una con 2 cartas (una original + una nueva repartida).
- Al terminar la primera mano, la UI pasa a la segunda mano y habilita las acciones correspondientes.
- La apuesta total en juego equivale a la suma de las apuestas por mano.

---
