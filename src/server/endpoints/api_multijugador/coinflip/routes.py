from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from models import db, SalaMultijugador, UsuarioSala

bp = Blueprint('api_multijugador_coinflip', __name__)

# Importar y registrar los socket handlers cuando se carga este blueprint
from .socket_handlers import register_coinflip_handlers
from flask import current_app

bp = Blueprint('api_multijugador_coinflip', __name__)

# Esta función se ejecutará cuando el blueprint se registre
@bp.record_once
def on_register(state):
    socketio = state.app.extensions.get('socketio')
    if socketio:
        # ⚠️ PASA LA APLICACIÓN AL HANDLER
        register_coinflip_handlers(socketio, state.app)
        print("✅ Handlers de CoinFlip registrados desde blueprint")
    else:
        print("❌ SocketIO no encontrado al registrar CoinFlip handlers")

@bp.route('/api/multijugador/coinflip/sala/<int:sala_id>')
@login_required
def sala_coinflip(sala_id):
    """Página principal del CoinFlip multijugador"""
    print(f"🎮 Accediendo a sala CoinFlip {sala_id} para usuario {current_user.username}")
    
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    # Verificar que el usuario está en la sala y que está jugando
    usuario_en_sala = UsuarioSala.query.filter_by(
        usuario_id=current_user.id, 
        sala_id=sala_id
    ).first()
    
    if not usuario_en_sala:
        print(f"❌ Usuario {current_user.username} no está en la sala {sala_id}")
        return redirect(url_for('salas_espera.lobby'))
    
    if sala.estado != 'jugando':
        print(f"❌ Sala {sala_id} no está en estado 'jugando' (está: {sala.estado})")
        return redirect(url_for('salas_espera.lobby'))
    
    print(f"✅ Renderizando CoinFlip multijugador para {current_user.username}")
    return render_template('juegos_multijugador/coinflip_multijugador.html', 
                         sala=sala, user=current_user)

@bp.route('/apostar/<int:sala_id>', methods=['POST'])
@login_required
def apostar(sala_id):
    """Procesar apuesta en CoinFlip multijugador"""
    data = request.get_json()
    
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    # Verificar que el usuario está en la sala
    usuario_en_sala = UsuarioSala.query.filter_by(
        usuario_id=current_user.id, 
        sala_id=sala_id
    ).first()
    
    if not usuario_en_sala:
        return jsonify({'error': 'No estás en esta sala'}), 403
    
    try:
        cantidad = float(data.get('cantidad', 0))
        eleccion = data.get('eleccion')  # 'cara' o 'cruz'
    except (TypeError, ValueError):
        return jsonify({"error": "Datos inválidos"}), 400

    # Validaciones
    if cantidad <= 0 or eleccion not in ['cara', 'cruz']:
        return jsonify({"error": "Parámetros incorrectos"}), 400

    if current_user.balance < cantidad:
        return jsonify({"error": "Fondos insuficientes"}), 400

    # Restar la apuesta
    current_user.balance -= cantidad

    # Crear registro de la apuesta (resultado pendiente)
    apuesta = Apuesta(
        user_id=current_user.id,
        juego='coinflip_multijugador',
        cantidad=cantidad,
        resultado='pendiente',
        ganancia=0.0
    )
    
    db.session.add(apuesta)
    db.session.commit()

    # Emitir evento a la sala
    emit('nueva_apuesta', {
        'usuario_id': current_user.id,
        'username': current_user.username,
        'eleccion': eleccion,
        'cantidad': cantidad,
        'apuesta_id': apuesta.id
    }, room=f'coinflip_sala_{sala_id}')

    return jsonify({
        'success': True,
        'apuesta_id': apuesta.id,
        'nuevo_balance': current_user.balance
    })

@bp.route('/lanzar/<int:sala_id>', methods=['POST'])
@login_required
def lanzar_moneda(sala_id):
    """Lanzar la moneda (solo el creador puede lanzar)"""
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    # Solo el creador puede lanzar
    if sala.creador_id != current_user.id:
        return jsonify({'error': 'Solo el creador puede lanzar la moneda'}), 403
    
    # Generar resultado aleatorio
    resultado = random.choice(['cara', 'cruz'])
    
    # Emitir resultado a todos en la sala
    emit('resultado_moneda', {
        'resultado': resultado,
        'lanzador': current_user.username,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f'coinflip_sala_{sala_id}')
    
    return jsonify({
        'success': True,
        'resultado': resultado
    })

@bp.route('/procesar-resultados/<int:sala_id>', methods=['POST'])
@login_required
def procesar_resultados(sala_id):
    """Procesar resultados después del lanzamiento"""
    data = request.get_json()
    resultado = data.get('resultado')
    
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    # Obtener todas las apuestas pendientes de esta sala
    # (En una implementación real, necesitarías relacionar apuestas con sala)
    apuestas_pendientes = Apuesta.query.filter_by(
        juego='coinflip_multijugador', 
        resultado='pendiente'
    ).all()
    
    resultados = []
    
    for apuesta in apuestas_pendientes:
        gano = (apuesta.user.eleccion == resultado)  # Necesitarías almacenar la elección
        ganancia = apuesta.cantidad * 2 if gano else 0
        
        if gano:
            apuesta.user.balance += ganancia
        
        apuesta.ganancia = ganancia
        apuesta.resultado = 'ganada' if gano else 'perdida'
        
        resultados.append({
            'usuario_id': apuesta.user.id,
            'username': apuesta.user.username,
            'gano': gano,
            'ganancia': ganancia,
            'nuevo_balance': apuesta.user.balance
        })
    
    db.session.commit()
    
    # Emitir resultados
    emit('resultados_finales_coinflip', {
        'resultados': resultados,
        'resultado_moneda': resultado
    }, room=f'coinflip_sala_{sala_id}')
    
    # ⚠️ IMPORTANTE: Resetear para nueva ronda
    salas_coinflip[sala_id]['apuestas'] = []
    salas_coinflip[sala_id]['estado'] = 'esperando'
    
    # Emitir estado actualizado
    emit('estado_sala_actualizado', {
        'sala_id': sala_id,
        'jugadores': salas_coinflip[sala_id]['jugadores'],
        'apuestas': salas_coinflip[sala_id]['apuestas'],  # ← Vacías
        'estado': salas_coinflip[sala_id]['estado']       # ← 'esperando'
    }, room=f'coinflip_sala_{sala_id}')
    
    return jsonify({
        'success': True,
        'resultados': resultados
    })