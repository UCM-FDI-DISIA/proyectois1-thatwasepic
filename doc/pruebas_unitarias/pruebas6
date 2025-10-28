**PRUEBAS UNITARIAS: TRAGAPERRAS**

**PRUEBA 1: VALIDACIÓN DE APUESTA VÁLIDA**

**Identificación**
- **Nombre**: Validación de apuesta válida
- **Módulo**: Juego "Tragaperras"
- **Objetivo**: Verificar que el sistema acepta apuestas dentro del saldo disponible

**Alcance**
Validación de entrada de cantidad sin ejecutar el giro completo

**Diseño de la prueba**
- **Particiones de equivalencia**:
  - Cantidad válida: 1 <= cantidad <= saldo_actual
  - Cantidad inválida: cantidad > saldo_actual, cantidad <= 0
- **Valores límite**:
  - Límite inferior: 1
  - Límite superior: saldo_actual

**Datos de entrada**
```
saldoUsuario = 100
cantidadApuesta = 50
```

**Pasos de ejecución**
1. Establecer saldo de usuario: 100 créditos
2. Ingresar monto: 50 en campo "cantidad"
3. Ejecutar `girarTragaperras()`
4. Verificar validación inicial

**Resultado esperado**
- Validación pasa correctamente
- No se muestra mensaje de error
- Procede con la animación de giro

---

**PRUEBA 2: VALIDACIÓN DE APUESTA CON SALDO INSUFICIENTE**

**Identificación**
- **Nombre**: Validación de apuesta con saldo insuficiente
- **Módulo**: Juego "Tragaperras"
- **Objetivo**: Comprobar que el sistema rechaza apuestas que superan el saldo

**Datos de entrada**
```
saldoUsuario = 100
cantidadApuesta = 150
```

**Pasos de ejecución**
1. Establecer saldo de usuario: 100 créditos
2. Ingresar monto: 150 en campo "cantidad"
3. Ejecutar `girarTragaperras()`
4. Verificar comportamiento del sistema

**Resultado esperado**
- Se muestra alerta: "Fondos insuficientes"
- No se inicia la animación de giro
- Saldo permanece sin cambios
- Botón "GIRAR RODILLOS" permanece habilitado

---

**PRUEBA 3: CÁLCULO DE PREMIOS - COMBINACIÓN GANADORA**

**Identificación**
- **Nombre**: Cálculo correcto de premios para combinación ganadora
- **Módulo**: Lógica de juego - Cálculo de premios
- **Objetivo**: Verificar que las combinaciones ganadoras calculan el premio correcto

**Alcance**
Solo función `calcularPremio()`

**Datos de entrada**
```
resultados = ['7️⃣', '7️⃣', '7️⃣']
apuesta = 10
```

**Pasos de ejecución**
1. Ejecutar `calcularPremio(['7️⃣', '7️⃣', '7️⃣'], 10)`
2. Verificar resultado del cálculo

**Resultado esperado**
- Premio calculado: 10 × 50 = 500
- Retorna valor numérico positivo
- Combinación reconocida en tabla de premios

---

**PRUEBA 4: CÁLCULO DE PREMIOS - DOS SÍMBOLOS IGUALES**

**Identificación**
- **Nombre**: Premio por dos símbolos iguales
- **Módulo**: Lógica de juego - Premios secundarios
- **Objetivo**: Comprobar el premio mínimo por dos símbolos iguales

**Datos de entrada**
```
resultados = ['🍒', '🍒', '🍋']
apuesta = 10
```

**Pasos de ejecución**
1. Ejecutar `calcularPremio(['🍒', '🍒', '🍋'], 10)`
2. Verificar cálculo de premio secundario

**Resultado esperado**
- Premio calculado: 10 × 2 = 20
- Aplica multiplicador 2x para dos símbolos iguales
- No aplica premio de combinación completa

---

**PRUEBA 5: CÁLCULO DE PREMIOS - SIN COMBINACIÓN**

**Identificación**
- **Nombre**: Sin premio por combinación perdedora
- **Módulo**: Lógica de juego - Casos sin premio
- **Objetivo**: Verificar que combinaciones sin símbolos iguales no otorgan premio

**Datos de entrada**
```
resultados = ['🍒', '🍋', '💎']
apuesta = 10
```

**Pasos de ejecución**
1. Ejecutar `calcularPremio(['🍒', '🍋', '💎'], 10)`
2. Verificar retorno de función

**Resultado esperado**
- Premio calculado: 0
- No hay símbolos iguales
- No aplica ningún multiplicador

---

**PRUEBA 6: GENERACIÓN DE RESULTADOS CON PROBABILIDADES**

**Identificación**
- **Nombre**: Distribución correcta de probabilidades
- **Módulo**: Lógica de juego - Generación de símbolos
- **Objetivo**: Comprobar que los símbolos se generan según las probabilidades definidas

**Alcance**
Función `generarResultadoConProbabilidades()`

