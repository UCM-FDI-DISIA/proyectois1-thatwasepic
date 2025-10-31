from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Apuesta, Estadistica
from sqlalchemy import text
from ..admin_routes_utils import require_admin

bp = Blueprint('admin_panel', __name__)

@bp.route('/admin')
@login_required
@require_admin()
def home():
    """Panel principal de administración"""
    try:
        total_usuarios = User.query.count()
        total_apuestas = Apuesta.query.count()
        total_balance = db.session.execute(text("SELECT SUM(balance) FROM user")).scalar() or 0
        total_apostado = db.session.execute(text("SELECT SUM(cantidad) FROM apuesta")).scalar() or 0
        
        juegos = ['blackjack', 'poker', 'coinflip', 'tragaperras', 'caballos']
        juegos_stats = {}
        
        for juego in juegos:
            stats = db.session.query(
                db.func.count(Apuesta.id).label('total_apuestas'),
                db.func.sum(Apuesta.cantidad).label('total_apostado'),
                db.func.sum(Apuesta.ganancia).label('total_ganado')
            ).filter(Apuesta.juego == juego).first()
            
            ganadas = Apuesta.query.filter_by(juego=juego, resultado='ganada').count()
            
            juegos_stats[juego] = {
                'total_apuestas': stats[0] or 0,
                'total_apostado': stats[1] or 0,
                'total_ganado': stats[2] or 0,
                'ganadas': ganadas
            }
        
        usuarios_recientes = User.query.order_by(User.created_at.desc()).limit(5).all()
        apuestas_recientes = Apuesta.query.join(User).order_by(Apuesta.fecha.desc()).limit(10).all()
        
        return render_template('admin_panel.html',
                             total_usuarios=total_usuarios,
                             total_apuestas=total_apuestas,
                             total_balance=total_balance,
                             total_apostado=total_apostado,
                             juegos_stats=juegos_stats,
                             usuarios_recientes=usuarios_recientes,
                             apuestas_recientes=apuestas_recientes)
    except Exception as e:
        flash(f'Error al cargar el panel administrativo: {str(e)}')
        return redirect(url_for('admin_panel.home'))