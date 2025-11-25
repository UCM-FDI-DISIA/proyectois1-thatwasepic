from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room, emit, disconnect
from models import db, SalaMultijugador, UsuarioSala
from datetime import datetime
import json
from endpoints.protected.api.juegos.multiplayer.caballos.socket_handlers import register_caballos_handlers

def contar_jugadores_conectados(sala_id):
    """Contar solo jugadores realmente conectados a la sala"""
    return UsuarioSala.query.filter_by(
        sala_id=sala_id,
        estado='conectado'
    ).count()

def generar_url_redireccion(juego, sala_id):
    """Generar la URL correcta de redirección según el juego - MANTENER ORIGINAL"""
    if juego == 'coinflip':
        return f'/api/multijugador/coinflip/sala/{sala_id}'
    elif juego == 'blackjack':
        return f'/blackjack/sala/{sala_id}'
    elif juego == 'ruleta':
        return f'/ruleta/sala/{sala_id}'
    elif juego == 'caballos':
        return f'/caballos/sala/{sala_id}'
    elif juego == 'poker':
        return f'/multijugador/partida/poker/{sala_id}'
    else:
        return f'/multijugador/partida/{juego}/{sala_id}'

def register_socketio_handlers(socketio):
    
    @socketio.on('connect')
    def handle_connect():
        print(f"🔗 Nueva conexión SocketIO: {request.sid}")
        if current_user.is_authenticated:
            print(f"✅ Usuario {current_user.username} conectado a SocketIO (SID: {request.sid})")
            
            # Actualizar estado de conexión en todas sus salas
            salas_usuario = UsuarioSala.query.filter_by(
                usuario_id=current_user.id
            ).all()
            
            for usuario_sala in salas_usuario:
                usuario_sala.ultima_conexion = datetime.utcnow()
                usuario_sala.estado = 'conectado'
            
            db.session.commit()
            
            emit('connection_status', {
                'status': 'connected', 
                'user': current_user.username,
                'user_id': current_user.id
            })
            
            # Unirse automáticamente a las salas donde estaba
            for usuario_sala in salas_usuario:
                sala = SalaMultijugador.query.get(usuario_sala.sala_id)
                if sala and sala.estado == 'esperando':
                    join_room(f'sala_{usuario_sala.sala_id}')
                    print(f"🔄 Reconectado a sala {usuario_sala.sala_id}")
        else:
            print("❌ Conexión rechazada: usuario no autenticado")
            return False

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"🔌 Desconexión SocketIO: {request.sid}")
        if current_user.is_authenticated:
            print(f"❌ Usuario {current_user.username} desconectado de SocketIO")
            
            # Marcar como desconectado en todas sus salas
            salas_usuario = UsuarioSala.query.filter_by(
                usuario_id=current_user.id,
                estado='conectado'
            ).all()
            
            for usuario_sala in salas_usuario:
                usuario_sala.estado = 'desconectado'
                db.session.commit()
                
                # Notificar a la sala que el usuario se desconectó
                emit('user_disconnected', {
                    'user_id': current_user.id,
                    'username': current_user.username,
                    'jugadores_conectados': contar_jugadores_conectados(usuario_sala.sala_id)
                }, room=f'sala_{usuario_sala.sala_id}')
            
            print(f"📝 Usuario {current_user.username} marcado como desconectado")

    @socketio.on('join_room')
    def handle_join_room(data):
        if not current_user.is_authenticated:
            print("❌ Intento de unirse a sala sin autenticación")
            return
        
        sala_id = data.get('sala_id')
        print(f"🎯 Usuario {current_user.username} uniéndose a sala {sala_id}")
        
        sala = SalaMultijugador.query.get(sala_id)
        
        if not sala:
            print(f"❌ Sala {sala_id} no encontrada")
            emit('join_error', {'error': 'Sala no encontrada'})
            return
            
        if sala.estado != 'esperando':
            print(f"❌ Sala {sala_id} no está en estado 'esperando'")
            emit('join_error', {'error': 'La sala no está aceptando jugadores'})
            return
        
        join_room(f'sala_{sala_id}')
        
        usuario_sala = UsuarioSala.query.filter_by(
            usuario_id=current_user.id,
            sala_id=sala_id
        ).first()
        
        if usuario_sala:
            usuario_sala.estado = 'conectado'
            usuario_sala.ultima_conexion = datetime.utcnow()
        else:
            usuario_sala = UsuarioSala(
                usuario_id=current_user.id,
                sala_id=sala_id,
                posicion=sala.jugadores_actuales,
                estado='conectado'
            )
            db.session.add(usuario_sala)
            sala.jugadores_actuales += 1
        
        db.session.commit()
        
        jugadores_conectados = contar_jugadores_conectados(sala_id)
        
        emit('user_joined', {
            'user_id': current_user.id,
            'username': current_user.username,
            'jugadores_actuales': sala.jugadores_actuales,
            'jugadores_conectados': jugadores_conectados,
            'es_creador': (sala.creador_id == current_user.id)
        }, room=f'sala_{sala_id}')
        
        # Enviar estado actual de la sala al nuevo usuario
        jugadores = UsuarioSala.query.filter_by(sala_id=sala_id).join(User).all()
        emit('room_status', {
            'sala': {
                'id': sala.id,
                'nombre': sala.nombre,
                'estado': sala.estado,
                'juego': sala.juego,
                'creador_id': sala.creador_id
            },
            'jugadores': [{
                'id': us.player.id,
                'username': us.player.username,
                'posicion': us.posicion,
                'estado': us.estado,
                'es_creador': (us.player.id == sala.creador_id)
            } for us in jugadores]
        })
        
        print(f"✅ {current_user.username} unido exitosamente a sala {sala_id}")

    @socketio.on('start_game')
    def handle_start_game(data):
        sala_id = data.get('sala_id')
        print(f"🎮 Solicitando inicio de juego para sala {sala_id}")
        
        sala = SalaMultijugador.query.get(sala_id)
        
        if not sala:
            emit('game_start_failed', {'error': 'Sala no encontrada'}, room=request.sid)
            return
            
        if sala.creador_id != current_user.id:
            emit('game_start_failed', {'error': 'Solo el creador puede iniciar el juego'}, room=request.sid)
            return
            
        if sala.estado != 'esperando':
            emit('game_start_failed', {'error': 'La sala no está en estado de espera'}, room=request.sid)
            return
        
        jugadores_conectados = contar_jugadores_conectados(sala_id)
        
        if jugadores_conectados < 2:
            emit('game_start_failed', {
                'error': f'Se necesitan al menos 2 jugadores conectados (actualmente: {jugadores_conectados})'
            }, room=request.sid)
            return
        
        # Actualizar estado de la sala en la base de datos
        sala.estado = 'jugando'
        db.session.commit()
        
        # Generar URL de redirección - USAR LA ORIGINAL
        redirect_url = generar_url_redireccion(sala.juego, sala_id)
        
        print(f"🎮✅ Iniciando juego en sala {sala_id}")
        print(f"👥 Jugadores conectados: {jugadores_conectados}")
        print(f"🔄 Redirigiendo a: {redirect_url}")
        
        # Emitir a TODOS los jugadores de la sala
        emit('game_started', {
            'sala_id': sala_id,
            'juego': sala.juego,
            'redirect_url': redirect_url,
            'creador': current_user.username,
            'timestamp': datetime.utcnow().isoformat(),
            'jugadores_conectados': jugadores_conectados
        }, room=f'sala_{sala_id}')
        
        print(f"📢 Evento 'game_started' emitido a {jugadores_conectados} jugadores")

    # ... (el resto de los handlers se mantienen igual)
    @socketio.on('leave_room')
    def handle_leave_room(data):
        if not current_user.is_authenticated:
            return
        
        sala_id = data.get('sala_id')
        print(f"🚪 Usuario {current_user.username} saliendo de sala {sala_id}")
        
        leave_room(f'sala_{sala_id}')
        
        usuario_sala = UsuarioSala.query.filter_by(
            usuario_id=current_user.id,
            sala_id=sala_id
        ).first()
        
        if usuario_sala:
            usuario_sala.estado = 'desconectado'
            db.session.commit()
        
        jugadores_conectados = contar_jugadores_conectados(sala_id)
        
        emit('user_left', {
            'user_id': current_user.id,
            'username': current_user.username,
            'jugadores_conectados': jugadores_conectados
        }, room=f'sala_{sala_id}')

    @socketio.on('force_leave_room')
    def handle_force_leave_room(data):
        """Salir completamente de la sala"""
        if not current_user.is_authenticated:
            return
        
        sala_id = data.get('sala_id')
        print(f"🚪❌ Usuario {current_user.username} saliendo completamente de sala {sala_id}")
        
        leave_room(f'sala_{sala_id}')
        
        usuario_sala = UsuarioSala.query.filter_by(
            usuario_id=current_user.id,
            sala_id=sala_id
        ).first()
        
        if usuario_sala:
            sala = SalaMultijugador.query.get(sala_id)
            sala.jugadores_actuales -= 1
            db.session.delete(usuario_sala)
            db.session.commit()
            
            jugadores_conectados = contar_jugadores_conectados(sala_id)
            
            emit('user_left_completely', {
                'user_id': current_user.id,
                'username': current_user.username,
                'jugadores_conectados': jugadores_conectados,
                'jugadores_actuales': sala.jugadores_actuales
            }, room=f'sala_{sala_id}')

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
        }, room=f'sala_{sala_id}')
    
    # Registrar handlers específicos de Caballos multijugador
    # Necesitamos pasar socketio y app (que se pasa luego desde app.py)
    # Por ahora, registramos aquí pero register_caballos_handlers se llamará desde app.py