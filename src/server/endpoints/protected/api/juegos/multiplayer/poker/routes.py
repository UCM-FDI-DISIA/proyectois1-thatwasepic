from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, SalaMultijugador, UsuarioSala, PartidaMultijugador
import json
import random
from datetime import datetime

bp = Blueprint(
    'api_multijugador_poker',
    __name__,
    url_prefix='/api/multijugador/poker'
)
PALOS = ['♠', '♥', '♦', '♣']
VALORES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']


def _crear_mazo():
    return [{'valor': v, 'palo': p} for p in PALOS for v in VALORES]


def _obtener_o_crear_partida(sala: SalaMultijugador) -> PartidaMultijugador:
    partida = PartidaMultijugador.query.filter_by(sala_id=sala.id, estado='activa').order_by(
        PartidaMultijugador.fecha_inicio.desc()
    ).first()
    if partida is None:
        partida = PartidaMultijugador(
            sala_id=sala.id,
            estado='activa',
            datos_juego=json.dumps({
                'juego': 'poker',
                'fase': 'esperando',
                'cartas_comunitarias': [],
                'jugadores': {},
                'bote': 0.0,
                'ganador': None,
                'ultima_actualizacion': datetime.utcnow().isoformat()
            })
        )
        db.session.add(partida)
        db.session.commit()
    return partida


def _cargar_estado(partida: PartidaMultijugador):
    try:
        return json.loads(partida.datos_juego or '{}')
    except json.JSONDecodeError:
        return {
            'juego': 'poker',
            'fase': 'esperando',
            'cartas_comunitarias': [],
            'jugadores': {},
            'bote': 0.0,
            'ganador': None
        }


def _guardar_estado(partida: PartidaMultijugador, estado: dict):
    estado['ultima_actualizacion'] = datetime.utcnow().isoformat()
    partida.datos_juego = json.dumps(estado)
    db.session.commit()


def _sanitizar_estado_para_usuario(estado: dict, user_id: int) -> dict:
    """Quita las cartas privadas de otros jugadores antes de mandar al frontend."""
    estado_copia = json.loads(json.dumps(estado))  # copia profunda sencilla

    jugadores = estado_copia.get('jugadores', {})
    for uid, info in jugadores.items():
        if int(uid) != int(user_id):
            # No enseñar cartas de otros salvo en showdown
            if estado_copia.get('fase') != 'showdown':
                info.pop('cartas', None)
            # 'cartas_visibles' solo se rellena en showdown
    return estado_copia


def _asegurar_usuario_en_sala(sala_id: int):
    sala = SalaMultijugador.query.get_or_404(sala_id)
    usuario_sala = UsuarioSala.query.filter_by(
        sala_id=sala_id,
        usuario_id=current_user.id
    ).first()
    if usuario_sala is None:
        return None, None, jsonify({'error': 'No perteneces a esta sala'}), 403
    return sala, usuario_sala, None, None


@bp.route('/estado/<int:sala_id>', methods=['GET'])
@login_required
def estado(sala_id):
    sala, usuario_sala, resp, code = _asegurar_usuario_en_sala(sala_id)
    if resp is not None:
        return resp, code

    partida = _obtener_o_crear_partida(sala)
    estado = _cargar_estado(partida)
    return jsonify(_sanitizar_estado_para_usuario(estado, current_user.id))


@bp.route('/iniciar/<int:sala_id>', methods=['POST'])
@login_required
def iniciar_mano(sala_id):
    sala, usuario_sala, resp, code = _asegurar_usuario_en_sala(sala_id)
    if resp is not None:
        return resp, code

    # Solo el creador de la sala puede iniciar la mano
    if sala.creador_id != current_user.id:
        return jsonify({'error': 'Solo el creador de la sala puede iniciar una mano'}), 403

    partida = _obtener_o_crear_partida(sala)

    mazo = _crear_mazo()
    random.shuffle(mazo)

    # Cartas comunitarias (mostradas directamente para simplificar)
    comunitarias = [mazo.pop() for _ in range(5)]

    # Jugadores: todos los usuarios unidos a la sala
    jugadores_estado = {}
    jugadores_sala = UsuarioSala.query.filter_by(sala_id=sala.id).all()

    for us in jugadores_sala:
        # Dos cartas privadas por jugador
        cartas = [mazo.pop(), mazo.pop()]
        jugadores_estado[str(us.usuario_id)] = {
            'user_id': us.usuario_id,
            'username': us.player.username if hasattr(us, 'player') and us.player else f'Usuario {us.usuario_id}',
            'stack': 1000.0,
            'apuesta_actual': 0.0,
            'estado': 'activo',
            'ultima_accion': '---',
            'ha_actuado': False,
            'cartas': cartas,
            'cartas_visibles': None
        }

    estado = {
        'juego': 'poker',
        'fase': 'apuestas',
        'cartas_comunitarias': comunitarias,
        'jugadores': jugadores_estado,
        'bote': 0.0,
        'ganador': None
    }

    _guardar_estado(partida, estado)

    return jsonify({'mensaje': 'Nueva mano de póker iniciada'})


