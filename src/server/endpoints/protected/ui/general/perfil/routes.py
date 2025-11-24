from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Estadistica, IngresoFondos
from endpoints.protected.ui.admin.utils import is_admin_user

bp = Blueprint('perfil', __name__)

@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def home():
    stats = Estadistica.query.filter_by(user_id=current_user.id).all()
    
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
    
    if request.method == 'POST':
        nuevo_username = request.form.get('username')
        nuevo_email = request.form.get('email')
        nueva_password = request.form.get('password')
        
        if nuevo_username and nuevo_username != current_user.username:
            usuario_existente = User.query.filter_by(username=nuevo_username).first()
            if usuario_existente:
                flash('El nombre de usuario ya está en uso')
                return redirect(url_for('perfil.home'))
            current_user.username = nuevo_username
        
        if nuevo_email and nuevo_email != current_user.email:
            email_existente = User.query.filter_by(email=nuevo_email).first()
            if email_existente:
                flash('El email ya está en uso')
                return redirect(url_for('perfil.home'))
            current_user.email = nuevo_email
        
        if nueva_password:
            if len(nueva_password) < 6:
                flash('La contraseña debe tener al menos 6 caracteres')
                return redirect(url_for('perfil.home'))
            current_user.set_password(nueva_password)
        
        db.session.commit()
        flash('Perfil actualizado correctamente')
        return redirect(url_for('perfil.home'))
    
    return render_template('pages/casino/perfil/perfil.html', 
                         user=current_user, 
                         stats=stats, 
                         ingresos_fondos=ingresos_fondos,
                         total_ingresado=total_ingresado,
                         pagination=ingresos_pagination,
                         is_admin=is_admin_user)