from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, DepositoLimite
from datetime import datetime

bp = Blueprint('notificaciones', __name__, url_prefix='/api')

@bp.route('/notificaciones/estado', methods=['GET'])
@login_required
def notificaciones_estado():
    return jsonify({
        "notifications_enabled": current_user.notifications_enabled
    })

@bp.route('/notificaciones/actualizar', methods=['POST'])
@login_required
def notificaciones_actualizar():
    data = request.get_json()

    enabled = data.get("notifications_enabled")
    if enabled is None:
        return jsonify({"error": "Campo notifications_enabled no existente"}), 400

    current_user.notifications_enabled = bool(enabled)
    db.session.commit()

    return jsonify({"message": "Estado de las notificaciones actualizado correctamente."})