def _resolver_si_todos_han_actuado(estado: dict):
    jugadores = estado.get('jugadores', {})
    activos = [j for j in jugadores.values() if j.get('estado') == 'activo']
    if not activos:
        return  # nadie activo, dejamos la mano como está

    if not all(j.get('ha_actuado') for j in activos):
        return  # aún quedan jugadores por actuar

    # Todos han actuado: elegimos un ganador aleatorio entre los activos
    ganador = random.choice(activos)

    bote = estado.get('bote', 0.0) or 0.0
    ganador['stack'] = float(ganador.get('stack', 1000.0)) + float(bote)
    ganador['ultima_accion'] = 'ganador'

    # Mostramos cartas de todos en showdown
    for j in jugadores.values():
        j['cartas_visibles'] = j.get('cartas')

    estado['fase'] = 'terminada'
    estado['ganador'] = {
        'user_id': ganador['user_id'],
        'username': ganador['username'],
        'ganancia': bote
    }


def _accion_generica(sala_id: int, tipo: str, cantidad: float | None = None):
    sala, usuario_sala, resp, code = _asegurar_usuario_en_sala(sala_id)
    if resp is not None:
        return resp, code

    partida = _obtener_o_crear_partida(sala)
    estado = _cargar_estado(partida)

    if estado.get('fase') not in ('apuestas',):
        return jsonify({'error': 'No se pueden realizar acciones en este momento'}), 400

    jugadores = estado.setdefault('jugadores', {})
    j = jugadores.get(str(current_user.id))
    if j is None:
        return jsonify({'error': 'No estás registrado como jugador en esta mano'}), 400

    if j.get('estado') != 'activo':
        return jsonify({'error': 'Ya no participas en esta mano'}), 400

    if tipo == 'apostar':
        if cantidad is None or cantidad <= 0:
            return jsonify({'error': 'Cantidad de apuesta no válida'}), 400
        apuesta_minima = sala.apuesta_minima or 10.0
        if cantidad < apuesta_minima:
            return jsonify({'error': f'La apuesta mínima de la sala es {apuesta_minima}'}), 400

        j['apuesta_actual'] = float(j.get('apuesta_actual', 0.0)) + float(cantidad)
        estado['bote'] = float(estado.get('bote', 0.0)) + float(cantidad)
        j['ultima_accion'] = f'apuesta {cantidad:.2f}€'

    elif tipo == 'pasar':
        j['ultima_accion'] = 'pasa'

    elif tipo == 'retirarse':
        j['estado'] = 'retirado'
        j['ultima_accion'] = 'se retira'

    j['ha_actuado'] = True

    # Comprobar si termina la mano
    _resolver_si_todos_han_actuado(estado)
    _guardar_estado(partida, estado)

    mensajes = {
        'apostar': 'Apuesta realizada',
        'pasar': 'Has pasado',
        'retirarse': 'Te has retirado de la mano'
    }

    return jsonify({
        'mensaje': mensajes.get(tipo, 'Acción realizada'),
        'estado': estado.get('fase')
    })


@bp.route('/apostar/<int:sala_id>', methods=['POST'])
@login_required
def apostar(sala_id):
    data = request.get_json() or {}
    cantidad = float(data.get('cantidad', 0))
    return _accion_generica(sala_id, 'apostar', cantidad)


@bp.route('/pasar/<int:sala_id>', methods=['POST'])
@login_required
def pasar(sala_id):
    return _accion_generica(sala_id, 'pasar')


@bp.route('/retirarse/<int:sala_id>', methods=['POST'])
@login_required
def retirarse(sala_id):
    return _accion_generica(sala_id, 'retirarse')
