from flask import Flask, render_template
from flask_flatpages import FlatPages
from flask_login import LoginManager
from flask_socketio import SocketIO
from models import db, User
from endpoints import register_blueprints
from utils.flatpage_helpers import markdown_renderer, get_headings

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

# Configuración básica
app.config['SECRET_KEY'] = 'clave-secreta-casino-educativo-2024'
app.config["FLATPAGES_ROOT"] = "../flatpages"
app.config["FLATPAGES_EXTENSION"] = ".md"
app.config['FLATPAGES_HTML_RENDERER'] = markdown_renderer
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///casino.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Registrar el helper en el entorno Jinja
app.jinja_env.globals["get_headings"] = get_headings

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

# Registrar flatpages
pages = FlatPages(app)

print("📄 FlatPages encontrados:")
for p in pages:
    print(" -", p.path)

@app.route('/<path:path>/')
def flatpage(path):
    page = pages.get_or_404(path)
    template = page.meta.get('template', 'flatpage/flatpage.html')
    return render_template(template, page=page)

# Inicializar DB
with app.app_context():
    try:
        db.create_all()
        print("✅ Base de datos inicializada")
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")

if __name__ == '__main__':
    socketio.run(app, debug=True)