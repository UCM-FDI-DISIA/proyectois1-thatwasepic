from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from models import Apuesta, User
from ..admin_routes_utils import require_admin

# Crear blueprint directamente aquí
bp = Blueprint('admin_apuestas', __name__)

@bp.route('/admin/apuestas')
@login_required
@require_admin()
def home():
    """Historial de todas las apuestas"""
    try:
        page = request.args.get('page', 1, type=int)
        apuestas = Apuesta.query.join(User).order_by(Apuesta.fecha.desc()).paginate(
            page=page, per_page=20, error_out=False)
        
        return render_template('admin_apuestas.html', apuestas=apuestas)
    except Exception as e:
        flash(f'Error al cargar el historial de apuestas: {str(e)}')
        return redirect(url_for('admin_panel.home'))