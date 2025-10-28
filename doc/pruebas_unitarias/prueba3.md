# PRUEBAS UNITARIAS: LA RULETA

## PRUEBA UNITARIA 1: APUESTA EXITOSA EN RULETA

### 1️⃣ Identificación

* **Nombre de la prueba:** Apuesta exitosa en ruleta  
* **Módulo / Componente:** *Juego “Ruleta”*

---

### 2️⃣ Objetivo

Comprobar que el sistema permite realizar correctamente una apuesta válida en la ruleta, descontando el monto apostado del saldo y mostrando el resultado de la jugada.

---

### 3️⃣ Alcance

Se evalúa solo la funcionalidad de **realizar una apuesta válida** y la **respuesta del sistema**, sin incluir el cobro de premios o el historial de apuestas.

---

### 4️⃣ Diseño de la prueba

#### a) Particiones de equivalencia

| Parámetro | Clases válidas | Clases inválidas |
| ---------- | --------------- | ---------------- |
| Monto apostado | Valor numérico positivo (> 0) | 0 o negativo |
| Tipo de apuesta | Número individual, color o paridad | Opción inexistente / nula |
| Selección de número | Entre 0 y 36 | Menor que 0 o mayor que 36 |

#### b) Valores límite

| Parámetro | Límite inferior | Límite superior |
| ---------- | ---------------- | ---------------- |
| Monto apostado | 1 unidad | Sin límite (depende del saldo del usuario) |
| Número apostado | 0 | 36 |

---

### 5️⃣ Datos de entrada (ejemplo)

| Campo | Valor |
| ------ | ------ |
| Tipo de apuesta | Número |
| Selección | 17 |
| Monto apostado | 10 créditos |
| Saldo inicial | 100 créditos |

---

### 6️⃣ Pasos de ejecución

1. Iniciar sesión con un usuario válido.  
2. Acceder al módulo **“Ruleta”**.  
3. Seleccionar el número **17**, junto al monto de **10 créditos**.  
4. Pulsar **“Girar”**.  
5. Esperar el resultado de la jugada.

---

### 7️⃣ Resultado esperado

* El sistema acepta la apuesta.  
* Se descuenta el monto apostado del saldo.  
* Se muestra la animación y posteriormente el resultado de la ruleta.  
* Se indica si el usuario ganó o perdió.  
* No se presentan errores de validación.

---

### 8️⃣ Resultado obtenido

*(Completar tras ejecución)*

* ▢ Correcto — la apuesta se realizó con éxito y se procesó el resultado.  
* ▢ Incorrecto — se mostró error o la apuesta no fue procesada.

---

### 9️⃣ Criterio de éxito

La prueba se considera **superada** si el sistema acepta la apuesta válida, actualiza el saldo y muestra el resultado sin errores.

---

### 🔟 Observaciones / Notas

* El saldo del usuario se debe actualizar de forma inmediata.  
* Se puede verificar en la base de datos que la apuesta fue registrada con los valores correctos.


## PRUEBA UNITARIA 2: APUESTA INVÁLIDA (MONTO CERO)

### 1️⃣ Identificación

* **Nombre de la prueba:** Apuesta inválida sin monto  
* **Módulo / Componente:** *Juego “Ruleta”*

---

### 2️⃣ Objetivo

Comprobar que el sistema **rechaza correctamente una apuesta** cuando el usuario no introduce un monto.

---

### 3️⃣ Alcance

Evalúa la validación del campo **monto apostado**, sin involucrar el resultado del juego.

---

### 4️⃣ Diseño de la prueba

#### a) Particiones de equivalencia

| Parámetro | Clases válidas | Clases inválidas |
| ---------- | --------------- | ---------------- |
| Monto apostado | Valor numérico positivo (> 0) | 0 o negativo |
| Tipo de apuesta | Número individual, color o paridad | Opción inexistente / nula |
| Selección de número | Entre 0 y 36 | Menor que 0 o mayor que 36 |

#### b) Valores límite

| Parámetro | Límite inferior | Límite superior |
| ---------- | ---------------- | ---------------- |
| Monto apostado | 1 unidad | Sin límite (depende del saldo del usuario) |
| Número apostado | 0 | 36 |


---

### 5️⃣ Datos de entrada (ejemplo)

| Campo | Valor |
| ------ | ------ |
| Tipo de apuesta | --- |
| Monto apostado | 0 créditos |
| Saldo inicial | 100 créditos |

---

### 6️⃣ Pasos de ejecución

1. Iniciar sesión.  
2. Acceder a la ruleta.  
3. **NO** se selecciona ningun tipo de apuesta.
4. Pulsar **“Girar”**.  

---

### 7️⃣ Resultado esperado

* El sistema **rechaza la apuesta**.  
* Aparece mensaje:  
  **“Pon al menos una apuesta.”**  
* No se descuenta saldo.  
* No se ejecuta la animación de la ruleta.  

---

### 8️⃣ Resultado obtenido

*(Completar tras ejecución)*

* ▢ Correcto — el sistema bloqueó la apuesta y mostró mensaje de error.  
* ▢ Incorrecto — el sistema permitió continuar sin monto.  

---

### 9️⃣ Criterio de éxito

Prueba superada si el sistema impide realizar la apuesta y muestra un mensaje de error claro.

---

### 🔟 Observaciones

* La ruleta no debe hacer la animcaion 
* El saldo debe permanecer intacto.


## PRUEBA UNITARIA 3: APUESTA PERDEDORA EN RULETA

### 1️⃣ Identificación

