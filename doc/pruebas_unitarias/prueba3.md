PRUEBA UNITARIA 1: APUESTA EXITOSA EN RULETA
1️⃣ Identificación
Nombre de la prueba: Apuesta exitosa en ruleta
Módulo / Componente: Juego “Ruleta”
2️⃣ Objetivo
Comprobar que el sistema permite realizar correctamente una apuesta válida en la ruleta, descontando el monto apostado del saldo y mostrando el resultado de la jugada.
3️⃣ Alcance
Se evalúa solo la funcionalidad de realizar una apuesta válida y la respuesta del sistema, sin incluir el cobro de premios o el historial de apuestas.
4️⃣ Diseño de la prueba
a) Particiones de equivalencia
Parámetro	Clases válidas	Clases inválidas
Monto apostado	Valor numérico positivo (> 0)	0 o negativo
Tipo de apuesta	Número individual, color o paridad	Opción inexistente / nula
Selección de número	Entre 0 y 36	Menor que 0 o mayor que 36
b) Valores límite
Parámetro	Límite inferior	Límite superior
Monto apostado	1 unidad	Sin límite (depende del saldo del usuario)
Número apostado	0	36
5️⃣ Datos de entrada (ejemplo)
Campo	Valor
Tipo de apuesta	Número
Selección	17
Monto apostado	10 créditos
Saldo inicial	100 créditos
6️⃣ Pasos de ejecución
Iniciar sesión con un usuario válido.
Acceder al módulo “Ruleta”.
Seleccionar el número 17, junto al monto de 10 créditos.
Pulsar “Girar”.
Esperar el resultado de la jugada.
7️⃣ Resultado esperado
El sistema acepta la apuesta.
Se descuenta el monto apostado del saldo.
Se muestra la animación y posteriormente el resultado de la ruleta.
Se indica si el usuario ganó o perdió.
No se presentan errores de validación.
8️⃣ Resultado obtenido
(Completar tras ejecución)
▢ Correcto — la apuesta se realizó con éxito y se procesó el resultado.
▢ Incorrecto — se mostró error o la apuesta no fue procesada.
9️⃣ Criterio de éxito
La prueba se considera superada si el sistema acepta la apuesta válida, actualiza el saldo y muestra el resultado sin errores.
🔟 Observaciones / Notas
El saldo del usuario se debe actualizar de forma inmediata.
Se puede verificar en la base de datos que la apuesta fue registrada con los valores correctos
