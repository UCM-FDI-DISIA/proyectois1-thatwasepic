# PRUEBAS UNITARIAS: CARRERA DE CABALLOS

## PRUEBA 1: SELECCIÓN VÁLIDA DE CABALLO

### Identificación
- **Nombre**: Selección válida de caballo
- **Módulo**: Juego "Carrera de Caballos"

### Objetivo
Comprobar que el sistema permite seleccionar correctamente un caballo para apostar y actualiza la interfaz visualmente.

### Alcance
Se evalúa solo la funcionalidad de selección de caballo, sin incluir la ejecución de la carrera.

### Diseño de la prueba
**Particiones de equivalencia:**
- Parámetro: ID Caballo
  - Clases válidas: 1, 2, 3, 4
  - Clases inválidas: null, undefined, 0, 5, "texto"

**Valores límite:**
- Límite inferior: 1
- Límite superior: 4

### Datos de entrada
caballoId = 2 // Trueno

### Pasos de ejecución
1. Acceder al módulo "Carrera de Caballos"
2. Ejecutar `seleccionarCaballo(2)`
3. Verificar estado de la variable `caballoSeleccionado`
4. Comprobar cambios visuales en los botones

### Resultado esperado
- `caballoSeleccionado = 2`
- Botón del caballo 2 cambia de 
- Se muestra información de apuesta: "Apuestas por: Trueno (Multiplicador: 2.0x)"

---

## PRUEBA 2: VALIDACIÓN DE APUESTA CON SALDO INSUFICIENTE

### Identificación
- **Nombre**: Validación de apuesta con saldo insuficiente
- **Módulo**: Juego "Carrera de Caballos"

### Objetivo
Verificar que el sistema rechaza apuestas cuando el monto supera el saldo disponible.

### Alcance
Solo validación de fondos, sin procesar apuesta.

### Diseño de la prueba
**Particiones de equivalencia:**
- Parámetro: Cantidad
  - Clases válidas: 1 <= cantidad <= saldo_actual
  - Clases inválidas: cantidad > saldo_actual, cantidad <= 0

### Datos de entrada
saldoInicial = 100
cantidadApuesta = 150
caballoSeleccionado = 1

### Pasos de ejecución
1. Establecer saldo de usuario: 100 créditos
2. Seleccionar caballo 1
3. Ingresar monto: 150
4. Ejecutar `iniciarCarrera()`
5. Verificar comportamiento del sistema

### Resultado esperado
- Se muestra alerta: "Fondos insuficientes"
- No se inicia la carrera (`carreraEnCurso = false`)
- Saldo permanece sin cambios

---

## PRUEBA 3: CÁLCULO DE PROBABILIDADES

### Identificación
- **Nombre**: Cálculo correcto de probabilidades
- **Módulo**: Lógica de juego - Probabilidades

### Objetivo
Comprobar que las probabilidades se calculan correctamente basándose en velocidad y resistencia.

### Alcance
Solo función `calcularProbabilidades()`

### Datos de entrada
// Configuración actual de caballos
caballos = {
  1: { velocidad: 0.85, resistencia: 0.70 },
  2: { velocidad: 0.75, resistencia: 0.80 },
  3: { velocidad: 0.65, resistencia: 0.85 },
  4: { velocidad: 0.45, resistencia: 0.95 }
}

### Pasos de ejecución
1. Ejecutar `calcularProbabilidades()`
2. Verificar que la suma de todas las probabilidades = 1
3. Comprobar que Relámpago tiene mayor probabilidad que Azabache

### Resultado esperado
- Suma de probabilidades = 1.0
- Probabilidad(Relámpago) > Probabilidad(Azabache)
- Valores dentro de rango [0,1]

---

## PRUEBA 4: EJECUCIÓN COMPLETA DE CARRERA EXITOSA

### Identificación
- **Nombre**: Carrera completa con apuesta ganadora
- **Módulo**: Juego "Carrera de Caballos" completo

### Objetivo
Verificar el flujo completo desde la apuesta hasta el resultado ganador.

### Datos de entrada

saldoInicial = 100
cantidadApuesta = 50
caballoSeleccionado = 1 // Relámpago
caballoGanador = 1 // Relámpago gana


### Pasos de ejecución
1. Iniciar sesión con usuario válido
2. Acceder a "Carrera de Caballos"
3. Seleccionar Relámpago
4. Apostar 50 créditos
5. Ejecutar carrera
6. Simular victoria de Relámpago
7. Verificar resultados

### Resultado esperado
- Se descuenta apuesta del saldo: 100 - 50 = 50
- Se calcula ganancia: 50 × 1.5 = 75
- Nuevo saldo: 50 + 75 = 125
- Se muestra mensaje: "¡GANASTE! 🎉"
- Se actualiza balance en interfaz

---

## PRUEBA 5: RESETEO DE CARRERA

### Identificación
- **Nombre**: Reseteo correcto del estado del juego
- **Módulo**: Funcionalidad de reinicio

### Objetivo
Comprobar que la función `reiniciarCarrera()` restablece correctamente el estado del juego.

### Pasos de ejecución
1. Configurar estado con caballo seleccionado y carrera en curso
2. Ejecutar `reiniciarCarrera()`
3. Verificar estado resultante

### Resultado esperado
- `caballoSeleccionado = null`
- `carreraEnCurso = false`
- Todos los caballos en posición inicial (left: 0px)
- Botones de selección en estado "outline"
- Información de apuesta limpiada
- Botón "Iniciar Carrera" habilitado

---

## PRUEBA 6: COMUNICACIÓN CON BACKEND

### Identificación
- **Nombre**: Envío correcto de resultados al servidor
- **Módulo**: API Integration

### Objetivo
Verificar que los datos se envían correctamente al endpoint del servidor.

### Datos de entrada
resultado = "ganada"
cantidad = 50
ganancia = 75
caballoApostado = 1
caballoGanador = 1

### Pasos de ejecución
1. Ejecutar `enviarResultadoCaballos()` con datos de prueba
2. Verificar estructura de la petición HTTP
3. Comprobar manejo de respuesta exitosa

### Resultado esperado
- Petición POST a '/api/caballos/apostar'
- Headers incluyen 'Content-Type' y CSRF Token
- Body contiene todos los datos necesarios
- En respuesta exitosa, actualiza balance en interfaz

---

## PRUEBA 7: VALIDACIÓN DE ENTRADA DE MONTO

### Identificación
- **Nombre**: Validación de entrada de cantidad
- **Módulo**: Control de formularios

### Objetivo
Comprobar que el input de cantidad valida correctamente los valores.

### Casos de prueba:
1. **Cantidad mayor al saldo**: Debe ajustarse al saldo máximo
2. **Cantidad negativa**: No permitida (min="1")
3. **Valor decimal**: Permitido (step="1" pero parseFloat lo maneja)
4. **Campo vacío**: Alert "Ingresa una cantidad válida"

---

## PRUEBA 8: ANIMACIÓN Y ESTADOS VISUALES

### Identificación
- **Nombre**: Estados visuales durante la carrera
- **Módulo**: Interfaz de usuario

### Objetivo
Verificar los cambios visuales durante la ejecución de la carrera.

### Verificaciones:
- Botón "Iniciar Carrera" se deshabilita durante carrera
- Caballos se mueven progresivamente hacia la meta
- Caballo ganador tiene animación "pulse"
- Posiciones se reinician correctamente

---
