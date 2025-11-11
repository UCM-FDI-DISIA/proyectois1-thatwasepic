from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import User
from endpoints.protected.ui.admin.utils import require_admin

bp = Blueprint('admin_usuarios', __name__)

@bp.route('/admin/usuarios')
@login_required
@require_admin()
def home():  # CORREGIDO: cambiar admin_usuarios por home
    """Gestión de usuarios"""
    try:
        usuarios = User.query.order_by(User.created_at.desc()).all()
        return render_template('admin_usuarios.html', usuarios=usuarios)
    except Exception as e:
        flash(f'Error al cargar la gestión de usuarios: {str(e)}')
        return redirect(url_for('admin_panel.home'))