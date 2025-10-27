from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db

bp = Blueprint('coinflip_api', __name__, url_prefix='/api/coinflip')

@bp.route('/apostar', methods=['POST'])
@login_required
def apostar():
    """
    Recibe una apuesta del juego de cara o cruz.
    Espera un JSON con:
        {
            "cantidad": float,
            "eleccion": "cara" | "cruz",
            "resultado_moneda": "cara" | "cruz"
        }
    Devuelve un JSON con:
        {
            "resultado": "ganada" | "perdida",
            "ganancia": float,
            "nuevo_balance": float
        }
    """
    data = request.get_json()

    try:
        cantidad = float(data.get('cantidad', 0))
        eleccion = data.get('eleccion')
        resultado = data.get('resultado_moneda')
    except (TypeError, ValueError):
        return jsonify({"error": "Datos inválidos"}), 400

    # Validaciones básicas
    if cantidad <= 0 or eleccion not in ['cara', 'cruz'] or resultado not in ['cara', 'cruz']:
        return jsonify({"error": "Parámetros incorrectos"}), 400

    if current_user.balance < cantidad:
        return jsonify({"error": "Fondos insuficientes"}), 400

    # Restar la apuesta
    current_user.balance -= cantidad

    # Determinar si ganó
    gano = (eleccion == resultado)
    ganancia = cantidad * 2 if gano else 0

    if gano:
        current_user.balance += ganancia

    # Guardar en base de datos
    db.session.commit()

    return jsonify({
        "resultado": "ganada" if gano else "perdida",
        "ganancia": ganancia,
        "nuevo_balance": current_user.balance
    })
