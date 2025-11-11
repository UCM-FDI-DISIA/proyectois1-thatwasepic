# routes.py - Versión actualizada
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import User
from endpoints.protected.ui.admin.utils import require_admin
from datetime import datetime, timedelta

bp = Blueprint('admin_usuarios', __name__)

@bp.route('/admin/usuarios')
@login_required
@require_admin()
def home():
    """Gestión de usuarios con estadísticas"""
    try:
        usuarios = User.query.order_by(User.created_at.desc()).all()
        
        # Calcular estadísticas (solo balances no negativos)
        usuarios_no_negativos = [user for user in usuarios if user.balance >= 0]
        total_balance = sum(user.balance for user in usuarios_no_negativos)
        usuarios_positivos = sum(1 for user in usuarios_no_negativos if user.balance > 0)
        usuarios_negativos = sum(1 for user in usuarios if user.balance < 0)  # Solo para info
        usuarios_cero = sum(1 for user in usuarios_no_negativos if user.balance == 0)
        
        # Usuarios registrados hoy
        hoy = datetime.now().date()
        usuarios_hoy = sum(1 for user in usuarios_no_negativos if user.created_at.date() == hoy)
        
        # Usuarios activos este mes
        hace_30_dias = datetime.now() - timedelta(days=30)
        usuarios_activos = sum(1 for user in usuarios_no_negativos if user.created_at >= hace_30_dias)
        
        return render_template('admin_usuarios.html', 
                             usuarios=usuarios_no_negativos,  # Solo usuarios no negativos
                             total_balance=total_balance,
                             usuarios_positivos=usuarios_positivos,
                             usuarios_negativos=usuarios_negativos,
                             usuarios_cero=usuarios_cero,
                             usuarios_hoy=usuarios_hoy,
                             usuarios_activos=usuarios_activos,
                             now=datetime.now())
                             
    except Exception as e:
        flash(f'Error al cargar la gestión de usuarios: {str(e)}', 'error')
        return redirect(url_for('admin_panel.home'))