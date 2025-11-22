# server/endpoints/protected/api/juegos/multiplayer/poker/socket_handlers.py

from datetime import datetime

from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room, emit

from models import SalaMultijugador, UsuarioSala, PartidaMultijugador, User, db
import json

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

    def _return_stack_to_balance(sala_id: int, user_id: int):
        partida = (
            PartidaMultijugador.query
            .filter_by(sala_id=sala_id, estado='activa')
            .order_by(PartidaMultijugador.fecha_inicio.desc())
            .first()
        )
        if not partida:
            return
        try:
            estado = json.loads(partida.datos_juego or '{}')
        except json.JSONDecodeError:
            return
        jugadores = estado.get('jugadores') or {}
        jug = jugadores.get(str(user_id))
        if not jug:
            return
        stack = float(jug.get('stack', 0.0) or 0.0)
        if stack <= 0:
            return
        user = User.query.get(user_id)
        nuevo_balance = float(getattr(user, 'balance', 0.0) or 0.0) + stack
        if user:
            user.balance = nuevo_balance
            db.session.add(user)
        jug['stack'] = 0.0
        jug['saldo_cuenta'] = nuevo_balance
        jug['ultima_accion'] = 'Sale de la mesa'
        estado['jugadores'][str(user_id)] = jug
        partida.datos_juego = json.dumps(estado)
        db.session.commit()
        socketio.emit('poker_estado_actualizado', {'sala_id': sala_id}, room=_room_name(sala_id))

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
        _return_stack_to_balance(sala_id, current_user.id)
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
