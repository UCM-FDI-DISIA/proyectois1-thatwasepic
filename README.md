<p align="center">
  <img src="assets/logo/logo.png" style="width: 40%; max-width: 350px;" width="350px">
</p>

<h1 align="center">
  <img alt="LogBait" src="assets/logo/logo.svg" style="height: 1.1em; vertical-align: bottom;" height="20px">
</h1>

<p align="center">
  Plataforma de Apuestas Online
</p>

<p align="center">
  <a href="https://github.com/UCM-FDI-DISIA/proyectois1-thatwasepic/wiki">Ver Wiki</a>
  ·
  <a href="https://github.com/UCM-FDI-DISIA/proyectois1-thatwasepic/issues/new">Reportar bug</a>
</p>

<p align="center">
  <em>Instancia principal:</em>
  <br>
  <a href="https://logbait.onrender.com/"><b>logbait.onrender.com</b></a>
</p>


**LogBait** es una plataforma web de apuestas desarrollada como proyecto académico.

Su objetivo es ofrecer una experiencia sencilla, segura y responsable para los usuarios interesados en realizar apuestas en línea de manera simulada.

---

## 📜 Descripción general

LogBait permite a los usuarios registrarse, gestionar su saldo virtual, realizar apuestas en distintos juegos y consultar los resultados obtenidos.

Actualmente se encuentra en fase **beta**, pues ya incorpora la funcionalidad del Producto Mínimo Viable (cuyo propósito es ofrecer una versión funcional que cubra las características esenciales de una casa de apuestas online) además de varias características adicionales.

Según vayamos avanzando en el proyecto, seguiremos implementando historias de usuario que aportarán versatilidad y comodidad al usuario. Las funcionalidades concretas de estas historias se pueden observar en el apartado de **Próximos pasos**.

