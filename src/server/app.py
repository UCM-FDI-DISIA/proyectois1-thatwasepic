from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from models import db, User
from endpoints import register_blueprints

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

# Configuración básica
app.config['SECRET_KEY'] = 'clave-secreta-casino-educativo-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///casino.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
socketio = SocketIO(app, cors_allowed_origins="*")

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

# Inicializar DB
with app.app_context():
    try:
        db.create_all()
        print("✅ Base de datos inicializada")
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")

if __name__ == '__main__':
    socketio.run(app, debug=True)