**Pasos de ejecución**
1. Ejecutar función 1000 veces
2. Contar frecuencia de cada símbolo
3. Calcular distribución porcentual

**Resultado esperado**
- 🍒: ~25% de aparición
- 🍋: ~20% de aparición  
- 🍊: ~15% de aparición
- ⭐: ~15% de aparición
- 💎: ~15% de aparición
- 7️⃣: ~10% de aparición
- Siempre retorna array de 3 elementos

---

**PRUEBA 7: FLUJO COMPLETO - VICTORIA GRANDE**

**Identificación**
- **Nombre**: Flujo completo con premio máximo
- **Módulo**: Juego completo "Tragaperras"
- **Objetivo**: Verificar el flujo completo desde apuesta hasta premio grande

**Datos de entrada**
```
saldoInicial = 200
cantidadApuesta = 10
resultado = ['7️⃣', '7️⃣', '7️⃣']
```

**Pasos de ejecución**
1. Iniciar con saldo: 200
2. Apostar 10 créditos
3. Simular resultado: triple 7
4. Ejecutar flujo completo
5. Verificar resultados finales

**Resultado esperado**
- Se descuenta apuesta: 200 - 10 = 190
- Se calcula premio: 10 × 50 = 500
- Nuevo saldo: 190 + 500 = 690
- Se muestra mensaje: "¡GANADOR! 🎉"
- Se activa animación de confeti
- Se actualiza "ÚLTIMO PREMIO" a $500.00

---

**PRUEBA 8: ESTADOS VISUALES DURANTE EL GIRO**

**Identificación**
- **Nombre**: Estados visuales durante la animación
- **Módulo**: Interfaz de usuario - Animaciones
- **Objetivo**: Verificar los cambios visuales durante la ejecución del giro

**Verificaciones**
- Botón "GIRAR RODILLOS" cambia a "GIRANDO..." y se deshabilita
- Rodillos muestran animación rápida de símbolos
- Balance se actualiza temporalmente restando la apuesta
- Al ganar: activa `win-animation` en contenedor y `win-symbol` en rodillos
- Al perder: muestra mensaje "Sin premio 😞"

---

**PRUEBA 9: COMUNICACIÓN CON BACKEND**

**Identificación**
- **Nombre**: Envío correcto de resultados al servidor
- **Módulo**: API Integration
- **Objetivo**: Verificar que los datos se envían correctamente al endpoint

**Datos de entrada**
```
resultado = "ganada"
cantidad = 10
ganancia = 500
```

**Pasos de ejecución**
1. Ejecutar `enviarResultadoTragaperras("ganada", 500, 10)`
2. Verificar estructura de la petición HTTP
3. Comprobar manejo de respuesta

**Resultado esperado**
- Petición POST a '/api/tragaperras/apostar'
- Headers incluyen 'Content-Type': 'application/json'
- Body contiene: {cantidad: 10, resultado: "ganada", ganancia: 500}
- En respuesta exitosa, actualiza balance en interfaz

---

**PRUEBA 10: MANEJO DE ERRORES DE CONEXIÓN**

**Identificación**
- **Nombre**: Recuperación ante fallos de red
- **Módulo**: Manejo de errores
- **Objetivo**: Verificar que el sistema se recupera correctamente ante fallos de conexión

**Pasos de ejecución**
1. Simular fallo en fetch('/api/tragaperras/apostar')
2. Ejecutar `enviarResultadoTragaperras()`
3. Verificar comportamiento de recuperación

**Resultado esperado**
- Se muestra mensaje: "Error de conexión"
- Se revierte descuento temporal del balance
- Botón "GIRAR RODILLOS" se rehabilita
- Estado `girando` vuelve a false

---

**PRUEBA 11: VALIDACIÓN DE ENTRADA DE CANTIDAD**

**Identificación**
- **Nombre**: Validación robusta de input de apuesta
- **Módulo**: Control de formularios
- **Objetivo**: Comprobar que el input valida correctamente todos los casos

**Casos de prueba**
- Cantidad mayor al saldo: Se ajusta al máximo disponible
- Cantidad menor a 1: Se establece en 1
- Valor decimal: ParseFloat lo maneja correctamente
- Campo vacío: Alert "Ingresa una cantidad válida"
- Valor negativo: No permitido (min="1")

---

**PRUEBA 12: RESETEO DE ESTADO TRAS GIRO**

**Identificación**
- **Nombre**: Restablecimiento correcto del estado
- **Módulo**: Gestión de estado del juego
- **Objetivo**: Comprobar que el estado se restablece correctamente tras cada giro

**Pasos de ejecución**
1. Completar un giro (ganador o perdedor)
2. Verificar estado final del sistema

**Resultado esperado**
- `girando = false`
- Botón "GIRAR RODILLOS" habilitado y con texto original
- Animaciones visuales detenidas
- Balance actualizado correctamente
- Listo para siguiente giro
