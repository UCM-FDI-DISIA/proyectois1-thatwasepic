from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from models import db, SalaMultijugador, UsuarioSala, PartidaMultijugador, Apuesta, Estadistica, User
from datetime import datetime
import json, random

bp = Blueprint('api_multijugador_ruleta', __name__)

@bp.route('/ruleta/multijugador')
@login_required
def home():
    """Página principal de la ruleta multijugador"""
    # Render the multijugador template and pass current user so JS receives the balance
    return render_template('juegos_multijugador/ruleta_multijugador.html', user=current_user)


@bp.route('/ruleta/sala/<int:sala_id>')
@login_required
def sala_ruleta(sala_id):
    """Página de sala para una partida multijugador de ruleta.

    Esta ruta sigue la convención usada por CoinFlip y otras rutas de
    juegos: `/ruleta/sala/<id>` para que las redirecciones desde la
    sala de espera funcionen sin problemas.
    """
    sala = SalaMultijugador.query.get_or_404(sala_id)

    # Verificar que el usuario está en la sala
    usuario_en_sala = UsuarioSala.query.filter_by(usuario_id=current_user.id, sala_id=sala_id).first()
    if not usuario_en_sala:
        from flask import redirect, url_for
        return redirect(url_for('salas_espera.lobby'))

    # Solo permitir acceso si la sala está en estado 'jugando'
    if sala.estado != 'jugando':
        from flask import redirect, url_for
        return redirect(url_for('salas_espera.lobby'))

    return render_template('juegos_multijugador/ruleta_multijugador.html', sala=sala, user=current_user)

# Registrar handlers de Socket.IO cuando el blueprint se registre (patrón igual a coinflip)
from .socket_handlers import register_ruleta_handlers


@bp.record_once
def on_register(state):
    socketio = state.app.extensions.get('socketio')
    if socketio:
        register_ruleta_handlers(socketio, state.app)
        print("✅ Handlers de Ruleta multijugador registrados desde blueprint")
    else:
        print("❌ SocketIO no encontrado al registrar handlers de Ruleta")

# Helper: load partida datos_juego as dict
def _load_partida(partida):
    if not partida or not partida.datos_juego:
        return None
    try:
        return json.loads(partida.datos_juego)
    except Exception:
        return None

# Helper: save partida dict
def _save_partida(partida, data):
    partida.datos_juego = json.dumps(data)
    partida.fecha_inicio = partida.fecha_inicio or datetime.utcnow()
    partida.fecha_fin = None
    db.session.add(partida)


@bp.route('/rooms', methods=['GET'])
@login_required
def list_rooms():
    """Lista salas de ruleta en estado 'esperando'"""
    salas = SalaMultijugador.query.filter_by(juego='ruleta', estado='esperando').all()
    out = []
    for s in salas:
        out.append({
            'id': s.id,
            'nombre': s.nombre,
            'capacidad': s.capacidad,
            'jugadores_actuales': s.jugadores_actuales,
            'apuesta_minima': s.apuesta_minima,
            'creador_id': s.creador_id
        })
    return jsonify(out)


@bp.route('/create', methods=['POST'])
@login_required
def create_room():
    data = request.get_json() or {}
    nombre = data.get('nombre') or f"Sala de Ruleta {datetime.utcnow().isoformat()}"
    capacidad = int(data.get('capacidad', 2))
    apuesta_minima = float(data.get('apuesta_minima', 10.0))

    if capacidad < 2:
        return jsonify({'error': 'capacidad mínima 2'}), 400

    sala = SalaMultijugador(
        nombre=nombre,
        juego='ruleta',
        capacidad=capacidad,
        apuesta_minima=apuesta_minima,
        creador_id=current_user.id,
        jugadores_actuales=0,
        estado='esperando'
    )
    db.session.add(sala)
    db.session.commit()

    # auto-join creator
    usuario_sala = UsuarioSala(usuario_id=current_user.id, sala_id=sala.id, posicion=0)
    db.session.add(usuario_sala)
    sala.jugadores_actuales = 1
    db.session.commit()

    return jsonify({'ok': True, 'sala_id': sala.id, 'capacidad': sala.capacidad})


