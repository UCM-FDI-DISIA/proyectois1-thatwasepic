from flask import Blueprint, render_template

# Definimos el Blueprint
bp = Blueprint('index', __name__)

# Ruta principal del sitio
@bp.route('/')
def home():
    return render_template('index.html')
