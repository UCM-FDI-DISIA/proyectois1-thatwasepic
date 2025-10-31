from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import User, Estadistica, Apuesta
from ..admin_routes_utils import require_admin

bp = Blueprint('admin_usuario_detalle', __name__)

@bp.route('/admin/usuario/<int:user_id>')
@login_required
@require_admin()
def home(user_id):  # Ya está correcto
    """Detalles de un usuario específico"""
    try:
        usuario = User.query.get_or_404(user_id)
        stats = Estadistica.query.filter_by(user_id=user_id).all()
        apuestas = Apuesta.query.filter_by(user_id=user_id).order_by(Apuesta.fecha.desc()).limit(20).all()
        
        return render_template('admin_usuario_detalle.html',
                             usuario=usuario,
                             stats=stats,
                             apuestas=apuestas)
    except Exception as e:
        flash(f'Error al cargar los detalles del usuario: {str(e)}')
        return redirect(url_for('admin_panel.home'))