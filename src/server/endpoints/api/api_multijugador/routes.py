from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, SalaMultijugador, UsuarioSala, User

bp = Blueprint('api_multijugador', __name__)

# Lista de juegos permitidos con sus capacidades máximas
JUEGOS_PERMITIDOS = {
    'blackjack': {'nombre': 'Blackjack', 'max_jugadores': 4},
    'ruleta': {'nombre': 'Ruleta', 'max_jugadores': 4},
    'coinflip': {'nombre': 'Coinflip', 'max_jugadores': 2},
    'carrera_caballos': {'nombre': 'Carrera de Caballos', 'max_jugadores': 4}
}

@bp.route('/api/multijugador/salas')
@login_required
def obtener_salas():
    """Obtener lista de salas disponibles"""
    salas = SalaMultijugador.query.filter_by(estado='esperando').all()
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
    """Obtener lista de juegos permitidos con sus detalles"""
    return jsonify(JUEGOS_PERMITIDOS)

@bp.route('/api/multijugador/crear-sala', methods=['POST'])
@login_required
def crear_sala_api():
    """Crear sala mediante API"""
    data = request.get_json()
    
    nombre = data.get('nombre')
    juego = data.get('juego')
    capacidad = data.get('capacidad', 4)
    apuesta_minima = data.get('apuesta_minima', 10.0)
    
    # Validaciones
    if not nombre or not juego:
        return jsonify({'error': 'Nombre y juego son requeridos'}), 400
    
    # Validar que el juego esté permitido
    if juego not in JUEGOS_PERMITIDOS:
        return jsonify({'error': f'Juego no permitido. Juegos permitidos: {", ".join(JUEGOS_PERMITIDOS.keys())}'}), 400
    
    # Validar capacidad según el juego
    max_jugadores = JUEGOS_PERMITIDOS[juego]['max_jugadores']
    if capacidad < 2 or capacidad > max_jugadores:
        return jsonify({
            'error': f'La capacidad para {JUEGOS_PERMITIDOS[juego]["nombre"]} debe ser entre 2 y {max_jugadores} jugadores'
        }), 400
    
    # Crear sala
    nueva_sala = SalaMultijugador(
        nombre=nombre,
        juego=juego,
        capacidad=capacidad,
        apuesta_minima=apuesta_minima,
        creador_id=current_user.id
    )
    
    db.session.add(nueva_sala)
    db.session.commit()
    
    # El creador se une automáticamente
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
            'es_creador': (us.player.id == sala.creador_id)
        } for us in jugadores]
    })

@bp.route('/api/multijugador/iniciar-partida/<int:sala_id>', methods=['POST'])
@login_required
def iniciar_partida(sala_id):
    """Iniciar una partida multijugador"""
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    # Verificar que el usuario es el creador
    if sala.creador_id != current_user.id:
        return jsonify({'error': 'Solo el creador puede iniciar la partida'}), 403
    
    # Verificar que hay al menos 2 jugadores
    if sala.jugadores_actuales < 2:
        return jsonify({'error': 'Se necesitan al menos 2 jugadores'}), 400
    
    # Cambiar estado de la sala
    sala.estado = 'jugando'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'mensaje': 'Partida iniciada'
    })