@bp.route('/join', methods=['POST'])
@login_required
def join_room():
    data = request.get_json() or {}
    sala_id = data.get('sala_id')
    if not sala_id:
        return jsonify({'error': 'sala_id requerido'}), 400

    sala = SalaMultijugador.query.get(sala_id)
    if not sala or sala.juego != 'ruleta':
        return jsonify({'error': 'Sala no encontrada'}), 404

    if sala.jugadores_actuales >= sala.capacidad:
        return jsonify({'error': 'Sala llena'}), 400

    exists = UsuarioSala.query.filter_by(usuario_id=current_user.id, sala_id=sala.id).first()
    if exists:
        return jsonify({'ok': True, 'message': 'Ya estás en la sala', 'sala_id': sala.id})

    usuario_sala = UsuarioSala(usuario_id=current_user.id, sala_id=sala.id, posicion=sala.jugadores_actuales)
    db.session.add(usuario_sala)
    sala.jugadores_actuales = sala.jugadores_actuales + 1
    db.session.commit()

    return jsonify({'ok': True, 'sala_id': sala.id, 'jugadores_actuales': sala.jugadores_actuales})


@bp.route('/place', methods=['POST'])
@login_required
def place_secret_bet():
    """Coloca la apuesta secreta en la partida asociada a la sala.
    Body: {"sala_id": int, "bets": [ {..}, ... ] }
    """
    data = request.get_json() or {}
    sala_id = data.get('sala_id')
    bets = data.get('bets')

    if not sala_id or not bets:
        return jsonify({'error': 'sala_id y bets son requeridos'}), 400

    sala = SalaMultijugador.query.get(sala_id)
    if not sala or sala.juego != 'ruleta':
        return jsonify({'error': 'Sala no encontrada'}), 404

    # buscar o crear PartidaMultijugador activa para la sala
    partida = PartidaMultijugador.query.filter_by(sala_id=sala.id, estado='activa').order_by(PartidaMultijugador.id.desc()).first()
    if not partida:
        partida = PartidaMultijugador(sala_id=sala.id, estado='activa')
        db.session.add(partida)
        db.session.commit()

    # calcular total cents
    total_cents = 0
    for b in bets:
        amt = int(b.get('amount', 0))
        total_cents += amt

    total_euros = total_cents / 100.0
    if total_euros > current_user.balance:
        return jsonify({'error': 'Fondos insuficientes'}), 400

    # descuenta balance ahora (retenido en la partida)
    current_user.balance -= total_euros

    # actualizar datos_juego (secret bets por usuario)
    partida_data = _load_partida(partida) or {}
    if 'created_at' not in partida_data:
        partida_data['created_at'] = datetime.utcnow().isoformat()
    bets_map = partida_data.get('bets', {})
    bets_map[str(current_user.id)] = {
        'bets': bets,
        'amount_cents': total_cents,
        'has_spun': False,
        'submitted_at': datetime.utcnow().isoformat()
    }
    partida_data['bets'] = bets_map
    _save_partida(partida, partida_data)

    # crear registro Apuesta pendiente
    apuesta = Apuesta(user_id=current_user.id, juego='ruleta', cantidad=total_euros, ganancia=0, resultado='PENDIENTE')
    db.session.add(apuesta)
    db.session.commit()

    return jsonify({'ok': True, 'balance': int(current_user.balance * 100), 'message': 'Apuesta secreta registrada'})


