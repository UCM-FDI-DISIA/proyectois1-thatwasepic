from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Apuesta, Estadistica
from sqlalchemy import text
from ..utils import require_admin

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
        total_ganado = db.session.execute(text("SELECT SUM(ganancia) FROM apuesta")).scalar() or 0
        
        # Calcular métricas de rendimiento
        house_edge = (total_apostado - total_ganado) / total_apostado if total_apostado > 0 else 0
        apuestas_ganadas = Apuesta.query.filter_by(resultado='ganada').count()
        apuestas_perdidas = Apuesta.query.filter_by(resultado='perdida').count()
        
        # Estadísticas por juego agrupadas
        grupos_juegos = {
            'coinflip': ['coinflip', 'coinflip_multijugador'],
            'blackjack': ['blackjack', 'blackjack_multijugador'],
            'poker': ['poker', 'poker_multijugador'],
            'tragaperras': ['tragaperras', 'slots'],
            'caballos': ['caballos'],
            'ruleta': ['ruleta']
        }
        
        juegos_stats = {}
        
        for juego_base, variantes in grupos_juegos.items():
            total_apuestas_grupo = 0
            total_apostado_grupo = 0.0
            total_ganado_grupo = 0.0
            ganadas_grupo = 0
            
            for variante in variantes:
                stats = db.session.query(
                    db.func.count(Apuesta.id).label('total_apuestas'),
                    db.func.sum(Apuesta.cantidad).label('total_apostado'),
                    db.func.sum(Apuesta.ganancia).label('total_ganado')
                ).filter(Apuesta.juego == variante).first()
                
                ganadas = Apuesta.query.filter_by(juego=variante, resultado='ganada').count()
                
                total_apuestas_grupo += stats[0] or 0
                total_apostado_grupo += stats[1] or 0.0
                total_ganado_grupo += stats[2] or 0.0
                ganadas_grupo += ganadas
            
            if total_apuestas_grupo > 0:
                juegos_stats[juego_base] = {
                    'total_apuestas': total_apuestas_grupo,
                    'total_apostado': float(total_apostado_grupo),
                    'total_ganado': float(total_ganado_grupo),
                    'ganadas': ganadas_grupo,
                    'neto': float(total_ganado_grupo - total_apostado_grupo)
                }
        
        usuarios_recientes = User.query.order_by(User.created_at.desc()).limit(5).all()
        apuestas_recientes = Apuesta.query.join(User).order_by(Apuesta.fecha.desc()).limit(10).all()
        
        return render_template('pages/admin/inicio/index.html',
                             total_usuarios=total_usuarios,
                             total_apuestas=total_apuestas,
                             total_balance=total_balance,
                             total_apostado=total_apostado,
                             total_ganado=total_ganado,
                             house_edge=house_edge,
                             apuestas_ganadas=apuestas_ganadas,
                             apuestas_perdidas=apuestas_perdidas,
                             juegos_stats=juegos_stats,
                             usuarios_recientes=usuarios_recientes,
                             apuestas_recientes=apuestas_recientes)
    except Exception as e:
        flash(f'Error al cargar el panel administrativo: {str(e)}')
        return redirect(url_for('admin_panel.home'))