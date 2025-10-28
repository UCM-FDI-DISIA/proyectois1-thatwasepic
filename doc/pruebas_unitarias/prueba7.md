# PRUEBA UNITARIA: COINFLIP

## PRUEBA UNITARIA 1: APUESTA EXITOSA EN COINFLIP

### 1️⃣ Identificación

* **Nombre de la prueba:** Apuesta exitosa en Coinflip  
* **Módulo / Componente:** *Juego “Coinflip”*

---

### 2️⃣ Objetivo

Comprobar que el sistema permite realizar correctamente una apuesta válida en Coinflip, descontando el monto apostado del saldo y mostrando el resultado (cara o cruz).

---

### 3️⃣ Alcance

Se evalúa solo la funcionalidad de **realizar una apuesta válida** y la **respuesta del sistema**, sin incluir la acumulación de premios o historial.

---

### 4️⃣ Diseño de la prueba

#### a) Particiones de equivalencia

| Parámetro | Clases válidas | Clases inválidas |
| ---------- | --------------- | ---------------- |
| Monto apostado | Valor numérico positivo (> 0) | 0 o negativo |
| Elección | Cara o Cruz | Opción inexistente / nula |

#### b) Valores límite

| Parámetro | Límite inferior | Límite superior |
| ---------- | ---------------- | ---------------- |
| Monto apostado | 1 unidad | Sin límite (depende del saldo del usuario) |

---

### 5️⃣ Datos de entrada (ejemplo)

| Campo | Valor |
| ------ | ------ |
| Elección | Cara |
| Monto apostado | 10 créditos |
| Saldo inicial | 100 créditos |

---

### 6️⃣ Pasos de ejecución

1. Iniciar sesión con un usuario válido.  
2. Acceder al módulo **“Coinflip”**.  
3. Seleccionar **Cara** como elección.  
4. Introducir el monto **10 créditos**.  
5. Pulsar **“Girar” / “Apostar”**.  
6. Esperar el resultado de la jugada.

---

### 7️⃣ Resultado esperado

* La apuesta se acepta correctamente.  
* Se descuenta **10 créditos** del saldo.  
* Se muestra el resultado de la moneda (Cara o Cruz).  
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

### 🔟 Observaciones

* El saldo del usuario debe actualizarse inmediatamente.  
* Se puede verificar en la base de datos que la apuesta fue registrada correctamente.

---


## PRUEBA UNITARIA 2: APUESTA INVÁLIDA EN COINFLIP

### 1️⃣ Identificación

* **Nombre de la prueba:** Apuesta inválida (monto cero o vacío)  
* **Módulo / Componente:** *Juego “Coinflip”*

---

### 2️⃣ Objetivo

Comprobar que el sistema **rechaza correctamente una apuesta** cuando el usuario no introduce un monto o introduce un valor igual a cero.

---

### 3️⃣ Alcance

Evalúa la validación del campo **monto apostado**, sin involucrar el resultado de la moneda.

---

### 4️⃣ Diseño de la prueba

#### a) Particiones de equivalencia

| Parámetro | Clases válidas | Clases inválidas |
| ---------- | --------------- | ---------------- |
| Monto apostado | Valor numérico positivo (> 0) | 0 o negativo |
| Elección | Cara o Cruz | Opción inexistente / nula |

#### b) Valores límite

| Parámetro | Límite inferior | Límite superior |
| ---------- | ---------------- | ---------------- |
| Monto apostado | 1 unidad | Sin límite (depende del saldo del usuario) |

---

### 5️⃣ Datos de entrada (ejemplo)

| Campo | Valor |
| ------ | ------ |
| Elección | Cruz |
| Monto apostado | 0 créditos |
| Saldo inicial | 50 créditos |

---

### 6️⃣ Pasos de ejecución

1. Iniciar sesión con un usuario válido.  
2. Acceder al módulo **“Coinflip”**.  
3. Seleccionar **Cruz** como elección.  
4. Dejar el campo “Monto” vacío o introducir **0**.  
5. Pulsar **“Girar” / “Apostar”**.  

---

### 7️⃣ Resultado esperado

* El sistema **rechaza la apuesta**.  
* Aparece mensaje:  
  **“Debes ingresar un monto válido para apostar.”**  
* No se descuenta saldo.  

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

* Puede probarse también con campo vacío o valores no numéricos (“abc”).  
* El saldo debe permanecer intacto.

---


## PRUEBA UNITARIA 3: APUESTA PERDEDORA EN COINFLIP

### 1️⃣ Identificación

* **Nombre de la prueba:** Apuesta perdedora en Coinflip  
* **Módulo / Componente:** *Juego “Coinflip”*

---

### 2️⃣ Objetivo

Comprobar que el sistema gestiona correctamente una apuesta válida **cuando el resultado es perdedor**, descontando el monto del saldo y mostrando el mensaje correspondiente.

---

### 3️⃣ Alcance

Se valida únicamente el **comportamiento del sistema ante una pérdida**, sin incluir la acumulación de premios.

