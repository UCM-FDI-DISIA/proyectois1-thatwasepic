from flask import Blueprint, jsonify, request, render_template, abort, current_app
from flask_login import login_required, current_user
from models import db, SalaMultijugador, UsuarioSala, PartidaMultijugador, User, Estadistica, Apuesta
import json
import random
from datetime import datetime
from itertools import combinations
from .socket_handlers import register_poker_handlers

# ⚠️ IMPORTANTE:
# Este blueprint NO tiene url_prefix, igual que ruleta.
# Las rutas llevan el path completo.
bp = Blueprint('api_multijugador_poker', __name__)


@bp.record_once
def on_register(state):
    socketio = state.app.extensions.get('socketio')
    if socketio:
        register_poker_handlers(socketio, state.app)

PALOS = ['♠', '♥', '♦', '♣']
VALORES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
VALOR_MAP = {v: idx + 2 for idx, v in enumerate(VALORES)}  # 2 -> 2 ... A -> 14
HAND_NAMES = {
    8: 'Escalera de color',
    7: 'Póker',
    6: 'Full',
    5: 'Color',
    4: 'Escalera',
    3: 'Trío',
    2: 'Doble pareja',
    1: 'Pareja',
    0: 'Carta alta'
}


# ===========================
#   HELPERS / LÓGICA COMÚN
# ===========================

def _crear_mazo():
    return [{'valor': v, 'palo': p} for p in PALOS for v in VALORES]


def _escalera_mayor(valores: list[int]) -> int | None:
    """
    Recibe lista de valores (ej. [14, 13, 11...]) y devuelve la carta más alta
    de una escalera, soportando la escalera baja A-2-3-4-5 (devuelve 5).
    """
    unicos = sorted(set(valores), reverse=True)
    if len(unicos) < 5:
        return None
    for i in range(len(unicos) - 4):
        ventana = unicos[i:i + 5]
        if ventana[0] - ventana[-1] == 4:
            return ventana[0]
    if set([14, 5, 4, 3, 2]).issubset(set(unicos)):
        return 5
    return None


def _puntuar_combinacion(cartas: tuple[dict, ...]):
    valores = sorted([VALOR_MAP[c['valor']] for c in cartas], reverse=True)
    palos = [c['palo'] for c in cartas]
    conteos = {}
    for v in valores:
        conteos[v] = conteos.get(v, 0) + 1
    pares_conteo = sorted(conteos.items(), key=lambda x: (-x[1], -x[0]))
    es_color = len(set(palos)) == 1
    escalera_alta = _escalera_mayor(valores)

    if es_color and escalera_alta:
        return (8, escalera_alta)

    if pares_conteo[0][1] == 4:
        resto = max(v for v in valores if v != pares_conteo[0][0])
        return (7, pares_conteo[0][0], resto)

    if pares_conteo[0][1] == 3 and len(pares_conteo) > 1 and pares_conteo[1][1] == 2:
        return (6, pares_conteo[0][0], pares_conteo[1][0])

    if es_color:
        return (5, valores)

    if escalera_alta:
        return (4, escalera_alta)

    if pares_conteo[0][1] == 3:
        kickers = sorted([v for v in valores if v != pares_conteo[0][0]], reverse=True)
        return (3, pares_conteo[0][0], kickers)

    parejas = [valor for valor, cnt in pares_conteo if cnt == 2]
    if len(parejas) >= 2:
        parejas = sorted(parejas, reverse=True)[:2]
        kicker = max(v for v in valores if v not in parejas)
        return (2, parejas[0], parejas[1], kicker)

    if pares_conteo[0][1] == 2:
        pareja = pares_conteo[0][0]
        kickers = sorted([v for v in valores if v != pareja], reverse=True)
        return (1, pareja, kickers)

    return (0, valores)


def _evaluar_mejor_mano(cartas: list[dict]):
    if len(cartas) < 5:
        return (0, []), cartas
    mejor_rank = None
    mejor_combo = None
    for combo in combinations(cartas, 5):
        rank = _puntuar_combinacion(combo)
        if mejor_rank is None or rank > mejor_rank:
            mejor_rank = rank
            mejor_combo = combo
    return mejor_rank, list(mejor_combo or [])


