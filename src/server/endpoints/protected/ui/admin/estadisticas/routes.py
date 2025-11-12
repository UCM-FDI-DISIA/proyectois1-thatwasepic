from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Apuesta, Estadistica
from sqlalchemy import func, text
from endpoints.protected.ui.admin.utils import require_admin

bp = Blueprint('admin_estadisticas', __name__)

@bp.route('/admin/estadisticas')
@login_required
@require_admin()
def home():
    """Estadísticas generales del sistema"""
    try:
        # Estadísticas básicas
        total_usuarios = User.query.count()
        total_apuestas = Apuesta.query.count()
        total_balance = db.session.execute(text("SELECT SUM(balance) FROM user")).scalar() or 0
        total_apostado = db.session.execute(text("SELECT SUM(cantidad) FROM apuesta")).scalar() or 0
        total_ganado = db.session.execute(text("SELECT SUM(ganancia) FROM apuesta")).scalar() or 0
        
        print(f"DEBUG: total_apuestas={total_apuestas}, total_apostado={total_apostado}")

        # Calcular house edge (ganancia de la casa)
        house_edge = (total_apostado - total_ganado) / total_apostado if total_apostado > 0 else 0
        
        # Contar apuestas por resultado
        apuestas_ganadas = Apuesta.query.filter_by(resultado='ganada').count()
        apuestas_perdidas = Apuesta.query.filter_by(resultado='perdida').count()
        apuestas_empate = Apuesta.query.filter_by(resultado='empate').count()
        
        # Top usuarios por balance
        top_usuarios_balance = User.query.order_by(User.balance.desc()).limit(10).all()
        
        # Top apostadores
        top_apostadores = db.session.query(
            User.username,
            func.count(Apuesta.id).label('total_apuestas'),
            func.sum(Apuesta.cantidad).label('total_apostado')
        ).join(Apuesta, User.id == Apuesta.user_id
        ).group_by(User.id, User.username
        ).order_by(func.sum(Apuesta.cantidad).desc()).limit(10).all()
        
        # OBTENER Y AGRUPAR JUEGOS SIMILARES
        juegos_unicos = db.session.query(Apuesta.juego).distinct().all()
        juegos_unicos = [juego[0] for juego in juegos_unicos]
        
        print(f"DEBUG: Juegos únicos encontrados: {juegos_unicos}")
        
        # Definir grupos de juegos que deben agruparse
        grupos_juegos = {
            'coinflip': ['coinflip', 'coinflip_multijugador'],
            'blackjack': ['blackjack', 'blackjack_multijugador'],
            'poker': ['poker', 'poker_multijugador'],
            'tragaperras': ['tragaperras', 'slots'],
            'caballos': ['caballos'],
            'ruleta': ['ruleta']
        }
        
        juegos_stats = {}
        
        # Procesar cada grupo de juegos
        for juego_base, variantes in grupos_juegos.items():
            total_apuestas_grupo = 0
            total_apostado_grupo = 0.0
            total_ganado_grupo = 0.0
            ganadas_grupo = 0
            
            # Sumar estadísticas de todas las variantes de este juego
            for variante in variantes:
                apuestas_variante = Apuesta.query.filter_by(juego=variante).all()
                total_apuestas_grupo += len(apuestas_variante)
                total_apostado_grupo += sum(apuesta.cantidad for apuesta in apuestas_variante)
                total_ganado_grupo += sum(apuesta.ganancia for apuesta in apuestas_variante)
                ganadas_grupo += sum(1 for apuesta in apuestas_variante if apuesta.resultado == 'ganada')
                
                if len(apuestas_variante) > 0:
                    print(f"DEBUG {variante}: {len(apuestas_variante)} apuestas")
            
            # Solo agregar el juego si tiene apuestas
            if total_apuestas_grupo > 0:
                juegos_stats[juego_base] = {
                    'total_apuestas': total_apuestas_grupo,
                    'total_apostado': float(total_apostado_grupo),
                    'total_ganado': float(total_ganado_grupo),
                    'ganadas': ganadas_grupo,
                    'neto': float(total_ganado_grupo - total_apostado_grupo),
                    'variantes': [v for v in variantes if Apuesta.query.filter_by(juego=v).count() > 0]
                }
        
        # Si no hay juegos en los grupos, usar los juegos únicos directamente
        if not juegos_stats and juegos_unicos:
            for juego in juegos_unicos:
                apuestas_juego = Apuesta.query.filter_by(juego=juego).all()
                if apuestas_juego:
                    total_apuestas_juego = len(apuestas_juego)
                    total_apostado_juego = sum(apuesta.cantidad for apuesta in apuestas_juego)
                    total_ganado_juego = sum(apuesta.ganancia for apuesta in apuestas_juego)
                    ganadas_juego = sum(1 for apuesta in apuestas_juego if apuesta.resultado == 'ganada')
                    
                    juegos_stats[juego] = {
                        'total_apuestas': total_apuestas_juego,
                        'total_apostado': float(total_apostado_juego),
                        'total_ganado': float(total_ganado_juego),
                        'ganadas': ganadas_juego,
                        'neto': float(total_ganado_juego - total_apostado_juego),
                        'variantes': [juego]
                    }
        
        print(f"DEBUG: Estadísticas agrupadas: {juegos_stats}")
        
        return render_template('pages/admin/estadisticas/estadisticas.html',
                             total_usuarios=total_usuarios,
                             total_apuestas=total_apuestas,
                             total_balance=total_balance,
                             total_apostado=total_apostado,
                             total_ganado=total_ganado,
                             house_edge=house_edge,
                             apuestas_ganadas=apuestas_ganadas,
                             apuestas_perdidas=apuestas_perdidas,
                             apuestas_empate=apuestas_empate,
                             top_usuarios_balance=top_usuarios_balance,
                             top_apostadores=top_apostadores,
                             juegos_stats=juegos_stats)
    except Exception as e:
        flash(f'Error al cargar las estadísticas: {str(e)}')
        return redirect(url_for('admin_panel.home'))