@bp.route('/spin', methods=['POST'])
@login_required
def spin_room():
    """Marca al jugador como listo y realiza el giro si procede (todos listos o 30s desde created_at)."""
    data = request.get_json() or {}
    sala_id = data.get('sala_id')
    if not sala_id:
        return jsonify({'error': 'sala_id requerido'}), 400

    sala = SalaMultijugador.query.get(sala_id)
    if not sala or sala.juego != 'ruleta':
        return jsonify({'error': 'Sala no encontrada'}), 404

    partida = PartidaMultijugador.query.filter_by(sala_id=sala.id, estado='activa').order_by(PartidaMultijugador.id.desc()).first()
    if not partida:
        return jsonify({'error': 'No hay partida activa'}), 400

    partida_data = _load_partida(partida)
    if not partida_data or 'bets' not in partida_data:
        return jsonify({'error': 'No hay apuestas en la partida'}), 400

    user_key = str(current_user.id)
    if user_key not in partida_data['bets']:
        return jsonify({'error': 'No tienes apuesta en esta partida'}), 400

    # marcar ready
    partida_data['bets'][user_key]['has_spun'] = True
    partida_data['bets'][user_key]['ready_at'] = datetime.utcnow().isoformat()
    _save_partida(partida, partida_data)
    db.session.commit()

    # comprobar condiciones de giro
    bets_map = partida_data.get('bets', {})
    ready_count = sum(1 for v in bets_map.values() if v.get('has_spun'))
    # número de jugadores en sala
    required = sala.capacidad

    created_at = datetime.fromisoformat(partida_data.get('created_at'))
    elapsed = (datetime.utcnow() - created_at).total_seconds()

    auto_spin = elapsed >= 30
    if ready_count < required and not auto_spin:
        return jsonify({'ok': True, 'spun': False, 'players_ready': ready_count, 'players_needed': required, 'seconds_elapsed': int(elapsed)})

    # efectuar giro
    result_number = random.randint(0, 36)

    # payout logic similar a api_ruleta
    PAYOUT = {
        'straight': 35, 'split': 17, 'street': 11,
        'corner': 8, 'line': 5, 'dozen': 2, 'column': 2, 'even': 1
    }
    REDS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

    results_public = {}
    # procesar cada apuesta
    for uid, info in bets_map.items():
        inner_bets = info.get('bets', [])
        total_bet_cents = 0
        total_win_cents = 0
        total_returned_cents = 0
        for bet in inner_bets:
            tipo = bet.get('type')
            cantidad = int(bet.get('amount', 0))
            numeros = set(bet.get('set', []))
            label = bet.get('label', '').lower()
            total_bet_cents += cantidad
            gana = False
            if tipo == 'even':
                if ('rojo' in label and result_number in REDS) \
                or ('negro' in label and result_number not in REDS and result_number != 0) \
                or ('par' in label and result_number % 2 == 0 and result_number != 0) \
                or ('impar' in label and result_number % 2 == 1) \
                or ('1-18' in label and 1 <= result_number <= 18) \
                or ('19-36' in label and 19 <= result_number <= 36):
                    gana = True
            elif result_number in numeros:
                gana = True

            if gana:
                total_win_cents += cantidad * PAYOUT.get(tipo, 0)
                total_returned_cents += cantidad

        total_bet_euros = total_bet_cents / 100.0
        total_win_euros = total_win_cents / 100.0
        total_returned_euros = total_returned_cents / 100.0
        total_payout_euros = total_win_euros + total_returned_euros

        # actualizar balance (la apuesta ya se descontó en /place)
        user = User.query.get(int(uid))
        if user:
            user.balance += total_payout_euros

        # actualizar Apuesta pendiente
        apuesta = Apuesta.query.filter_by(user_id=int(uid), juego='ruleta', resultado='PENDIENTE').order_by(Apuesta.id.desc()).first()
        if apuesta:
            apuesta.ganancia = total_win_euros
            apuesta.resultado = f'Número {result_number} - Ganancia: {total_win_euros:.2f}€'

        stats = Estadistica.query.filter_by(user_id=int(uid), juego='ruleta').first()
        if not stats:
            stats = Estadistica(user_id=int(uid), juego='ruleta', partidas_jugadas=0, partidas_ganadas=0, ganancia_total=0.0, apuesta_total=0.0)
            db.session.add(stats)
        stats.partidas_jugadas += 1
        stats.apuesta_total += total_bet_euros
        stats.ganancia_total += total_win_euros
        if total_win_euros > 0:
            stats.partidas_ganadas += 1

        results_public[uid] = {
            'bet_total_euros': total_bet_euros,
            'win_euros': total_win_euros,
            'payout_euros': total_payout_euros
        }

    # finalizar partida
    partida.estado = 'finalizada'
    partida.datos_juego = json.dumps({'result': result_number, 'results': results_public})
    sala.estado = 'esperando'
    db.session.commit()

    # devolver solo info del usuario que solicita
    my_result = results_public.get(str(current_user.id), {'bet_total_euros': 0, 'win_euros': 0, 'payout_euros': 0})
    return jsonify({'ok': True, 'spun': True, 'result': result_number, 'my_result': my_result})


@bp.route('/status/<int:sala_id>', methods=['GET'])
@login_required
def status(sala_id):
    """Estado rápido de la partida en sala: cuántos ready y segundos transcurridos."""
    sala = SalaMultijugador.query.get_or_404(sala_id)
    partida = PartidaMultijugador.query.filter_by(sala_id=sala.id, estado='activa').order_by(PartidaMultijugador.id.desc()).first()
    if not partida or not partida.datos_juego:
        return jsonify({'ok': True, 'has_partida': False, 'players_ready': 0, 'players_needed': sala.capacidad, 'seconds_elapsed': 0})

    partida_data = _load_partida(partida)
    created_at = partida_data.get('created_at')
    created_dt = datetime.fromisoformat(created_at) if created_at else partida.fecha_inicio or datetime.utcnow()
    elapsed = int((datetime.utcnow() - created_dt).total_seconds())
    bets_map = partida_data.get('bets', {})
    ready_count = sum(1 for v in bets_map.values() if v.get('has_spun'))

    return jsonify({'ok': True, 'has_partida': True, 'players_ready': ready_count, 'players_needed': sala.capacidad, 'seconds_elapsed': elapsed})
