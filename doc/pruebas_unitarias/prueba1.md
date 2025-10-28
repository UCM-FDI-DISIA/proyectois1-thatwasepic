## PRUEBA UNITARIA: REGISTRO DE USUARIO NUEVO

### 1️⃣ Identificación

* **Nombre de la prueba:** Registro exitoso
* **Módulo / componente:** *“Registrarse”*

### 2️⃣ Objetivo

Comprobar que el sistema permite crear correctamente un nuevo usuario con datos válidos a través del formulario de registro de la web.
Debe mostrarse un mensaje o redirección de éxito, y la cuenta debe quedar guardada en la base de datos.

---

### 3️⃣ Alcance

Se prueba **solo la operación de alta de usuario**, sin incluir el login posterior ni la verificación por correo.

---

### 4️⃣ Diseño de la prueba

#### a) Particiones de equivalencia

| Parámetro         | Clases válidas                  | Clases inválidas                  |
| ----------------- | ------------------------------- | --------------------------------- |
| Nombre de usuario | texto alfanumérico sin espacios | vacío                             |
| Email             | formato válido (con “@”)        | formato inválido / vacío          |
| Contraseña        | texto alfanumérico sin espacios | vacía                             |

#### b) Valores límite

| Parámetro  | Valor límite inferior | Valor límite superior                          |
| ---------- | --------------------- | ---------------------------------------------- |
| Contraseña | 4 caracteres          | (sin límite máximo )                           |
| Usuario    | 1 carácter            | (sin límite de caracteres)                     |

---

### 5️⃣ Datos de entrada (ejemplo)

* **Usuario:** `Usuario1`
* **Email:** `Usuario1@example.com`
* **Contraseña:** `1234`

---

### 6️⃣ Pasos de ejecución

1. Acceder a la página principal: `https://logbait.pythonanywhere.com`.
2. Hacer clic en el botón **“Registrarse”**.
3. Introducir en el formulario los datos anteriores.
4. Pulsar **“Crear cuenta” / “Registrarse”**.
5. Esperar la respuesta del sistema.

---

### 7️⃣ Resultado esperado

* El sistema muestra un mensaje **“Registro exitoso. Ahora puedes iniciar sesión.”** y redirige automáticamente a la pantalla de inicio de sesión.
* Se crea un registro nuevo en la base de datos de usuarios con:
  * `username = Usuario1`
  * `email = Usuario1@example.com`
* No aparece ningún mensaje de error.
* El usuario puede iniciar sesión con las mismas credenciales inmediatamente después.

---

### 8️⃣ Resultado obtenido

*(Se completa al ejecutar la prueba)*

* ▢ Correcto — la cuenta se creó y se redirigió a login.
* ▢ Incorrecto — se mostró error / la cuenta no se creó.

---

### 9️⃣ Criterio de éxito

La prueba se considera **superada** si el sistema crea el usuario y muestra el mensaje o redirección de éxito **sin errores de validación**.

---

### 🔟 Observaciones / Notas

* Si el nombre de usuario ya existía, el sistema muestra el mensaje “El nombre de usuario ya existe”.
* Pueden existir varias cuentas con el mismo email.
---

