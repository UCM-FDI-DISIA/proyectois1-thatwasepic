from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, DepositoLimite
from datetime import datetime

bp = Blueprint('limite_depositos', __name__, url_prefix='/api')

@bp.route('/limite_depositos', methods=['GET'])
@login_required
def obtener_limite():
    limite = DepositoLimite.query.filter_by(user_id=current_user.id).first()

    if not limite:
        return jsonify({'activo': False})

    return jsonify({
        'activo': True,
        'limite_monto': limite.limite_monto,
        'periodo_dias': limite.periodo_dias,
        'fecha_establecido': limite.fecha_establecido.strftime('%d/%m/%y %H:%M:%S')
    })

@bp.route('/limite_depositos', methods=['POST'])
@login_required
def establecer_limite():
    data = request.get_json()
    monto = float(data.get('monto', 0))
    dias = int(data.get('dias', 0))

    if monto < 20:
        return jsonify({'error': 'El límite debe ser de al menos $20'}), 400
    if dias < 1:
        return jsonify({'error': 'El periodo debe ser de al menos 1 día'}), 400

    limite = DepositoLimite.query.filter_by(user_id=current_user.id).first()

    if not limite:
        limite = DepositoLimite(user_id=current_user.id)

    limite.limite_monto = monto
    limite.periodo_dias = dias
    limite.fecha_establecido = datetime.utcnow()

    db.session.add(limite)
    db.session.commit()

    return jsonify({'ok': True, 'mensaje': 'Límite establecido correctamente'})

@bp.route('/limite_depositos', methods=['DELETE'])
@login_required
def eliminar_limite():
    limite = DepositoLimite.query.filter_by(user_id=current_user.id).first()
    if not limite:
        return jsonify({'error': 'No hay límite configurado'}), 400

    db.session.delete(limite)
    db.session.commit()

    return jsonify({'ok': True, 'mensaje': 'El límite ha sido eliminado'})