Se puede encontrar información más detallada sobre el proyecto y su gestión en la [Wiki del repositorio](https://github.com/UCM-FDI-DISIA/proyectois1-thatwasepic/wiki).

> [!WARNING]
> Este proyecto tiene **fines exclusivamente educativos y académicos**. No se maneja dinero real ni se promueve el juego con apuestas monetarias: todas las operaciones y apuestas son completamente ficticias, y el contenido está destinado únicamente a la **evaluación de conocimientos técnicos y metodológicos**.

---

## 📆 Metodología de desarrollo

El proyecto se ha desarrollado aplicando **metodologías ágiles**, con iteraciones cortas y una planificación basada en **historias de usuario**, priorizando la entrega temprana de valor

El desarrollo de LogBait ocurre en Sprints que tienen como objetivo la implementación de historias de usuario, de acuerdo con un orden de prioridad.

---

## ⭐ Funcionalidades del LogBait

### 👤 Gestión de usuarios
- Registro e inicio de sesión seguros.
- **Perfil editable** con información básica del usuario.
- **Panel de administración** accesible por los administradores de la instancia[^1].

[^1]: Los nombres de usuario `admin`, `administrador` y `logbait` están reservados para administradores. Estos usuarios no existen por defecto: es necesario registrarse con uno de los nombres mencionados para hacer uso de tal usuario. **Se recomienda registrar los tres usuarios** con una contraseña robusta antes de hacer pública una instancia de LogBait, para evitar accesos en modo administrador no autorizados.

### 💰 Gestión de saldo
- Depósito y retirada de **saldo virtual**.  
- **Límite de depósito configurable** por el usuario, con avisos sobre la cantidad depositable en cada ingreso. 
- Visualización clara y sencilla del **saldo** disponible.

### 🎲 Apuestas
- Interfaz sencilla para realizar apuestas en varias **modalidades de juego**: un solo jugador, o multijugador.
- Multitud de **juegos diferentes** disponibles: blackjack, ruleta, póker, coinflip, carrera de caballos y quiniela.
- Ajuste automático del **saldo** una vez obtenido el resultado de la apuesta.  

### 📊 Resultados e historial
- Visualización de **resultados recientes** en cada juego y modalidad.
- **Historial completo** de depósitos y resultados de apuestas (ganancias y/o pérdidas).
- Sistema de **estadísticas** completo para todos los juegos.

---

## 🧰 Tecnologías utilizadas

LogBait se ha desarrollado como **aplicación web**, haciendo uso de las siguientes tecnologías:

- Para el *backend* o servidor: **Python** con **Flask y SQLAlchemy**
- Para el *frontend*: **HTML, CSS y JavaScript**, utilizando **Bootstrap** como *toolkit* de interfaz de usuario.

---

## ⚙️ Ejecución local

Es imprescindible, antes de comenzar, tener instalado [**Python**](https://www.python.org/downloads/) (versión **3.08 o superior**) y disponer de la copia local completa del código de LogBait (fundamentalmente la carpeta `src`) que se incluía junto a este archivo. Se puede obtener una nueva copia o una versión más reciente del código fuente de LogBait y de este archivo `README.md` en cualquier momento, clonando el repositorio:

``` bash
git clone https://github.com/UCM-FDI-DISIA/proyectois1-thatwasepic.git
```

### Ejecución del servidor local

Vamos a diferenciar, dentro de todos los sistemas operativos existentes, tres de los más utilizados actualmente, como son **Linux**, **macOS** y **Windows**.

#### Linux y macOS

Comenzaremos abriendo una **terminal** (en macOS la aplicación `Terminal.app`, y en Linux la terminal propia del entorno de escritorio que se use, como puede ser GNOME Terminal, Konsole, xterm...) en la carpeta raíz del repositorio local. Para ello, basta con introducir en la misma la ruta en la que se encuentra este archivo:

``` bash
cd $HOME/ruta/a/copia/local/del/repositorio
```

##### Método 1: usar script de ejecución

Junto con el código fuente de LogBait, se incluye un script Bash `run_server.sh` que automatiza la creación del entorno virtual de Python, la instalación de las dependencias en el mismo y la ejecución del servidor local.

Para utilizarlo, en la terminal abierta, basta con navegar a la carpeta del servidor:

``` bash
cd src/server
```

para después ejecutar el script (otorgándole permisos de ejecución antes con `chmod +x run_server.sh`, en caso de que no los tuviese ya):

``` bash
./run_server.sh
```

##### Método 2: ejecución manual

Para ejecutar el servidor manualmente sin hacer uso del script proporcionado, se seguirán los siguientes pasos:

1.  Crear y activar el **entorno virtual**:

    ``` bash
    python 3 -m venv venv
    source venv/bin/activate
    ```

2.  Instalar **dependencias** necesarias para su funcionamiento:

    ``` bash
    pip3 install -r requirements.txt
    ```

3.  Inicializar el servidor local:

    ``` bash
    python3 app.py
    ```

Ahora veamos las pequeñas diferencias en el código al hacerlo en Windows, aunque la estructura de pasos es la misma.

#### Windows

Comenzaremos abriendo una **terminal** en la carpeta raíz del repositorio local, es decir, en el directorio donde se encuentra este archivo. Esto se puede hacer de dos formas:

-   *Método 1:* abrir la carpeta raíz del repositorio en el Explorador de archivos, hacer clic derecho en un espacio en blanco de la carpeta manteniendo pulsada la tecla <kbd>Shift</kbd>, y hacer clic en "*Abrir ventana de PowerShell aquí*".

-   *Método 2:* abrir la aplicación de terminal (tanto Windows Terminal como Símbolo del sistema (CMD) o Powershell son válidad) desde el Menú Inicio, y navegar a la carpeta raíz del repositorio local con el comando:

    ``` cmd
    cd C:\ruta\a\copia\local\del\repositorio
    ```

##### Método 1: usar script de ejecución

Junto con el código fuente de LogBait, se incluye un script PowerShell `run_server.ps1` que automatiza la creación del entorno virtual de Python, la instalación de las dependencias en el mismo y la ejecución del servidor local.

Para utilizarlo, en la terminal abierta, basta con navegar a la carpeta del servidor:

``` bash
cd src\server
```

para después ejecutar el script:

``` bash
powershell -File "run_server.ps1"
```

##### Método 2: ejecución manual

Para ejecutar el servidor manualmente sin hacer uso del script proporcionado, se seguirán los siguientes pasos:

1.  Crear y activar el **entorno virtual**:

    ``` cmd
    python -m venv venv
    .\venv\Scripts\activate
    ```

2.  Instalar **dependencias** necesarias para su funcionamiento:

    ``` cmd
    pip install -r requirements.txt
    ```

3.  Inicializar la base de datos:

    ``` cmd
    python app.py
    ```

### Apertura de la instancia local

Tras realizar lo anterior, la instancia local de LogBait estará en ejecución. Todos los datos relacionados con dicha instancia (por ahora, solamente la base de datos `casino.db`) se almacenan en el directorio `src/server/instance`.
Para utilizarla, basta con **abrir el navegador web en la dirección http://127.0.0.1:5000**.

### Apagado del servidor local

Para finalizar la ejecución de la instancia local, en la terminal abierta, basta con presionar las teclas <kbd>Ctrl</kbd> + <kbd>C</kbd> y, en caso de que se haya ejecutado el servidor de forma manual (sin el script `run_server.sh` o `run_server.ps1`), introducir el comando:

``` bash
deactivate
```

para salir del entorno virtual Python.

---

## 💡 Próximos pasos

Las futuras iteraciones del proyecto incluirán:
- Sistema de recompensas y promociones con logros.  
- Mejora del sistema de chat (emojis, reacciones, mutes).  
- Estadísticas avanzadas de rendimiento y actividad con gráficos.  
- Soporte para múltiples servidores con sincronización Redis (escalabilidad).  
- Mejoras de accesibilidad y experiencia de usuario en dispositivos móviles.  
- Sistema de torneos y ligas entre jugadores.

---

## 👥 Créditos

Este proyecto está desarrollado por un equipo de 7 personas, compuesto por las siguientes:

<a href="https://github.com/UCM-FDI-DISIA/proyectois1-thatwasepic/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=UCM-FDI-DISIA/proyectois1-thatwasepic" height="50px"/>
</a>
