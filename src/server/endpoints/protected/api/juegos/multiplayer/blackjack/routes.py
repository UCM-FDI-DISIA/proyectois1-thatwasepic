from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import SalaMultijugador
from .socket_handlers import register_blackjack_handlers

bp = Blueprint("api_multijugador_blackjack", __name__)

@bp.record_once
def on_register(state):
    socketio = state.app.extensions.get("socketio")
    app = state.app
    if socketio:
        register_blackjack_handlers(socketio, app)

@bp.route("/blackjack/sala/<int:sala_id>")
@login_required
def vista_sala_blackjack(sala_id):
    sala = SalaMultijugador.query.get_or_404(sala_id)
    if sala.juego != "blackjack":
        abort(404)
    return render_template("pages/casino/juegos/multiplayer/blackjack.html",
                           sala=sala, user=current_user)

