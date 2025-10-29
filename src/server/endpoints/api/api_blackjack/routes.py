from flask import request, jsonify, Blueprint
from flask_login import login_required, current_user
from models import db, Apuesta, Estadistica


bp = Blueprint('blackjack_api', __name__, url_prefix='/api/blackjack')

@bp.route('/apostar', methods=['POST'])
@login_required
def apostar():
    try:
        data = request.get_json()
        cantidad = float(data.get('cantidad', 0))
        ganancia = float(data.get('ganancia', 0))
        resultado = data.get('resultado', '')
        
        # Calcular el cambio neto en el balance
        cambio_neto = ganancia - cantidad
        
        # Actualizar el balance del usuario
        current_user.balance += cambio_neto
        
        #  Registrar apuesta
        apuesta = Apuesta(
            user_id=current_user.id,
            juego='blackjack',
            cantidad=cantidad,
            resultado=resultado,
            ganancia=ganancia
        )
        db.session.add(apuesta)
        
        # Actualizar estadísticas
        stats = Estadistica.query.filter_by(user_id=current_user.id, juego='blackjack').first()
        if not stats:
            stats = Estadistica(
                user_id=current_user.id, 
                juego='blackjack',
                partidas_jugadas=0,
                partidas_ganadas=0,
                ganancia_total=0.0,
                apuesta_total=0.0
            )
            db.session.add(stats)
        
        stats.partidas_jugadas += 1
        stats.apuesta_total += cantidad
        stats.ganancia_total += ganancia
        
        if ganancia > cantidad:
            stats.partidas_ganadas += 1
        
        db.session.commit()
        
        return jsonify({
            'nuevo_balance': current_user.balance,
            'cambio_neto': cambio_neto,
            'mensaje': f'Apuesta de blackjack procesada: {resultado}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error procesando apuesta: {str(e)}'}), 400