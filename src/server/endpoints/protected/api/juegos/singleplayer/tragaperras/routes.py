from flask import request, jsonify, Blueprint
from flask_login import login_required, current_user
from models import db, Apuesta, Estadistica

bp = Blueprint('api_tragaperras', __name__, url_prefix='/api/tragaperras')

@bp.route('/apostar', methods=['POST'])
@login_required
def apostar():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
            
        cantidad = float(data['cantidad'])
        ganancia = float(data['ganancia'])
        resultado = data['resultado']
        
        # Verificar fondos
        if cantidad > current_user.balance:
            return jsonify({'error': 'Fondos insuficientes'}), 400
        
        # Actualizar balance
        current_user.balance = current_user.balance - cantidad + ganancia
        
        # Registrar apuesta
        apuesta = Apuesta(
            user_id=current_user.id,
            juego='tragaperras',
            cantidad=cantidad,
            resultado=resultado,
            ganancia=ganancia
        )
        db.session.add(apuesta)
        
        #  Actualizar estadísticas
        stats = Estadistica.query.filter_by(user_id=current_user.id, juego='tragaperras').first()
        if not stats:
            stats = Estadistica(
                user_id=current_user.id, 
                juego='tragaperras',
                partidas_jugadas=0,
                partidas_ganadas=0,
                ganancia_total=0.0,
                apuesta_total=0.0
            )
            db.session.add(stats)
        
        stats.partidas_jugadas += 1
        stats.apuesta_total += cantidad
        # ganancia_total debe sumar ganancia bruta, no neta
        stats.ganancia_total += ganancia
        
        if ganancia > cantidad:
            stats.partidas_ganadas += 1
        
        db.session.commit()
        
        return jsonify({
            'nuevo_balance': current_user.balance,
            'mensaje': f'Apuesta de tragaperras procesada: {resultado}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500