* **Nombre de la prueba:** Apuesta perdedora en ruleta  
* **Módulo / Componente:** *Juego “Ruleta”*

---

### 2️⃣ Objetivo

Comprobar que el sistema gestiona correctamente una apuesta válida **cuando el resultado es perdedor**, descontando el monto del saldo.

---

### 3️⃣ Alcance

Se valida únicamente el **comportamiento del sistema ante una pérdida**, sin incluir cálculos de premios o acumulaciones.

---

### 4️⃣ Diseño de la prueba

#### a) Particiones de equivalencia

| Parámetro | Clases válidas | Clases inválidas |
| ---------- | --------------- | ---------------- |
| Monto apostado | Valor numérico positivo (> 0) | 0 o negativo |
| Tipo de apuesta | Número individual, color o paridad | Opción inexistente / nula |
| Selección de número | Entre 0 y 36 | Menor que 0 o mayor que 36 |

#### b) Valores límite

| Parámetro | Límite inferior | Límite superior |
| ---------- | ---------------- | ---------------- |
| Monto apostado | 1 unidad | Sin límite (depende del saldo del usuario) |
| Número apostado | 0 | 36 |

---

### 5️⃣ Datos de entrada (ejemplo)

| Campo | Valor |
| ------ | ------ |
| Tipo de apuesta | Número directo |
| Selección | 7 |
| Monto apostado | 5 créditos |
| Saldo inicial | 20 créditos |
| Resultado ruleta | 12 (no coincide) |

---

### 6️⃣ Pasos de ejecución

1. Iniciar sesión con un usuario con saldo disponible (20 créditos).  
2. Acceder al módulo **“Ruleta”**.  
3. Seleccionar **número 7**, junto al monto de **5 créditos**  
4. Pulsar **“Girar”**.  
5. Esperar el resultado del giro.  

---

### 7️⃣ Resultado esperado

* La apuesta se acepta correctamente.  
* Se descuenta **5 créditos** del saldo del usuario.  
* Se muestra el resultado.
* El nuevo saldo mostrado debe ser **15 créditos**.  

---

### 8️⃣ Resultado obtenido

*(Completar tras ejecución)*

* ▢ Correcto — la apuesta fue procesada, el resultado mostrado fue perdedor y el saldo se actualizó.  
* ▢ Incorrecto — el saldo no se actualizó o el resultado no fue coherente.  

---

### 9️⃣ Criterio de éxito

La prueba se considera superada si el sistema **procesa correctamente una apuesta perdedora** y **actualiza el saldo**.

---

### 🔟 Observaciones

* Puede verificarse en la base de datos que el resultado se registró.  
* El saldo debe reflejarse actualizado inmediatamente.


## PRUEBA UNITARIA 4: APUESTA CON SALDO INSUFICIENTE

### 1️⃣ Identificación

* **Nombre de la prueba:** Apuesta rechazada por saldo insuficiente  
* **Módulo / Componente:** *Juego “Ruleta”*

---

### 2️⃣ Objetivo

Comprobar que el sistema **impide realizar una apuesta** cuando el monto introducido **supera el saldo disponible del usuario**.

---

### 3️⃣ Alcance

Se evalúa la validación de **saldo disponible** antes de ejecutar la apuesta, sin llegar a procesar el giro de la ruleta.

---

### 4️⃣ Diseño de la prueba

#### a) Particiones de equivalencia

| Parámetro | Clases válidas | Clases inválidas |
| ---------- | --------------- | ---------------- |
| Monto apostado | Valor numérico positivo (> 0) | 0 o negativo |
| Tipo de apuesta | Número individual, color o paridad | Opción inexistente / nula |
| Selección de número | Entre 0 y 36 | Menor que 0 o mayor que 36 |

#### b) Valores límite

| Parámetro | Límite inferior | Límite superior |
| ---------- | ---------------- | ---------------- |
| Monto apostado | 1 unidad | Sin límite (depende del saldo del usuario) |
| Número apostado | 0 | 36 |

---

### 5️⃣ Datos de entrada (ejemplo)

| Campo | Valor |
| ------ | ------ |
| Tipo de apuesta | Par |
| Monto apostado | 15 créditos |
| Saldo inicial | 10 créditos |

---

### 6️⃣ Pasos de ejecución

1. Iniciar sesión con un usuario que tenga **10 créditos** de saldo.  
2. Entrar a la sección **“Ruleta”**.  
3. Seleccionar tipo de apuesta **Par**, introduciendo un monto de **15 créditos** (mayor que el saldo disponible).  
4. Pulsar **“Girar”**.  

---

### 7️⃣ Resultado esperado

* El sistema **bloquea la acción** y **perimite apostar** unicamente hasta **10 créditos** (saldo disponible).  
* Aparece mensaje:  
  **“Saldo insuficiente.”**  
* No se descuenta (no se perimte el saldo negativo).  

---

### 8️⃣ Resultado obtenido

*(Completar tras ejecución)*

* ▢ Correcto — el sistema bloqueó la apuesta y mostró el mensaje correspondiente.  
* ▢ Incorrecto — el sistema permitió apostar más del saldo disponible.  

---

### 9️⃣ Criterio de éxito

La prueba se considera superada si el sistema **impide apostar más del saldo disponible** y muestra un **mensaje claro y preciso**.

---

### 🔟 Observaciones / Notas

* Puede probarse también con saldo exacto (ejemplo: apostar 10 € con saldo 10 €, que debe ser permitido).  
* El control de saldo debe realizarse **durante** la fase de creacion de apuesta.
