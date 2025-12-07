from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, SalaMultijugador, UsuarioSala, User
from models import BloqueoChat  

bp = Blueprint('api_multijugador', __name__)

JUEGOS_PERMITIDOS = {
    'blackjack': {'nombre': 'Blackjack', 'max_jugadores': 4},
    'ruleta': {'nombre': 'Ruleta', 'max_jugadores': 4},
    'coinflip': {'nombre': 'Coinflip', 'max_jugadores': 2},
    'caballos': {'nombre': 'Carrera de Caballos', 'max_jugadores': 4}
}

@bp.route('/api/multijugador/salas')
@login_required
def obtener_salas():
    """Obtener lista de salas disponibles"""
    salas = SalaMultijugador.query.filter(
        SalaMultijugador.estado == 'esperando',
        SalaMultijugador.jugadores_actuales > 0
    ).all()
    
    return jsonify([{
        'id': sala.id,
        'nombre': sala.nombre,
        'juego': sala.juego,
        'capacidad': sala.capacidad,
        'jugadores_actuales': sala.jugadores_actuales,
        'apuesta_minima': sala.apuesta_minima,
        'creador': sala.owner.username if sala.owner else 'Desconocido'
    } for sala in salas])

@bp.route('/api/multijugador/juegos-permitidos')
@login_required
def obtener_juegos_permitidos():
    return jsonify(JUEGOS_PERMITIDOS)

@bp.route('/api/multijugador/crear-sala', methods=['POST'])
@login_required
def crear_sala_api():
    data = request.get_json()
    
    nombre = data.get('nombre')
    juego = data.get('juego')
    capacidad = data.get('capacidad', 4)
    apuesta_minima = data.get('apuesta_minima', 10.0)
    
    if not nombre or not juego:
        return jsonify({'error': 'Nombre y juego son requeridos'}), 400
    
    if juego not in JUEGOS_PERMITIDOS:
        return jsonify({'error': f'Juego no permitido. Juegos permitidos: {", ".join(JUEGOS_PERMITIDOS.keys())}'}), 400
    
    max_jugadores = JUEGOS_PERMITIDOS[juego]['max_jugadores']
    if capacidad < 2 or capacidad > max_jugadores:
        return jsonify({
            'error': f'La capacidad para {JUEGOS_PERMITIDOS[juego]["nombre"]} debe ser entre 2 y {max_jugadores} jugadores'
        }), 400
    
    nueva_sala = SalaMultijugador(
        nombre=nombre,
        juego=juego,
        capacidad=capacidad,
        apuesta_minima=apuesta_minima,
        creador_id=current_user.id
    )
    
    db.session.add(nueva_sala)
    db.session.commit()
    
    usuario_sala = UsuarioSala(
        usuario_id=current_user.id,
        sala_id=nueva_sala.id,
        posicion=0
    )
    db.session.add(usuario_sala)
    nueva_sala.jugadores_actuales = 1
    db.session.commit()
    
    return jsonify({
        'success': True,
        'sala_id': nueva_sala.id,
        'mensaje': 'Sala creada exitosamente'
    })

@bp.route('/api/multijugador/estado-sala/<int:sala_id>')
@login_required
def estado_sala(sala_id):
    """Obtener estado actual de una sala"""
    sala = SalaMultijugador.query.get_or_404(sala_id)
    jugadores = UsuarioSala.query.filter_by(sala_id=sala_id).join(User).all()
    
    return jsonify({
        'sala': {
            'id': sala.id,
            'nombre': sala.nombre,
            'estado': sala.estado,
            'jugadores_actuales': sala.jugadores_actuales,
            'capacidad': sala.capacidad,
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

@bp.route('/api/multijugador/iniciar-partida/<int:sala_id>', methods=['POST'])
@login_required
def iniciar_partida(sala_id):
    """Iniciar una partida multijugador"""
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    if sala.creador_id != current_user.id:
        return jsonify({'error': 'Solo el creador puede iniciar la partida'}), 403
    
    if sala.jugadores_actuales < 2:
        return jsonify({'error': 'Se necesitan al menos 2 jugadores'}), 400
    
    sala.estado = 'jugando'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'mensaje': 'Partida iniciada'
    })

@bp.route('/api/multijugador/terminar-partida/<int:sala_id>', methods=['POST'])
@login_required
def terminar_partida(sala_id):
    """Terminar una partida y marcar la sala como terminada"""
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    if sala.creador_id != current_user.id:
        return jsonify({'error': 'Solo el creador puede terminar la partida'}), 403
    
    sala.estado = 'terminada'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'mensaje': 'Partida terminada y sala marcada para eliminación'
    })

@bp.route('/api/multijugador/bloquear-usuario/<int:sala_id>/<int:usuario_id>', methods=['POST'])
@login_required
def bloquear_usuario(sala_id, usuario_id):
    """Bloquear a un usuario en el chat de la sala"""
    # Verificaciones
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    # Verificar que ambos usuarios están en la sala
    usuario_en_sala = UsuarioSala.query.filter_by(
        usuario_id=current_user.id,
        sala_id=sala_id
    ).first()
    
    usuario_a_bloquear_en_sala = UsuarioSala.query.filter_by(
        usuario_id=usuario_id,
        sala_id=sala_id
    ).first()
    
    if not usuario_en_sala or not usuario_a_bloquear_en_sala:
        return jsonify({'error': 'Uno de los usuarios no está en la sala'}), 404
    
    if usuario_id == current_user.id:
        return jsonify({'error': 'No puedes bloquearte a ti mismo'}), 400
    
    # Verificar si ya existe el bloqueo
    bloqueo_existente = BloqueoChat.query.filter_by(
        usuario_id=current_user.id,
        usuario_bloqueado_id=usuario_id,
        sala_id=sala_id
    ).first()
    
    if bloqueo_existente:
        return jsonify({'error': 'Ya has bloqueado a este usuario'}), 400
    
    # Crear nuevo bloqueo
    nuevo_bloqueo = BloqueoChat(
        usuario_id=current_user.id,
        usuario_bloqueado_id=usuario_id,
        sala_id=sala_id
    )
    
    db.session.add(nuevo_bloqueo)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'mensaje': 'Usuario bloqueado exitosamente',
        'usuario_bloqueado_id': usuario_id
    })

@bp.route('/api/multijugador/desbloquear-usuario/<int:sala_id>/<int:usuario_id>', methods=['POST'])
@login_required
def desbloquear_usuario(sala_id, usuario_id):
    """Desbloquear a un usuario en el chat de la sala"""
    # Buscar y eliminar bloqueo
    bloqueo = BloqueoChat.query.filter_by(
        usuario_id=current_user.id,
        usuario_bloqueado_id=usuario_id,
        sala_id=sala_id
    ).first()
    
    if not bloqueo:
        return jsonify({'error': 'No has bloqueado a este usuario'}), 404
    
    db.session.delete(bloqueo)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'mensaje': 'Usuario desbloqueado exitosamente'
    })

@bp.route('/api/multijugador/usuarios-bloqueados/<int:sala_id>', methods=['GET'])
@login_required
def obtener_usuarios_bloqueados(sala_id):
    """Obtener lista de usuarios bloqueados por el usuario actual en esta sala"""
    bloqueos = BloqueoChat.query.filter_by(
        usuario_id=current_user.id,
        sala_id=sala_id
    ).all()
    
    usuarios_bloqueados = [bloqueo.usuario_bloqueado_id for bloqueo in bloqueos]
    
    return jsonify({
        'usuarios_bloqueados': usuarios_bloqueados
    })