from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Apuesta
from sqlalchemy import func  #  Asegurar que func está importado
from ..admin_routes_utils import require_admin


# Crear blueprint directamente aquí
bp = Blueprint('admin_estadisticas', __name__)

@bp.route('/admin/estadisticas')
@login_required
@require_admin()
def home():
    """Estadísticas generales del sistema"""
    try:
        # Top usuarios por balance
        top_usuarios_balance = User.query.order_by(User.balance.desc()).limit(10).all()
        
        # Top apostadores
        top_apostadores = db.session.query(
            User.username,
            func.sum(Apuesta.cantidad).label('total_apostado')
        ).join(Apuesta).group_by(User.id).order_by(func.sum(Apuesta.cantidad).desc()).limit(10).all()
        
        return render_template('admin_estadisticas.html',
                             top_usuarios_balance=top_usuarios_balance,
                             top_apostadores=top_apostadores)
    except Exception as e:
        flash(f'Error al cargar las estadísticas: {str(e)}')
        return redirect(url_for('admin_panel.home'))