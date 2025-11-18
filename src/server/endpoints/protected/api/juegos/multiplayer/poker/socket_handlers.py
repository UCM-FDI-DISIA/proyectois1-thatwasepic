# server/endpoints/protected/api/juegos/multiplayer/poker/socket_handlers.py

from datetime import datetime

from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room, emit

from models import SalaMultijugador, UsuarioSala

CHAT_HISTORY_LIMIT = 80


def register_poker_handlers(socketio, app):
    """
    Registra eventos Socket.IO específicos de póker (chat + señales ligeras).
    Se invoca una única vez desde el blueprint mediante @bp.record_once.
    """
    chat_histories: dict[int, list[dict]] = {}

    def _room_name(sala_id: int) -> str:
        return f"poker_{sala_id}"

    def _usuario_pertenece(sala_id: int, user_id: int) -> bool:
        return UsuarioSala.query.filter_by(
            sala_id=sala_id,
            usuario_id=user_id
        ).first() is not None

    @socketio.on('poker_join')
    def poker_join(data):
        if not current_user.is_authenticated:
            return
        sala_id = data.get('sala_id')
        try:
            sala_id = int(sala_id)
        except (TypeError, ValueError):
            return

        sala = SalaMultijugador.query.get(sala_id)
        if not sala or sala.juego != 'poker':
            emit('poker_error', {'error': 'Sala no encontrada'}, room=request.sid)
            return

        if not _usuario_pertenece(sala_id, current_user.id):
            emit('poker_error', {'error': 'No perteneces a esta sala'}, room=request.sid)
            return

        join_room(_room_name(sala_id))
        history = chat_histories.get(sala_id, [])
        if history:
            emit('poker_chat_history', history, room=request.sid)

    @socketio.on('poker_leave')
    def poker_leave(data):
        if not current_user.is_authenticated:
            return
        sala_id = data.get('sala_id')
        try:
            sala_id = int(sala_id)
        except (TypeError, ValueError):
            return
        leave_room(_room_name(sala_id))

    @socketio.on('poker_chat_message')
    def poker_chat_message(data):
        if not current_user.is_authenticated:
            return

        sala_id = data.get('sala_id')
        message = (data.get('message') or '').strip()
        if not message:
            return

        try:
            sala_id = int(sala_id)
        except (TypeError, ValueError):
            return

        if not _usuario_pertenece(sala_id, current_user.id):
            emit('poker_error', {'error': 'No perteneces a esta sala'}, room=request.sid)
            return

        payload = {
            'user_id': current_user.id,
            'username': current_user.username,
            'message': message[:400],
            'timestamp': datetime.utcnow().isoformat()
        }

        history = chat_histories.setdefault(sala_id, [])
        history.append(payload)
        if len(history) > CHAT_HISTORY_LIMIT:
            history[:] = history[-CHAT_HISTORY_LIMIT:]

        emit('poker_chat_message', payload, room=_room_name(sala_id))
