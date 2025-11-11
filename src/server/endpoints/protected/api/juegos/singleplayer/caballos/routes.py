from flask import request, jsonify, Blueprint
from flask_login import login_required, current_user
from models import db, Apuesta, Estadistica
import random

bp = Blueprint('api_caballos', __name__, url_prefix='/api/caballos')

# Configuración que coincide con tu HTML
CABALLOS = {
    1: { 
        'id': 1,
        'nombre': 'Relámpago', 
        'multiplicador': 1.5, 
        'velocidad': 0.85, 
        'resistencia': 0.70,
        'emoji': '🐎'
    },
    2: { 
        'id': 2,
        'nombre': 'Trueno', 
        'multiplicador': 2.0, 
        'velocidad': 0.75, 
        'resistencia': 0.80,
        'emoji': '🐴'
    },
    3: { 
        'id': 3,
        'nombre': 'Centella', 
        'multiplicador': 3.0, 
        'velocidad': 0.65, 
        'resistencia': 0.85,
        'emoji': '🏇'
    },
    4: { 
        'id': 4,
        'nombre': 'Azabache', 
        'multiplicador': 6.0, 
        'velocidad': 0.45, 
        'resistencia': 0.95,
        'emoji': '🎠'
    }
}

@bp.route('/apostar', methods=['POST'])
@login_required
def apostar():
    try:
        print("🔍 Iniciando procesamiento de apuesta de caballos...")
        
        data = request.get_json()
        print(f"🔍 Datos recibidos: {data}")
        
        if not data:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
            
        # Obtener datos EXACTAMENTE como los envía tu frontend
        cantidad = data.get('cantidad')
        resultado = data.get('resultado')  # 'ganada' o 'perdida'
        ganancia = data.get('ganancia')
        caballo_apostado = data.get('caballo_apostado')  # ID del caballo
        caballo_ganador = data.get('caballo_ganador')    # ID del caballo ganador
        
        print(f"🔍 Procesando: cantidad={cantidad}, resultado={resultado}, ganancia={ganancia}")
        
        # Validaciones
        if cantidad is None:
            return jsonify({'error': 'Falta la cantidad'}), 400
            
        try:
            cantidad = float(cantidad)
            ganancia = float(ganancia) if ganancia is not None else 0.0
            caballo_apostado = int(caballo_apostado) if caballo_apostado else None
            caballo_ganador = int(caballo_ganador) if caballo_ganador else None
        except (ValueError, TypeError) as e:
            print(f"❌ Error en conversión de datos: {e}")
            return jsonify({'error': 'Datos inválidos'}), 400
        
        if cantidad <= 0:
            return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
            
        if cantidad > current_user.balance:
            return jsonify({'error': 'Fondos insuficientes'}), 400
        
        #  Verificar que el caballo apostado existe
        if caballo_apostado not in CABALLOS:
            return jsonify({'error': 'Caballo apostado no válido'}), 400
            
        #  Verificar que el caballo ganador existe (si se proporciona)
        if caballo_ganador and caballo_ganador not in CABALLOS:
            return jsonify({'error': 'Caballo ganador no válido'}), 400
        
        print(f"🔍 Validaciones pasadas. Actualizando balance...")
        
        #  Actualizar balance del usuario
        balance_anterior = current_user.balance
        current_user.balance = current_user.balance - cantidad + ganancia
        print(f"🔍 Balance actualizado: {balance_anterior} -> {current_user.balance}")
        
        #  Registrar apuesta
        apuesta = Apuesta(
            user_id=current_user.id,
            juego='caballos',
            cantidad=cantidad,
            resultado=resultado,
            ganancia=ganancia
        )
        db.session.add(apuesta)
        print("🔍 Apuesta registrada")
        
        #  Manejar estadísticas de forma CORRECTA
        stats = Estadistica.query.filter_by(user_id=current_user.id, juego='caballos').first()
        
        if stats:
            print("🔍 Estadísticas existentes encontradas")
            # Si existen estadísticas, usar valores por defecto si son None
            partidas_jugadas = stats.partidas_jugadas if stats.partidas_jugadas is not None else 0
            partidas_ganadas = stats.partidas_ganadas if stats.partidas_ganadas is not None else 0
            ganancia_total = stats.ganancia_total if stats.ganancia_total is not None else 0.0
            apuesta_total = stats.apuesta_total if stats.apuesta_total is not None else 0.0
            
            stats.partidas_jugadas = partidas_jugadas + 1
            if resultado == 'ganada':
                stats.partidas_ganadas = partidas_ganadas + 1
            # ✅ CORRECCIÓN: ganancia_total debe sumar la ganancia bruta, no neta
            stats.ganancia_total = ganancia_total + ganancia
            stats.apuesta_total = apuesta_total + cantidad
            
            print(f"🔍 Estadísticas actualizadas: PJ={stats.partidas_jugadas}, PG={stats.partidas_ganadas}, GananciaTotal={stats.ganancia_total}, ApuestaTotal={stats.apuesta_total}")
        else:
            print("🔍 Creando nuevas estadísticas")
            # Crear nuevas estadísticas
            stats = Estadistica(
                user_id=current_user.id, 
                juego='caballos',
                partidas_jugadas=1,
                partidas_ganadas=1 if resultado == 'ganada' else 0,
                # ✅ CORRECCIÓN: ganancia_total debe ser la ganancia bruta
                ganancia_total=ganancia,
                apuesta_total=cantidad
            )
            db.session.add(stats)
        
        #  Hacer commit
        db.session.commit()
        print("✅ Commit exitoso")
        
        #  Preparar respuesta
        respuesta = {
            'resultado': resultado,
            'ganancia': ganancia,
            'nuevo_balance': current_user.balance
        }
        
        #  Añadir información de caballos si está disponible
        if caballo_apostado:
            respuesta['caballo_apostado'] = CABALLOS[caballo_apostado]
        if caballo_ganador:
            respuesta['caballo_ganador'] = CABALLOS[caballo_ganador]
            
        print(f"✅ Enviando respuesta: {respuesta}")
        
        return jsonify(respuesta)
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ ERROR CRÍTICO: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error al procesar la apuesta: {str(e)}'}), 500