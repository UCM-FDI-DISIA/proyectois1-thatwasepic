from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from models import Apuesta, User
from endpoints.protected.ui.admin.utils import require_admin
from sqlalchemy import func

bp = Blueprint('admin_apuestas', __name__)

@bp.route('/admin/apuestas')
@login_required
@require_admin()
def home():
    """Historial de todas las apuestas con filtros"""
    try:
        page = request.args.get('page', 1, type=int)
        juego_filter = request.args.get('juego', '')
        resultado_filter = request.args.get('resultado', '')
        
        # Consulta base
        query = Apuesta.query.join(User)
        
        # Aplicar filtros
        if juego_filter:
            query = query.filter(Apuesta.juego == juego_filter)
        
        if resultado_filter:
            query = query.filter(Apuesta.resultado == resultado_filter)
        
        # Calcular estadísticas
        apuestas_ganadas = Apuesta.query.filter(Apuesta.resultado == 'ganada').count()
        apuestas_perdidas = Apuesta.query.filter(Apuesta.resultado == 'perdida').count()
        
        # Ordenar y paginar
        apuestas = query.order_by(Apuesta.fecha.desc()).paginate(
            page=page, per_page=20, error_out=False)
        
        return render_template('pages/admin/apuestas/apuestas.html', 
                             apuestas=apuestas,
                             juego_actual=juego_filter,
                             resultado_actual=resultado_filter,
                             apuestas_ganadas=apuestas_ganadas,
                             apuestas_perdidas=apuestas_perdidas)
                             
    except Exception as e:
        flash(f'Error al cargar el historial de apuestas: {str(e)}')
        return redirect(url_for('admin_panel.home'))