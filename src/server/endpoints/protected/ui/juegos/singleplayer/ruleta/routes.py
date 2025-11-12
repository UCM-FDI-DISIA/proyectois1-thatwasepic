from flask import request, jsonify, Blueprint, render_template
from flask_login import login_required, current_user
from models import db, Apuesta

# Blueprint principal para las rutas de la ruleta
bp = Blueprint('ruleta', __name__)

@bp.route('/ruleta')
@login_required
def home():
    """Página principal de la ruleta"""
    return render_template('pages/casino/juegos/singleplayer/ruleta.html')
