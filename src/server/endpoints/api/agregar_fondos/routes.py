from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Apuesta, Estadistica


bp = Blueprint('agregar_fondos', __name__, url_prefix='/api')

@bp.route('/agregar_fondos', methods=['POST'])
@login_required
def agregar_fondos():
    data = request.get_json()
    cantidad = float(data['cantidad'])
    
    if cantidad <= 0:
        return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
    
    current_user.balance += cantidad
    db.session.commit()
    
    return jsonify({
        'nuevo_balance': current_user.balance,
        'mensaje': f'Se agregaron ${cantidad:.2f} a tu cuenta'
    })

@bp.route('/account/state', methods=['GET'])
@login_required
def account_state():
    # Devuelve balance y (si hay) stats de ruleta en tu tabla general
    stats = Estadistica.query.filter_by(user_id=current_user.id, juego="ruleta").first()
    return jsonify({
        'ok': True,
        'balance': int(current_user.balance * 100),   # céntimos
        'balance_float': float(current_user.balance), # euros
        'ruleta_stats': {
            'partidas_jugadas': stats.partidas_jugadas,
            'partidas_ganadas': stats.partidas_ganadas,
            'ganancia_total': stats.ganancia_total,
            'apuesta_total': stats.apuesta_total
        } if stats else None
    })


@bp.route('/balance', methods=['GET'])
@login_required
def obtener_balance():
    return jsonify({'balance': current_user.balance})
