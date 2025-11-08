from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room, emit
from models import db, SalaMultijugador, UsuarioSala
from datetime import datetime
import json

def register_socketio_handlers(socketio):
    
    @socketio.on('connect')
    def handle_connect():
        if current_user.is_authenticated:
            print(f"✅ Usuario {current_user.username} conectado a SocketIO")
            emit('connection_status', {'status': 'connected', 'user': current_user.username})
        else:
            return False

    @socketio.on('disconnect')
    def handle_disconnect():
        if current_user.is_authenticated:
            print(f"❌ Usuario {current_user.username} desconectado")

    @socketio.on('join_room')
    def handle_join_room(data):
        if not current_user.is_authenticated:
            return
        
        sala_id = data.get('sala_id')
        sala = SalaMultijugador.query.get(sala_id)
        
        if sala:
            join_room(f'sala_{sala_id}')
            
            # Emitir evento a todos en la sala
            emit('user_joined', {
                'user_id': current_user.id,
                'username': current_user.username,
                'jugadores_actuales': sala.jugadores_actuales
            }, room=f'sala_{sala_id}')
            
            print(f"🎮 {current_user.username} se unió a la sala {sala_id}")

    @socketio.on('leave_room')
    def handle_leave_room(data):
        if not current_user.is_authenticated:
            return
        
        sala_id = data.get('sala_id')
        leave_room(f'sala_{sala_id}')
        
        emit('user_left', {
            'user_id': current_user.id,
            'username': current_user.username
        }, room=f'sala_{sala_id}')

    @socketio.on('start_game')
    def handle_start_game(data):
        sala_id = data.get('sala_id')
        sala = SalaMultijugador.query.get(sala_id)
        
        if sala and sala.creador_id == current_user.id:
            sala.estado = 'jugando'
            db.session.commit()
            
            emit('game_started', {
                'sala_id': sala_id,
                'juego': sala.juego
            }, room=f'sala_{sala_id}')

    # ⚠️ CORREGIR: El handler del chat de sala de espera
    @socketio.on('chat_message')
    def handle_chat_message(data):
        if not current_user.is_authenticated:
            return
            
        sala_id = data.get('sala_id')
        message = data.get('message')
        
        print(f"💬 Chat sala {sala_id}: {current_user.username}: {message}")
        
        emit('new_message', {
            'user_id': current_user.id,
            'username': current_user.username,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'sala_{sala_id}')  # ⚠️ Asegúrate de que es 'sala_{sala_id}'

    @socketio.on('game_action')
    def handle_game_action(data):
        sala_id = data.get('sala_id')
        action = data.get('action')
        
        emit('game_update', {
            'user_id': current_user.id,
            'username': current_user.username,
            'action': action,
            'timestamp': data.get('timestamp')
        }, room=f'sala_{sala_id}')