from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Apuesta, Estadistica, IngresoFondos

bp = Blueprint('estadisticas', __name__)

@bp.route('/estadisticas')
@login_required
def home():
    stats = Estadistica.query.filter_by(user_id=current_user.id).all()
    apuestas_recientes = Apuesta.query.filter_by(user_id=current_user.id).order_by(Apuesta.fecha.desc()).limit(10).all()

    # Obtener el parámetro de pestaña activa
    tab_activa = request.args.get('tab', 'recientes')
    page = request.args.get('page', 1, type=int)
    per_page = 8
    
    # Obtener historial de ingresos de fondos con paginación
    ingresos_pagination = IngresoFondos.query.filter_by(user_id=current_user.id)\
        .order_by(IngresoFondos.fecha.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    ingresos_fondos = ingresos_pagination.items
    total_ingresado = db.session.query(db.func.sum(IngresoFondos.cantidad))\
        .filter_by(user_id=current_user.id).scalar() or 0
    
    return render_template('pages/casino/estadisticas/estadisticas.html', 
                         stats=stats, 
                         apuestas=apuestas_recientes,
                         ingresos_fondos=ingresos_fondos,
                         total_ingresado=total_ingresado,
                         pagination=ingresos_pagination,
                         user=current_user)