from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import SalaMultijugador, UsuarioSala
from .socket_handlers import register_caballos_handlers

bp = Blueprint('api_multijugador_caballos', __name__)

@bp.record_once
def on_register(state):
    socketio = state.app.extensions.get("socketio")
    app = state.app
    if socketio:
        register_caballos_handlers(socketio, app)
        print("✅ Handlers de Caballos registrados")

@bp.route('/caballos/sala/<int:sala_id>')
@login_required
def sala_caballos(sala_id):
    """Página de sala para una partida multijugador de caballos"""
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    # Verificar que el usuario está en la sala
    usuario_en_sala = UsuarioSala.query.filter_by(usuario_id=current_user.id, sala_id=sala_id).first()
    if not usuario_en_sala:
        abort(403)
    
    if sala.juego != "caballos":
        abort(404)
    
    return render_template("pages/casino/juegos/multiplayer/caballos.html",
                           sala=sala, user=current_user)
