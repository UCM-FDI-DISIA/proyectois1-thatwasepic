from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Apuesta, Estadistica, IngresoFondos

bp = Blueprint('estadisticas', __name__)

def obtener_pagina_transacciones(num_por_pagina):
    page = request.args.get("page", 1, type=int)
    
    ingresos_pag = IngresoFondos.query.filter_by(
        user_id=current_user.id
    ).order_by(IngresoFondos.fecha.desc()).paginate(page=page, per_page=num_por_pagina, error_out=False)

    return ingresos_pag

@bp.route('/estadisticas')
@login_required
def home():
    stats = Estadistica.query.filter_by(user_id=current_user.id).all()
    apuestas_recientes = Apuesta.query.filter_by(user_id=current_user.id).order_by(Apuesta.fecha.desc()).limit(10).all()
    
    # Obtener historial de ingresos de fondos con paginación
    ingresos_pag = obtener_pagina_transacciones(8)

    total_ingresado = db.session.query(db.func.sum(IngresoFondos.cantidad))\
        .filter_by(user_id=current_user.id).scalar() or 0

    # Necesario para actualización automática de la lista de transacciones.
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("partials/tabla_ingresos.html", ingresos=ingresos_pag)
    
    return render_template('pages/casino/estadisticas/estadisticas.html', 
                         stats=stats, 
                         apuestas=apuestas_recientes,
                         total_ingresado=total_ingresado,
                         ingresos=ingresos_pag,
                         user=current_user,
                         realtime_required=True)