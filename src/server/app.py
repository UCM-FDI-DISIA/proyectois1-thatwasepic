from flask import Flask, render_template
from flask_flatpages import FlatPages
from flask_login import LoginManager
from flask_socketio import SocketIO
from models import db, User
from endpoints import register_blueprints
from utils.flatpage_helpers import markdown_renderer, get_headings
import os

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

# CONFIGURACIÓN MEJORADA
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-secreta-casino-educativo-2024')
app.config["FLATPAGES_ROOT"] = "../flatpages"
app.config["FLATPAGES_EXTENSION"] = ".md"
app.config['FLATPAGES_HTML_RENDERER'] = markdown_renderer

# CONFIGURACIÓN DE BASE DE DATOS MEJORADA PARA PSYCOPG3
if os.environ.get('DATABASE_URL'):
    database_url = os.environ.get('DATABASE_URL')
    # Asegurar que use el formato postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    else:
        # Si ya es postgresql://, cambiar a postgresql+psycopg://
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print("🚀 Usando PostgreSQL con psycopg3 (Render)")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///casino.db'
    print("💻 Usando SQLite (Local)")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

# Registrar el helper en el entorno Jinja
app.jinja_env.globals["get_headings"] = get_headings

# Inicializar extensiones
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# SOCKETIO SIMPLIFICADO
is_production = os.environ.get('DATABASE_URL') is not None

socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode=None,  # Dejar que SocketIO decida automáticamente
                   logger=True,
                   engineio_logger=is_production)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Registrar todos los blueprints del paquete endpoints
register_blueprints(app)

# Importar y registrar handlers de SocketIO
try:
    from socketio_handlers import register_socketio_handlers
    register_socketio_handlers(socketio)
    print("✅ Handlers de SocketIO registrados")
except ImportError as e:
    print(f"⚠️  No se pudieron cargar los handlers de SocketIO: {e}")

# Registrar handlers específicos de juegos multijugador
try:
    from endpoints.protected.api.juegos.multiplayer.caballos.socket_handlers import register_caballos_handlers
    register_caballos_handlers(socketio, app)
    print("✅ Handlers de Caballos multijugador registrados")
except ImportError as e:
    print(f"⚠️  No se pudieron cargar los handlers de Caballos: {e}")

# Registrar flatpages
pages = FlatPages(app)

print("📄 FlatPages encontrados:")
for p in pages:
    print(" -", p.path)

@app.route('/<path:path>/')
def flatpage(path):
    page = pages.get_or_404(path)
    template = page.meta.get('template', 'pages/casino/flatpage.html')
    return render_template(template, page=page)

# Inicializar DB
with app.app_context():
    try:
        db.create_all()
        print("✅ Base de datos inicializada")
        
        # Crear usuario demo solo en local
        if not os.environ.get('DATABASE_URL') and not User.query.filter_by(username='demo').first():
            demo_user = User(username='demo', email='demo@casino.com')
            demo_user.set_password('demo123')
            db.session.add(demo_user)
            db.session.commit()
            print("✅ Usuario demo creado (usuario: demo, contraseña: demo123)")
            
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    socketio.run(
        app, 
        port=port, 
        debug=not is_production,
        allow_unsafe_werkzeug=True
    )