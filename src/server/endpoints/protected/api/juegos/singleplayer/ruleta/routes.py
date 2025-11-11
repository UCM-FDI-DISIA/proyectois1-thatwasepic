from flask import request, jsonify, Blueprint
from flask_login import login_required, current_user
from models import db, Apuesta, Estadistica
import random

bp = Blueprint('api_ruleta', __name__, url_prefix='/api/ruleta')

@bp.route('/state', methods=['GET'])
@login_required
def get_state():
    """Obtiene el estado actual de la ruleta del usuario"""
    try:
        stats = Estadistica.query.filter_by(user_id=current_user.id, juego="ruleta").first()
        if not stats:
            stats = Estadistica(
                user_id=current_user.id,
                juego="ruleta",
                partidas_jugadas=0,
                partidas_ganadas=0,
                ganancia_total=0.0,
                apuesta_total=0.0
            )
            db.session.add(stats)
            db.session.commit()

        return jsonify({
            'ok': True,
            'balance': int(current_user.balance * 100),
            'stats': {
                'partidas_jugadas': stats.partidas_jugadas,
                'partidas_ganadas': stats.partidas_ganadas,
                'ganancia_total': stats.ganancia_total,
                'apuesta_total': stats.apuesta_total
            }
        })
    except Exception as e:
        return jsonify({'error': f'Error obteniendo estado: {str(e)}'}), 400


@bp.route('/place', methods=['POST'])
@login_required
def place_bets():
    """Coloca las apuestas y descuenta el dinero del balance"""
    try:
        data = request.get_json()
        bets = data.get('bets', [])
        min_cell = data.get('min_cell', 20)

        if not bets:
            return jsonify({'error': 'No hay apuestas para procesar'}), 400

        total_bet_cents = sum(bet['amount'] for bet in bets)
        total_bet_euros = total_bet_cents / 100

        for bet in bets:
            if bet['amount'] < min_cell:
                return jsonify({'error': f'Apuesta mínima por casilla: {min_cell}¢'}), 400

        if total_bet_euros > current_user.balance:
            return jsonify({'error': 'Fondos insuficientes'}), 400

        current_user.balance -= total_bet_euros

        apuesta = Apuesta(
            user_id=current_user.id,
            juego='ruleta',
            cantidad=total_bet_euros,
            ganancia=0,
            resultado='PENDIENTE'
        )
        db.session.add(apuesta)
        db.session.commit()

        return jsonify({
            'ok': True,
            'balance': int(current_user.balance * 100),
            'mensaje': f'Apuestas colocadas: {total_bet_euros:.2f}€'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error colocando apuestas: {str(e)}'}), 400


@bp.route('/spin', methods=['POST'])
@login_required
def spin_ruleta():
    """Realiza un giro de ruleta y actualiza estadísticas"""
    try:
        data = request.get_json()
        bets = data.get('bets', [])

        # El servidor decide el número ganador para asegurar integridad.
        # Ignoramos cualquier 'result' enviado por el cliente.
        result_number = random.randint(0, 36)

        if not bets:
            return jsonify({'error': 'No hay apuestas para liquidar'}), 400

        PAYOUT = {
            'straight': 35, 'split': 17, 'street': 11,
            'corner': 8, 'line': 5, 'dozen': 2, 'column': 2, 'even': 1
        }

        REDS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

        total_bet_cents = sum(bet['amount'] for bet in bets)
        total_win_cents = 0
        total_returned_cents = 0

        # Calcular resultado
        for bet in bets:
            tipo = bet['type']
            cantidad = bet['amount']
            numeros = set(bet['set'])
            label = bet.get('label', '').lower()

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

        # Conversión a euros
        total_bet_euros = total_bet_cents / 100
        total_win_euros = total_win_cents / 100
        total_returned_euros = total_returned_cents / 100

        # Cuando la apuesta ya se descontó en /place, aquí debemos devolver
        # lo que corresponde: la ganancia bruta más lo devuelto (la propia apuesta).
        # Antes se restaba de nuevo la apuesta (se duplicaba la resta) lo que
        # provocaba que el usuario siempre perdiera la cantidad apostada.
        total_payout_euros = total_win_euros + total_returned_euros

        # Actualizar balance del usuario: añadimos únicamente lo que debe
        # recibirse tras el giro (ganancias + devolución de la apuesta).
        current_user.balance += total_payout_euros

        # Actualizar estadísticas globales
        stats = Estadistica.query.filter_by(user_id=current_user.id, juego="ruleta").first()
        if not stats:
            stats = Estadistica(
                user_id=current_user.id,
                juego="ruleta",
                partidas_jugadas=0,
                partidas_ganadas=0,
                ganancia_total=0.0,
                apuesta_total=0.0
            )
            db.session.add(stats)

        stats.partidas_jugadas += 1
        stats.apuesta_total += total_bet_euros
        #  ganancia_total debe sumar ganancia bruta
        stats.ganancia_total += total_win_euros
        
        if total_win_euros > 0:
            stats.partidas_ganadas += 1

        # Actualizar apuesta
        apuesta = Apuesta.query.filter_by(
            user_id=current_user.id, juego='ruleta', resultado='PENDIENTE'
        ).order_by(Apuesta.id.desc()).first()

        if apuesta:
            apuesta.ganancia = total_win_euros
            apuesta.resultado = f'Número {result_number} - Ganancia: {total_win_euros:.2f}€'

        db.session.commit()

        return jsonify({
            'ok': True,
            'balance': int(current_user.balance * 100),
            'stats': {
                'partidas_jugadas': stats.partidas_jugadas,
                'partidas_ganadas': stats.partidas_ganadas,
                'ganancia_total': stats.ganancia_total,
                'apuesta_total': stats.apuesta_total
            },
            'result': result_number,
            'mensaje': f'¡Sale el número {result_number}! Ganancia: {total_win_euros:.2f}€'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error en el giro: {str(e)}'}), 400