from flask import Blueprint, render_template, abort, redirect, url_for
from flask_login import login_required, current_user
from models import SalaMultijugador, UsuarioSala
from .socket_handlers import register_blackjack_handlers

bp = Blueprint("api_multijugador_blackjack", __name__)

@bp.record_once
def on_register(state):
    socketio = state.app.extensions.get("socketio")
    app = state.app
    if socketio:
        register_blackjack_handlers(socketio, app)

@bp.route("/api/multijugador/blackjack/sala/<int:sala_id>")
@login_required
def vista_sala_blackjack(sala_id):
    """Página principal del Blackjack multijugador"""
    sala = SalaMultijugador.query.get_or_404(sala_id)

    # Verificar que el usuario está en la sala
    usuario_en_sala = UsuarioSala.query.filter_by(usuario_id=current_user.id,sala_id=sala_id).first()

    if not usuario_en_sala:
        return redirect(url_for('salas_espera.lobby'))

    if sala.juego != "blackjack":
        abort(404)

    if sala.estado != "jugando":
        return redirect(url_for('salas_espera.lobby'))

    return render_template(
        "pages/casino/juegos/multiplayer/blackjack.html",sala=sala,user=current_user,multijugador=True,realtime_required=True,)

