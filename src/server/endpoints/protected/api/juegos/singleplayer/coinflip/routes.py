from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Apuesta, Estadistica
from datetime import datetime

bp = Blueprint('api_coinflip', __name__, url_prefix='/api/coinflip')

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

    # Crear registro de la apuesta para estadísticas 
    apuesta = Apuesta(
        user_id=current_user.id,  # Cambiado de usuario_id a user_id
        juego='coinflip',
        tipo_juego='singleplayer',
        cantidad=cantidad,
        ganancia=ganancia,
        resultado='ganada' if gano else 'perdida'
        # Eliminado el campo 'detalles' que no existe en el modelo
    )
    
    db.session.add(apuesta)
    
    stats = Estadistica.query.filter_by(user_id=current_user.id, juego='coinflip').first()
    if not stats:
        stats = Estadistica(
            user_id=current_user.id, 
            juego='coinflip',
            tipo_juego='singleplayer',
            partidas_jugadas=0,
            partidas_ganadas=0,
            ganancia_total=0.0,
            apuesta_total=0.0
        )
        db.session.add(stats)
    
    stats.partidas_jugadas += 1
    stats.apuesta_total += cantidad
    stats.ganancia_total += ganancia
    
    if ganancia > cantidad:  # Si ganó (ganancia = 2*cantidad, por lo tanto > cantidad)
        stats.partidas_ganadas += 1
    
    db.session.commit()

    return jsonify({
        "resultado": "ganada" if gano else "perdida",
        "ganancia": ganancia,
        "nuevo_balance": current_user.balance
    })