---

### 4️⃣ Diseño de la prueba

#### a) Particiones de equivalencia

| Parámetro | Clases válidas | Clases inválidas |
| ---------- | --------------- | ---------------- |
| Monto apostado | Valor numérico positivo (> 0) y ≤ saldo | 0 o mayor que saldo / negativo |
| Elección | Cara o Cruz | Opción inexistente / nula |

#### b) Valores límite

| Parámetro | Límite inferior | Límite superior |
| ---------- | ---------------- | ---------------- |
| Monto apostado | 1 unidad | Igual al saldo |

---

### 5️⃣ Datos de entrada (ejemplo)

| Campo | Valor |
| ------ | ------ |
| Elección | Cara |
| Monto apostado | 20 créditos |
| Saldo inicial | 50 créditos |
| Resultado moneda | Cruz |

---

### 6️⃣ Pasos de ejecución

1. Iniciar sesión con un usuario con saldo disponible (50 créditos).  
2. Acceder al módulo **“Coinflip”**.  
3. Seleccionar **Cara** como elección.  
4. Introducir el monto **20 créditos**.  
5. Pulsar **“Girar” / “Apostar”**.  
6. Esperar el resultado de la moneda.  

---

### 7️⃣ Resultado esperado

* La apuesta se acepta correctamente.  
* Se descuenta **20 créditos** del saldo del usuario.  
* Se muestra el resultado de la moneda (**Cruz**).  
* Aparece mensaje:  
  **“Has perdido. Mejor suerte la próxima vez.”**  
* El nuevo saldo mostrado debe ser **30 créditos**.

---

### 8️⃣ Resultado obtenido

*(Completar tras ejecución)*

* ▢ Correcto — la apuesta fue procesada, el resultado mostrado fue perdedor y el saldo se actualizó.  
* ▢ Incorrecto — el saldo no se actualizó o el resultado no fue coherente.

---

### 9️⃣ Criterio de éxito

La prueba se considera superada si el sistema **procesa correctamente una apuesta perdedora**, **actualiza el saldo** y **muestra el mensaje correspondiente**.

---

### 🔟 Observaciones

* Puede verificarse en la base de datos que el resultado se registró.  
* El saldo debe reflejarse actualizado inmediatamente.

---


## PRUEBA UNITARIA 4: APUESTA CON SALDO INSUFICIENTE EN COINFLIP

### 1️⃣ Identificación

* **Nombre de la prueba:** Apuesta rechazada por saldo insuficiente  
* **Módulo / Componente:** *Juego “Coinflip”*

---

### 2️⃣ Objetivo

Comprobar que el sistema **impide realizar una apuesta** cuando el monto introducido **supera el saldo disponible del usuario**.

---

### 3️⃣ Alcance

Se evalúa la validación de **saldo disponible** antes de ejecutar la apuesta, sin procesar el giro de la moneda.

---

### 4️⃣ Diseño de la prueba

#### a) Particiones de equivalencia

| Parámetro | Clases válidas | Clases inválidas |
| ---------- | --------------- | ---------------- |
| Monto apostado | Valor numérico positivo (> 0) y ≤ saldo | > saldo disponible / negativo / vacío |
| Elección | Cara o Cruz | Opción inexistente / nula |

#### b) Valores límite

| Parámetro | Límite inferior | Límite superior |
| ---------- | ---------------- | ---------------- |
| Monto apostado | 1 unidad | Igual al saldo disponible |

---

### 5️⃣ Datos de entrada (ejemplo)

| Campo | Valor |
| ------ | ------ |
| Elección | Cruz |
| Monto apostado | 15 créditos |
| Saldo inicial | 10 créditos |

---

### 6️⃣ Pasos de ejecución

1. Iniciar sesión con un usuario con saldo **10 créditos**.  
2. Acceder al módulo **“Coinflip”**.  
3. Seleccionar **Cruz** como elección.  
4. Introducir un monto **15 créditos** (mayor que el saldo disponible).  
5. Pulsar **“Girar” / “Apostar”**.  

---

### 7️⃣ Resultado esperado

* El sistema **bloquea la acción** y **no permite enviar la apuesta**.  
* Aparece mensaje:  
  **“Saldo insuficiente para realizar esta apuesta.”**  
* No se descuenta ningún crédito.  

---

### 8️⃣ Resultado obtenido

*(Completar tras ejecución)*

* ▢ Correcto — el sistema bloqueó la apuesta y mostró el mensaje correspondiente.  
* ▢ Incorrecto — el sistema permitió apostar más del saldo disponible.

---

### 9️⃣ Criterio de éxito

La prueba se considera superada si el sistema **impide apostar más del saldo disponible** y muestra un **mensaje claro y preciso**.

---

### 🔟 Observaciones

* Puede probarse también con saldo exacto (ejemplo: apostar 10 créditos con saldo 10, que debe ser permitido).  
* El control de saldo debe realizarse **antes** de procesar el giro.