def _obtener_o_crear_partida(sala: SalaMultijugador) -> PartidaMultijugador:
    partida = (
        PartidaMultijugador.query
        .filter_by(sala_id=sala.id, estado='activa')
        .order_by(PartidaMultijugador.fecha_inicio.desc())
        .first()
    )

    if partida is None:
        partida = PartidaMultijugador(
            sala_id=sala.id,
            estado='activa',
            datos_juego=json.dumps({
                'juego': 'poker',
                'fase': 'preflop',                 
                'cartas_comunitarias': [],
                'cartas_comunitarias_visibles': [],
                'jugadores': {},
                'bote': 0.0,
                'apuesta_ronda': 0.0,
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
            'fase': 'preflop',                  
            'cartas_comunitarias': [],
            'cartas_comunitarias_visibles': [],
            'jugadores': {},
            'bote': 0.0,
            'apuesta_ronda': 0.0,
            'ganador': None
        }



def _guardar_estado(partida: PartidaMultijugador, estado: dict):
    estado['ultima_actualizacion'] = datetime.utcnow().isoformat()
    partida.datos_juego = json.dumps(estado)
    db.session.commit()
    _emit_estado_actualizado(partida.sala_id)


def _emit_estado_actualizado(sala_id: int):
    socketio = current_app.extensions.get('socketio')
    if not socketio:
        return
    room = f"poker_{sala_id}"
    socketio.emit('poker_estado_actualizado', {'sala_id': sala_id}, room=room)


def _jugador_necesita_actuar(jugador: dict | None, estado: dict) -> bool:
    if not jugador or jugador.get('estado') != 'activo':
        return False
    if estado.get('fase') == 'terminada':
        return False
    ronda = float(estado.get('apuesta_ronda', 0.0) or 0.0)
    apuesta_actual = float(jugador.get('apuesta_actual', 0.0) or 0.0)
    stack = float(jugador.get('stack', 0.0) or 0.0)
    if jugador.get('ha_actuado') and (ronda - apuesta_actual) <= 1e-6:
        return False
    if stack <= 0 and (ronda - apuesta_actual) > 1e-6:
        return False
    return True


def _buscar_turno_desde(estado: dict, start_idx: int = 0):
    orden = estado.get('orden_turnos') or []
    jugadores = estado.get('jugadores', {})
    n = len(orden)
    if n == 0:
        estado['turno_idx'] = None
        estado['turno_actual'] = None
        return
    for offset in range(n):
        idx = (start_idx + offset) % n
        jugador = jugadores.get(str(orden[idx]))
        if _jugador_necesita_actuar(jugador, estado):
            estado['turno_idx'] = idx
            estado['turno_actual'] = orden[idx]
            return
    estado['turno_idx'] = None
    estado['turno_actual'] = None


def _avanzar_turno(estado: dict):
    idx = estado.get('turno_idx')
    if idx is None:
        _buscar_turno_desde(estado, 0)
    else:
        _buscar_turno_desde(estado, idx + 1)


def _indice_siguiente(estado: dict, base_idx: int, saltos: int) -> int:
    orden = estado.get('orden_turnos') or []
    if not orden:
        return 0
    n = len(orden)
    return (base_idx + saltos) % n


def _establecer_turno_para_fase(estado: dict, fase: str):
    orden = estado.get('orden_turnos') or []
    if not orden:
        estado['turno_idx'] = None
        estado['turno_actual'] = None
        return
    total = len(orden)
    dealer_idx = estado.get('dealer_index', 0) % total
    if fase == 'preflop':
        if total <= 2:
            inicio = dealer_idx
        else:
            inicio = _indice_siguiente(estado, dealer_idx, 3)
    else:
        if total == 2:
            inicio = dealer_idx
        else:
            inicio = _indice_siguiente(estado, dealer_idx, 1)
    _buscar_turno_desde(estado, inicio)


def _apostar_blind(jugador: dict, monto: float, estado: dict) -> float:
    monto = float(monto or 0.0)
    if monto <= 0:
        return 0.0
    stack = float(jugador.get('stack', 0.0) or 0.0)
    user = User.query.get(jugador['user_id'])
    saldo = float(user.balance if user else jugador.get('saldo_cuenta', stack))
    disponible = min(stack, saldo)
    aporte = min(monto, disponible)
    jugador['stack'] = stack - aporte
    jugador['apuesta_actual'] = float(jugador.get('apuesta_actual', 0.0)) + aporte
    jugador['total_aportado'] = float(jugador.get('total_aportado', 0.0) or 0.0) + aporte
    estado['bote'] = float(estado.get('bote', 0.0)) + aporte
    nuevo_saldo = saldo - aporte
    jugador['saldo_cuenta'] = nuevo_saldo
    if user:
        user.balance = nuevo_saldo
    if jugador['stack'] <= 1e-6:
        jugador['stack'] = 0.0
        jugador['sin_stack'] = True
    return aporte


def _actualizar_turno_despues_accion(estado: dict, fase_anterior: str):
    fase_actual = estado.get('fase')
    if fase_actual == 'terminada':
        estado['turno_idx'] = None
        estado['turno_actual'] = None
        return
    if fase_actual != fase_anterior:
        _establecer_turno_para_fase(estado, fase_actual)
    else:
        _avanzar_turno(estado)


def _sanitizar_estado_para_usuario(estado: dict, user_id: int) -> dict:
    estado_copia = json.loads(json.dumps(estado))  # copia profunda

    jugadores = estado_copia.get('jugadores', {})
    for uid, info in jugadores.items():
        if int(uid) != int(user_id):
            if estado_copia.get('fase') not in ('showdown', 'terminada'):
                info.pop('cartas', None)
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


def _resolver_si_todos_han_actuado(estado: dict):
    jugadores = estado.get('jugadores', {})
    activos = [j for j in jugadores.values() if j.get('estado') == 'activo']
    if not activos:
        return  # nadie activo

    if len(activos) == 1:
        _finalizar_con_ganador(estado, activos[0])
        return

    # Si falta alguien por actuar, no avanzamos
    if not all(j.get('ha_actuado') for j in activos):
        return

    fase = estado.get('fase', 'preflop')
    comunitarias = estado.get('cartas_comunitarias', [])
    visibles = estado.setdefault('cartas_comunitarias_visibles', [])

    if fase == 'preflop':
        visibles[:] = comunitarias[:3]
        estado['fase'] = 'flop'
        _reiniciar_ronda_apuestas(estado)
        _establecer_turno_para_fase(estado, 'flop')
        return

    if fase == 'flop':
        visibles[:] = comunitarias[:4]
        estado['fase'] = 'turn'
        _reiniciar_ronda_apuestas(estado)
        _establecer_turno_para_fase(estado, 'turn')
        return

    if fase == 'turn':
        visibles[:] = comunitarias[:5]
        estado['fase'] = 'river'
        _reiniciar_ronda_apuestas(estado)
        _establecer_turno_para_fase(estado, 'river')
        return

    if fase in ('river', 'apuestas'):
        _finalizar_con_ganador(estado, None)


def _reiniciar_ronda_apuestas(estado: dict):
    estado['apuesta_ronda'] = 0.0
    for j in estado.get('jugadores', {}).values():
        if j.get('estado') == 'activo':
            j['ha_actuado'] = False
            j['apuesta_actual'] = 0.0
    estado.setdefault('cartas_comunitarias_visibles', [])
    estado['turno_idx'] = None
    estado['turno_actual'] = None


def _finalizar_con_ganador(estado: dict, ganador: dict | None):
    jugadores = estado.get('jugadores', {})
    bote = float(estado.get('bote', 0.0) or 0.0)
    comunitarias = estado.get('cartas_comunitarias', [])
    estado['cartas_comunitarias_visibles'] = list(comunitarias)

    participantes = [j for j in jugadores.values() if j.get('estado') == 'activo']
    if not participantes and ganador:
        participantes = [ganador]

    resultados = []
    for datos in participantes:
        cartas_totales = (datos.get('cartas') or []) + comunitarias
        rank, mejor_mano = _evaluar_mejor_mano(cartas_totales)
        resultados.append({
            'jugador': datos,
            'rank': rank,
            'mano': mejor_mano
        })

    if not resultados:
        estado['fase'] = 'terminada'
        estado['ganador'] = []
        return

    mejor_rank = max(res['rank'] for res in resultados)
    ganadores = [res for res in resultados if res['rank'] == mejor_rank]
    reparto = bote / len(ganadores) if ganadores else 0.0

    estado['ganador'] = []
    participantes_ids = {res['jugador']['user_id'] for res in resultados}

    for res in resultados:
        jugador = res['jugador']
        if jugador in participantes:
            jugador['cartas_visibles'] = jugador.get('cartas')
        else:
            jugador['cartas_visibles'] = jugador.get('cartas_visibles')
        jugador['ha_actuado'] = True
        jugador['mano_ganadora'] = res['mano']
        jugador['mano_texto'] = HAND_NAMES.get(res['rank'][0], 'Mejor mano')
        jugador['apuesta_actual'] = 0.0
        if res in ganadores:
            jugador['stack'] = float(jugador.get('stack', 0.0)) + reparto
            jugador['ultima_accion'] = f'Gana {reparto:.2f}€'
            jugador['es_ganador'] = True
            jugador['ultima_ganancia'] = reparto
            user = User.query.get(jugador['user_id'])
            if user:
                user.balance += reparto
                jugador['saldo_cuenta'] = user.balance
            estado['ganador'].append({
                'user_id': jugador['user_id'],
                'username': jugador['username'],
                'ganancia': reparto,
                'mano': res['mano'],
                'rango': jugador['mano_texto']
            })
        else:
            jugador['es_ganador'] = False
            jugador['ultima_ganancia'] = 0.0

    estado['fase'] = 'terminada'
    estado['bote'] = 0.0
    estado['apuesta_ronda'] = 0.0
    estado['turno_idx'] = None
    estado['turno_actual'] = None

    for datos in jugadores.values():
        if datos['user_id'] not in participantes_ids:
            datos['es_ganador'] = False
            datos['mano_ganadora'] = None
            datos['mano_texto'] = None
            datos['ultima_ganancia'] = 0.0
        stats = (
            Estadistica.query
            .filter_by(user_id=datos['user_id'], juego='poker_multijugador')
            .first()
        )
        if not stats:
            stats = Estadistica(
                user_id=datos['user_id'],
                juego='poker_multijugador',
                partidas_jugadas=0,
                partidas_ganadas=0,
                ganancia_total=0.0,
                apuesta_total=0.0
            )
            db.session.add(stats)
        stats.partidas_jugadas += 1
        stats.apuesta_total += float(datos.get('total_aportado', 0.0) or 0.0)
        if datos.get('es_ganador'):
            stats.partidas_ganadas += 1
            stats.ganancia_total += float(datos.get('ultima_ganancia', 0.0) or 0.0)

        apuesta_total = float(datos.get('total_aportado', 0.0) or 0.0)
        ganancia_total = float(datos.get('ultima_ganancia', 0.0) or 0.0)
        if apuesta_total > 0 or ganancia_total > 0:
            neto = ganancia_total - apuesta_total
            if neto > 1e-6:
                resultado = 'ganada'
            elif neto < -1e-6:
                resultado = 'perdida'
            else:
                resultado = 'empate'
            apuesta = Apuesta(
                user_id=datos['user_id'],
                juego='poker_multijugador',
                cantidad=apuesta_total,
                ganancia=ganancia_total,
                resultado=resultado
            )
            db.session.add(apuesta)



def _accion_generica(sala_id: int, tipo: str, cantidad: float | None = None):
    sala, usuario_sala, resp, code = _asegurar_usuario_en_sala(sala_id)
    if resp is not None:
        return resp, code

    partida = _obtener_o_crear_partida(sala)
    estado = _cargar_estado(partida)

    fase_actual = estado.get('fase')
    if fase_actual not in ('preflop', 'flop', 'turn', 'river'):
        if fase_actual == 'terminada':
            return jsonify({'error': 'La mano ya ha finalizado'}), 400
        return jsonify({'error': 'No se pueden realizar acciones en este momento'}), 400

    jugadores = estado.setdefault('jugadores', {})
    j = jugadores.get(str(current_user.id))
    if j is None:
        return jsonify({'error': 'No estás registrado como jugador en esta mano'}), 400

    if j.get('estado') != 'activo':
        return jsonify({'error': 'Ya no participas en esta mano'}), 400
    if estado.get('ganador'):
        return jsonify({'error': 'La mano ya ha finalizado'}), 400
    turno_actual = estado.get('turno_actual')
    if turno_actual is not None and turno_actual != current_user.id:
        return jsonify({'error': 'No es tu turno'}), 400

    apuesta_ronda = float(estado.setdefault('apuesta_ronda', 0.0) or 0.0)
    apuesta_actual = float(j.get('apuesta_actual', 0.0) or 0.0)

    def comprometer(monto: float) -> float:
        monto = float(monto or 0.0)
        if monto <= 0:
            return 0.0
        stack_disponible = float(j.get('stack', 0.0))
        saldo_usuario = float(getattr(current_user, 'balance', 0.0))
        disponible = min(stack_disponible, saldo_usuario)
        if disponible <= 0:
            raise ValueError('stack')
        aporte = min(monto, disponible)
        j['stack'] = stack_disponible - aporte
        j['apuesta_actual'] = float(j.get('apuesta_actual', 0.0)) + aporte
        j['total_aportado'] = float(j.get('total_aportado', 0.0) or 0.0) + aporte
        estado['bote'] = float(estado.get('bote', 0.0)) + aporte
        current_user.balance = saldo_usuario - aporte
        j['saldo_cuenta'] = current_user.balance
        if j['stack'] <= 1e-6:
            j['stack'] = 0.0
            j['sin_stack'] = True
        return aporte

    mensaje = 'Acción realizada'
    tipo = tipo.lower()

    if tipo == 'call':
        required = max(0.0, apuesta_ronda - apuesta_actual)
        if required <= 1e-6:
            j['ultima_accion'] = 'Check (auto)'
            mensaje = 'No había nada que igualar, se toma como check'
        else:
            try:
                aportado = comprometer(required)
            except ValueError as exc:
                if 'stack' in str(exc):
                    return jsonify({'error': 'No te quedan fichas en la mesa'}), 400
                return jsonify({'error': 'No tienes saldo suficiente para igualar'}), 400
            if aportado + 1e-6 < required:
                j['ultima_accion'] = f'All-in {aportado:.2f}€'
                mensaje = 'Te has puesto all-in'
            else:
                j['ultima_accion'] = f'Call {aportado:.2f}€'
                mensaje = 'Has igualado la apuesta'

    elif tipo == 'check':
        if apuesta_ronda - apuesta_actual > 1e-6:
            return jsonify({'error': 'No puedes hacer check, hay una apuesta activa'}), 400
        j['ultima_accion'] = 'Check'
        mensaje = 'Has hecho check'

    elif tipo == 'fold':
        j['estado'] = 'retirado'
        j['ultima_accion'] = 'Fold'
        mensaje = 'Te has retirado'

    elif tipo == 'raise':
        if cantidad is None or cantidad <= 0:
            return jsonify({'error': 'Indica cuánto quieres subir'}), 400
        subida = float(cantidad)
        apuesta_minima = getattr(sala, 'apuesta_minima', None) or 10.0
        if subida < apuesta_minima:
            return jsonify({'error': f'La subida mínima es de {apuesta_minima:.2f}€'}), 400
        total_a_pagar = max(0.0, apuesta_ronda - apuesta_actual) + subida
        try:
            aportado = comprometer(total_a_pagar)
        except ValueError as exc:
            clave = str(exc)
            if 'balance' in clave:
                return jsonify({'error': 'Saldo insuficiente para subir'}), 400
            return jsonify({'error': 'No te queda stack en la mesa'}), 400
        if aportado + 1e-6 < total_a_pagar:
            return jsonify({'error': 'No te queda stack suficiente para hacer raise'}), 400
        estado['apuesta_ronda'] = float(apuesta_ronda + subida)
        j['ultima_accion'] = f'Raise {subida:.2f}€'
        mensaje = 'Has subido la apuesta'
        for uid, info in jugadores.items():
            if info is not j and info.get('estado') == 'activo':
                info['ha_actuado'] = False

    else:
        return jsonify({'error': 'Acción no soportada'}), 400

    j['ha_actuado'] = True

    fase_antes = estado.get('fase')
    _resolver_si_todos_han_actuado(estado)
    _actualizar_turno_despues_accion(estado, fase_antes)
    _guardar_estado(partida, estado)

    return jsonify({
        'mensaje': mensaje,
        'estado': estado.get('fase'),
        'nuevo_balance': round(float(getattr(current_user, 'balance', 0.0)), 2)
    })


# ===========================
#        RUTAS API
# ===========================

@bp.route('/api/multijugador/poker/estado/<int:sala_id>', methods=['GET'])
@login_required
def estado(sala_id):
    sala, usuario_sala, resp, code = _asegurar_usuario_en_sala(sala_id)
    if resp is not None:
        return resp, code

    partida = _obtener_o_crear_partida(sala)
    estado = _cargar_estado(partida)
    return jsonify(_sanitizar_estado_para_usuario(estado, current_user.id))


@bp.route('/api/multijugador/poker/iniciar/<int:sala_id>', methods=['POST'])
@login_required
def iniciar_mano(sala_id):
    sala, usuario_sala, resp, code = _asegurar_usuario_en_sala(sala_id)
    if resp is not None:
        return resp, code

    # Solo el creador de la sala puede iniciar la mano
    if sala.creador_id != current_user.id:
        return jsonify({'error': 'Solo el creador de la sala puede iniciar una mano'}), 403

    partida = _obtener_o_crear_partida(sala)
    estado_previo = _cargar_estado(partida)

    mazo = _crear_mazo()
    random.shuffle(mazo)

    # Cartas comunitarias (5)
    comunitarias = [mazo.pop() for _ in range(5)]

    # Jugadores: todos los usuarios unidos a la sala
    jugadores_estado = {}
    jugadores_sala = UsuarioSala.query.filter_by(sala_id=sala.id).all()

    for us in jugadores_sala:
        cartas = [mazo.pop(), mazo.pop()]
        jugador_user = getattr(us, 'player', None)
        username = jugador_user.username if jugador_user else f'Usuario {us.usuario_id}'
        stack_inicial = float(getattr(jugador_user, 'balance', 1000.0) or 0.0)
        jugadores_estado[str(us.usuario_id)] = {
            'user_id': us.usuario_id,
            'username': username,
            'stack': stack_inicial,
            'apuesta_actual': 0.0,
            'total_aportado': 0.0,
            'saldo_cuenta': stack_inicial,
            'estado': 'activo',
            'ultima_accion': '---',
            'ha_actuado': False,
            'es_ganador': False,
            'mano_ganadora': None,
            'mano_texto': None,
            'cartas': cartas,
            'cartas_visibles': None
        }

    orden_turnos = [int(uid) for uid in jugadores_estado.keys()]
    if not orden_turnos:
        return jsonify({'error': 'No hay jugadores registrados'}), 400
    total_jugadores = len(orden_turnos)
    prev_dealer_idx = estado_previo.get('dealer_index', -1)
    dealer_index = (prev_dealer_idx + 1) % total_jugadores
    dealer_id = orden_turnos[dealer_index]
    small_blind = float(getattr(sala, 'apuesta_minima', None) or 20.0) / 2.0
    if small_blind < 1.0:
        small_blind = 1.0
    big_blind = max(small_blind * 2, getattr(sala, 'apuesta_minima', None) or 20.0)

    for j in jugadores_estado.values():
        j['rol'] = None
    jugadores_estado[str(dealer_id)]['rol'] = 'dealer'
    if total_jugadores == 1:
        sb_index = dealer_index
        bb_index = dealer_index
    elif total_jugadores == 2:
        sb_index = dealer_index
        bb_index = (dealer_index + 1) % total_jugadores
    else:
        sb_index = (dealer_index + 1) % total_jugadores
        bb_index = (dealer_index + 2) % total_jugadores
    jugadores_estado[str(orden_turnos[sb_index])]['rol'] = 'small_blind'
    jugadores_estado[str(orden_turnos[bb_index])]['rol'] = 'big_blind'

    estado = {
        'juego': 'poker',
        'fase': 'preflop',
        'cartas_comunitarias': comunitarias,
        'cartas_comunitarias_visibles': [], 
        'jugadores': jugadores_estado,
        'bote': 0.0,
        'apuesta_ronda': 0.0,
        'ganador': None,
        'orden_turnos': orden_turnos,
        'dealer_index': dealer_index,
        'turno_idx': None,
        'turno_actual': None,
        'small_blind': round(small_blind, 2),
        'big_blind': round(big_blind, 2)
    }

    sb_jugador = jugadores_estado.get(str(orden_turnos[sb_index]))
    bb_jugador = jugadores_estado.get(str(orden_turnos[bb_index]))
    if sb_jugador:
        aporte_sb = _apostar_blind(sb_jugador, estado['small_blind'], estado)
        if aporte_sb:
            sb_jugador['ultima_accion'] = f'Ciega pequeña {aporte_sb:.2f}€'
    if bb_jugador and bb_jugador is not sb_jugador:
        aporte_bb = _apostar_blind(bb_jugador, estado['big_blind'], estado)
        if aporte_bb:
            bb_jugador['ultima_accion'] = f'Ciega grande {aporte_bb:.2f}€'
        estado['apuesta_ronda'] = max(estado['apuesta_ronda'], aporte_bb)
    elif bb_jugador and bb_jugador is sb_jugador:
        aporte_bb = _apostar_blind(bb_jugador, estado['big_blind'], estado)
        if aporte_bb:
            bb_jugador['ultima_accion'] = f'Ciega grande {aporte_bb:.2f}€'
        estado['apuesta_ronda'] = max(estado['apuesta_ronda'], aporte_bb)

    _establecer_turno_para_fase(estado, 'preflop')

    _guardar_estado(partida, estado)

    return jsonify({'mensaje': 'Nueva mano de póker iniciada'})


@bp.route('/api/multijugador/poker/apostar/<int:sala_id>', methods=['POST'])
@bp.route('/api/multijugador/poker/raise/<int:sala_id>', methods=['POST'])
@login_required
def apostar(sala_id):
    data = request.get_json() or {}
    cantidad = float(data.get('cantidad', 0))
    return _accion_generica(sala_id, 'raise', cantidad)


@bp.route('/api/multijugador/poker/call/<int:sala_id>', methods=['POST'])
@login_required
def hacer_call(sala_id):
    return _accion_generica(sala_id, 'call')


@bp.route('/api/multijugador/poker/pasar/<int:sala_id>', methods=['POST'])
@bp.route('/api/multijugador/poker/check/<int:sala_id>', methods=['POST'])
@login_required
def pasar(sala_id):
    return _accion_generica(sala_id, 'check')


@bp.route('/api/multijugador/poker/retirarse/<int:sala_id>', methods=['POST'])
@bp.route('/api/multijugador/poker/fold/<int:sala_id>', methods=['POST'])
@login_required
def retirarse(sala_id):
    return _accion_generica(sala_id, 'fold')


# ===========================
#     VISTA HTML MULTI
# ===========================

@bp.route('/multijugador/partida/poker/<int:sala_id>')
@login_required
def vista_poker_multijugador(sala_id):
    """
    Esta es la URL a la que redirige salas_espera:
        /multijugador/partida/poker/<sala_id>
    """
    sala = SalaMultijugador.query.get_or_404(sala_id)

    # Si quieres asegurarte:
    if getattr(sala, 'juego', None) not in (None, 'poker'):
        abort(404)

    usuario_sala = UsuarioSala.query.filter_by(
        sala_id=sala_id,
        usuario_id=current_user.id
    ).first()

    if not usuario_sala:
        abort(403)

    return render_template(
        'pages/casino/juegos/multiplayer/poker.html',
        sala=sala
    )
