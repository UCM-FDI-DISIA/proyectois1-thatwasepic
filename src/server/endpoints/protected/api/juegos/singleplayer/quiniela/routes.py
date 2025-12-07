from flask import request, jsonify, Blueprint
from flask_login import login_required, current_user
from models import db, Apuesta, Estadistica
import random

bp = Blueprint('api_quiniela', __name__, url_prefix='/api/quiniela')

# Base de datos de equipos por liga
LIGAS_EQUIPOS = {
    'espana': {
        'nombre': 'LaLiga Santander',
        'equipos': [
            "Real Madrid", "FC Barcelona", "Atlético Madrid", "Sevilla FC",
            "Real Betis", "Villarreal CF", "Athletic Bilbao", "Real Sociedad",
            "Valencia CF", "Celta de Vigo", "Getafe CF", "Osasuna",
            "Mallorca", "Girona FC", "Rayo Vallecano", "Almería",
            "Cádiz CF", "Granada CF", "Las Palmas", "Deportivo Alavés"
        ]
    },
    'premier': {
        'nombre': 'Premier League',
        'equipos': [
            "Manchester City", "Liverpool", "Chelsea", "Arsenal",
            "Tottenham", "Manchester United", "Newcastle", "Brighton",
            "West Ham", "Crystal Palace", "Fulham", "Wolves",
            "Everton", "Brentford", "Aston Villa", "Nottingham Forest",
            "Leeds United", "Leicester City", "Southampton", "Bournemouth"
        ]
    },
    'serie_a': {
        'nombre': 'Serie A',
        'equipos': [
            "Juventus", "Inter Milan", "AC Milan", "Napoli",
            "Roma", "Lazio", "Atalanta", "Fiorentina",
            "Bologna", "Torino", "Monza", "Udinese",
            "Sassuolo", "Empoli", "Salernitana", "Lecce",
            "Verona", "Cagliari", "Genoa", "Frosinone"
        ]
    },
    'bundesliga': {
        'nombre': 'Bundesliga',
        'equipos': [
            "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen",
            "Union Berlin", "Freiburg", "Wolfsburg", "Eintracht Frankfurt",
            "Mainz 05", "Borussia M'gladbach", "Köln", "Augsburg",
            "Werder Bremen", "Bochum", "Stuttgart", "Heidenheim",
            "Darmstadt 98", "Hoffenheim"
        ]
    },
    'ligue_1': {
        'nombre': 'Ligue 1',
        'equipos': [
            "PSG", "Marseille", "Lyon", "Monaco",
            "Lille", "Rennes", "Nice", "Lens",
            "Reims", "Montpellier", "Toulouse", "Strasbourg",
            "Nantes", "Brest", "Le Havre", "Metz",
            "Lorient", "Clermont Foot"
        ]
    },
    'champions': {
        'nombre': 'Champions League',
        'equipos': [
            "Real Madrid", "Manchester City", "Bayern Munich", "PSG",
            "FC Barcelona", "Juventus", "Liverpool", "Chelsea",
            "AC Milan", "Inter Milan", "Atlético Madrid", "Borussia Dortmund",
            "Arsenal", "Napoli", "Benfica", "Porto",
            "Ajax", "PSV", "Celtic", "Shakhtar Donetsk"
        ]
    }
}

@bp.route('/ligas', methods=['GET'])
@login_required
def obtener_ligas():
    """Obtener lista de ligas disponibles"""
    ligas_info = []
    for key, liga in LIGAS_EQUIPOS.items():
        ligas_info.append({
            'id': key,
            'nombre': liga['nombre'],
            'equipos_count': len(liga['equipos'])
        })
    
    return jsonify({'ligas': ligas_info})

@bp.route('/generar-partidos', methods=['POST'])
@login_required
def generar_partidos():
    """Generar partidos aleatorios para una liga específica"""
    try:
        data = request.get_json()
        liga_id = data.get('liga', 'espana')
        num_partidos = int(data.get('partidos', 15))
        
        if liga_id not in LIGAS_EQUIPOS:
            return jsonify({'error': 'Liga no encontrada'}), 400
        
        liga = LIGAS_EQUIPOS[liga_id]
        equipos = liga['equipos'].copy()
        random.shuffle(equipos)  # Mezclar equipos para emparejamientos aleatorios
        
        partidos = []
        for i in range(0, min(num_partidos * 2, len(equipos)), 2):
            if i + 1 < len(equipos):
                partidos.append({
                    'local': equipos[i],
                    'visitante': equipos[i + 1]
                })
        
        # Si no hay suficientes equipos, generar partidos adicionales
        while len(partidos) < num_partidos:
            local = random.choice(equipos)
            visitante = random.choice([e for e in equipos if e != local])
            partidos.append({
                'local': local,
                'visitante': visitante
            })
        
        return jsonify({
            'partidos': partidos[:num_partidos],
            'liga': liga['nombre'],
            'total_partidos': len(partidos[:num_partidos])
        })
        
    except Exception as e:
        return jsonify({'error': f'Error generando partidos: {str(e)}'}), 500

@bp.route('/apostar', methods=['POST'])
@login_required
def apostar():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
            
        cantidad = float(data['cantidad'])
        pronosticos = data['pronosticos']  # Array de pronósticos [1, X, 2, ...]
        partidos_data = data['partidos']   # Datos de los partidos
        
        # Verificar fondos
        if cantidad > current_user.balance:
            return jsonify({'error': 'Fondos insuficientes'}), 400
        
        # Generar resultados reales aleatorios
        resultados_reales = generar_resultados_reales(len(pronosticos))
        
        # Calcular aciertos y ganancia
        aciertos = calcular_aciertos(pronosticos, resultados_reales)
        ganancia = calcular_ganancia(aciertos, len(pronosticos), cantidad)
        
        # Actualizar balance
        current_user.balance = current_user.balance - cantidad + ganancia
        
        # Registrar apuesta
        apuesta = Apuesta(
            user_id=current_user.id,
            juego='quiniela',
            tipo_juego='singleplayer',
            cantidad=cantidad,
            resultado=f"{aciertos}/{len(pronosticos)} aciertos",
            ganancia=ganancia
        )
        db.session.add(apuesta)
        
        # Actualizar estadísticas
        stats = Estadistica.query.filter_by(user_id=current_user.id, juego='quiniela').first()
        if not stats:
            stats = Estadistica(
                user_id=current_user.id, 
                juego='quiniela',
                tipo_juego='singleplayer',
                partidas_jugadas=0,
                partidas_ganadas=0,
                ganancia_total=0.0,
                apuesta_total=0.0
            )
            db.session.add(stats)
        
        stats.partidas_jugadas += 1
        stats.apuesta_total += cantidad
        stats.ganancia_total += ganancia
        
        if ganancia > cantidad:
            stats.partidas_ganadas += 1
        
        db.session.commit()
        
        return jsonify({
            'nuevo_balance': current_user.balance,
            'aciertos': aciertos,
            'total_partidos': len(pronosticos),
            'resultados_reales': resultados_reales,
            'ganancia': ganancia,
            'mensaje': f'Quiniela: {aciertos}/{len(pronosticos)} aciertos'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

def generar_resultados_reales(num_partidos):
    """Genera resultados aleatorios para los partidos"""
    resultados = []
    for _ in range(num_partidos):
        rand = random.random()
        if rand < 0.45:  # 45% probabilidad de victoria local
            resultados.append('1')
        elif rand < 0.80:  # 35% probabilidad de empate
            resultados.append('X')
        else:  # 20% probabilidad de victoria visitante
            resultados.append('2')
    return resultados

def calcular_aciertos(pronosticos, resultados):
    """Calcula cuántos aciertos hay"""
    return sum(1 for p, r in zip(pronosticos, resultados) if p == r)

def calcular_ganancia(aciertos, total_partidos, apuesta):
    """Calcula la ganancia basada en los aciertos"""
    if aciertos == total_partidos:  # Pleno
        return apuesta * 50
    elif aciertos >= total_partidos - 1:  # 1 fallo
        return apuesta * 20
    elif aciertos >= total_partidos - 2:  # 2 fallos
        return apuesta * 10
    elif aciertos >= total_partidos - 3:  # 3 fallos
        return apuesta * 5
    elif aciertos >= total_partidos - 4:  # 4 fallos
        return apuesta * 3
    elif aciertos >= total_partidos - 5:  # 5 fallos
        return apuesta * 2
    else:
        return 0