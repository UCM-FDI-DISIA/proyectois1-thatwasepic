from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room, emit
from models import db, SalaMultijugador, UsuarioSala, User, Apuesta, Estadistica
from datetime import datetime
import random
import time

# Diccionario para rastrear jugadores por sala
salas_coinflip = {}

def register_coinflip_handlers(socketio, app):
    print("✅ Registrando handlers de CoinFlip multijugador")
    
    @socketio.on('connect')
    def handle_connect_coinflip():
        if current_user.is_authenticated:
            print(f"🎮 Usuario {current_user.username} conectado a CoinFlip")
    
    @socketio.on('join_coinflip_room')
    def handle_join_coinflip_room(data):
        if not current_user.is_authenticated:
            print("❌ Usuario no autenticado intentando unirse a CoinFlip")
            return
        
        sala_id = data.get('sala_id')
        print(f"🎯 Usuario {current_user.username} uniéndose a sala CoinFlip {sala_id}")
        
        sala = SalaMultijugador.query.get(sala_id)
        
        if sala and sala.juego == 'coinflip':
            join_room(f'coinflip_sala_{sala_id}')
            
            # Inicializar sala si no existe
            if sala_id not in salas_coinflip:
                salas_coinflip[sala_id] = {
                    'jugadores': [],
                    'apuestas': [],
                    'estado': 'esperando'
                }
                print(f"🏠 Nueva sala CoinFlip creada: {sala_id}")
            
            # Agregar jugador si no está
            jugador_existente = next((j for j in salas_coinflip[sala_id]['jugadores'] if j['id'] == current_user.id), None)
            if not jugador_existente:
                salas_coinflip[sala_id]['jugadores'].append({
                    'id': current_user.id,
                    'username': current_user.username,
                    'es_creador': (sala.creador_id == current_user.id),
                    'balance': current_user.balance
                })
                print(f"👤 Jugador {current_user.username} agregado a sala {sala_id}")
            
            # Emitir estado actual a todos
            emit('estado_sala_actualizado', {
                'sala_id': sala_id,
                'jugadores': salas_coinflip[sala_id]['jugadores'],
                'apuestas': salas_coinflip[sala_id]['apuestas'],
                'estado': salas_coinflip[sala_id]['estado']
            }, room=f'coinflip_sala_{sala_id}')
            
            emit('user_joined_coinflip', {
                'user_id': current_user.id,
                'username': current_user.username,
                'sala_id': sala_id
            }, room=f'coinflip_sala_{sala_id}')
            
            print(f"✅ {current_user.username} unido exitosamente a sala CoinFlip {sala_id}")
        else:
            print(f"❌ Sala {sala_id} no encontrada o no es CoinFlip")

    @socketio.on('leave_coinflip_room')
    def handle_leave_coinflip_room(data):
        if not current_user.is_authenticated:
            return
        
        sala_id = data.get('sala_id')
        print(f"🚪 Usuario {current_user.username} saliendo de sala CoinFlip {sala_id}")
        
        leave_room(f'coinflip_sala_{sala_id}')
        
        # Remover jugador de la sala
        if sala_id in salas_coinflip:
            salas_coinflip[sala_id]['jugadores'] = [
                j for j in salas_coinflip[sala_id]['jugadores'] 
                if j['id'] != current_user.id
            ]
            salas_coinflip[sala_id]['apuestas'] = [
                a for a in salas_coinflip[sala_id]['apuestas']
                if a['usuario_id'] != current_user.id
            ]
        
        emit('user_left_coinflip', {
            'user_id': current_user.id,
            'username': current_user.username
        }, room=f'coinflip_sala_{sala_id}')

    @socketio.on('coinflip_apostar')
    def handle_coinflip_apostar(data):
        print("💰 Recibiendo apuesta CoinFlip:", data)
        
        sala_id = data.get('sala_id')
        cantidad = float(data.get('cantidad', 0))
        eleccion = data.get('eleccion')
        
        if sala_id not in salas_coinflip:
            print(f"❌ Sala {sala_id} no encontrada para apuesta")
            return
        
        # Verificar fondos del usuario
        if current_user.balance < cantidad:
            emit('error_apuesta', {
                'message': 'Fondos insuficientes'
            }, room=request.sid)
            return
        
        # Restar apuesta del balance
        current_user.balance -= cantidad
        db.session.commit()
        
        # Verificar si el usuario ya apostó
        apuesta_existente = next(
            (a for a in salas_coinflip[sala_id]['apuestas'] 
             if a['usuario_id'] == current_user.id), 
            None
        )
        
        if apuesta_existente:
            # Actualizar apuesta existente
            apuesta_existente['cantidad'] = cantidad
            apuesta_existente['eleccion'] = eleccion
            print(f"📝 Apuesta actualizada para {current_user.username}")
        else:
            # Crear nueva apuesta
            salas_coinflip[sala_id]['apuestas'].append({
                'usuario_id': current_user.id,
                'username': current_user.username,
                'eleccion': eleccion,
                'cantidad': cantidad,
                'timestamp': datetime.utcnow().isoformat()
            })
            print(f"✅ Nueva apuesta de {current_user.username}: ${cantidad} por {eleccion}")
        
        # Emitir evento de nueva apuesta
        emit('nueva_apuesta_coinflip', {
            'usuario_id': current_user.id,
            'username': current_user.username,
            'eleccion': eleccion,
            'cantidad': cantidad,
            'apuestas_totales': len(salas_coinflip[sala_id]['apuestas'])
        }, room=f'coinflip_sala_{sala_id}')
        
        # Emitir estado actualizado
        emit('estado_sala_actualizado', {
            'sala_id': sala_id,
            'jugadores': salas_coinflip[sala_id]['jugadores'],
            'apuestas': salas_coinflip[sala_id]['apuestas'],
            'estado': salas_coinflip[sala_id]['estado']
        }, room=f'coinflip_sala_{sala_id}')
        
        print(f"📊 Apuestas en sala {sala_id}: {len(salas_coinflip[sala_id]['apuestas'])}")

    @socketio.on('coinflip_lanzar')
    def handle_coinflip_lanzar(data):
        print("🎯 Recibiendo solicitud de lanzamiento:", data)
        
        sala_id = data.get('sala_id')
        sala = SalaMultijugador.query.get(sala_id)
        
        # Verificar que es el creador
        if not sala or sala.creador_id != current_user.id:
            print(f"❌ {current_user.username} no es el creador de la sala")
            emit('error_lanzamiento', {
                'message': 'Solo el creador puede lanzar la moneda'
            }, room=request.sid)
            return
        
        if sala_id not in salas_coinflip:
            print(f"❌ Sala {sala_id} no encontrada")
            return
        
        if len(salas_coinflip[sala_id]['apuestas']) == 0:
            print(f"❌ No hay apuestas en la sala {sala_id}")
            emit('error_lanzamiento', {
                'message': 'No hay apuestas para lanzar la moneda'
            }, room=request.sid)
            return
        
        # Cambiar estado a "lanzando"
        salas_coinflip[sala_id]['estado'] = 'lanzando'
        
        resultado = random.choice(['cara', 'cruz'])
        print(f"🎲 Resultado del lanzamiento: {resultado}")
        
        emit('moneda_lanzada', {
            'resultado': resultado,
            'lanzador': current_user.username,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'coinflip_sala_{sala_id}')
        
        # Procesar resultados después de 3 segundos
        def procesar_resultados_background():
            print("⏳ Esperando 3 segundos antes de procesar resultados...")
            time.sleep(3)
            
            print(f"🏁 Procesando resultados para sala {sala_id}")
            
            # Usar el contexto de la aplicación
            with app.app_context():
                resultados = []
                
                for apuesta in salas_coinflip[sala_id]['apuestas']:
                    gano = apuesta['eleccion'] == resultado
                    ganancia = apuesta['cantidad'] * 2 if gano else 0
                    
                    # Actualizar balance del usuario en la base de datos
                    usuario = User.query.get(apuesta['usuario_id'])
                    if usuario:
                        if gano:
                            usuario.balance += ganancia
                            print(f"🎉 {usuario.username} ganó ${ganancia}")
                        else:
                            print(f"😢 {usuario.username} perdió ${apuesta['cantidad']}")
                        
                        # Registrar apuesta en base de datos
                        apuesta_db = Apuesta(
                            user_id=usuario.id,
                            juego='coinflip_multijugador',
                            cantidad=apuesta['cantidad'],
                            ganancia=ganancia,
                            resultado='ganada' if gano else 'perdida'
                        )
                        db.session.add(apuesta_db)
                        
                        # Actualizar estadísticas
                        stats = Estadistica.query.filter_by(user_id=usuario.id, juego='coinflip').first()
                        if not stats:
                            stats = Estadistica(
                                user_id=usuario.id, 
                                juego='coinflip',
                                partidas_jugadas=0,
                                partidas_ganadas=0,
                                ganancia_total=0.0,
                                apuesta_total=0.0
                            )
                            db.session.add(stats)
                        
                        stats.partidas_jugadas += 1
                        stats.apuesta_total += apuesta['cantidad']
                        stats.ganancia_total += ganancia
                        
                        if ganancia > apuesta['cantidad']:
                            stats.partidas_ganadas += 1
                        
                        resultados.append({
                            'usuario_id': usuario.id,
                            'username': usuario.username,
                            'gano': gano,
                            'cantidad_apostada': apuesta['cantidad'],
                            'ganancia': ganancia,
                            'nuevo_balance': usuario.balance
                        })
                
                # Guardar cambios en la base de datos
                db.session.commit()
                
                # Emitir resultados
                socketio.emit('resultados_finales_coinflip', {
                    'resultados': resultados,
                    'resultado_moneda': resultado
                }, room=f'coinflip_sala_{sala_id}')
                
                # Resetear apuestas para la siguiente ronda
                salas_coinflip[sala_id]['apuestas'] = []
                salas_coinflip[sala_id]['estado'] = 'esperando'
                
                # Emitir estado actualizado
                socketio.emit('estado_sala_actualizado', {
                    'sala_id': sala_id,
                    'jugadores': salas_coinflip[sala_id]['jugadores'],
                    'apuestas': salas_coinflip[sala_id]['apuestas'],
                    'estado': salas_coinflip[sala_id]['estado']
                }, room=f'coinflip_sala_{sala_id}')
                
                print(f"✅ Resultados procesados para sala {sala_id}")
        
        socketio.start_background_task(procesar_resultados_background)

    @socketio.on('coinflip_chat_message')
    def handle_coinflip_chat(data):
        print("💬 Mensaje de chat recibido:", data)
        
        sala_id = data.get('sala_id')
        message = data.get('message')
        
        emit('new_coinflip_message', {
            'user_id': current_user.id,
            'username': current_user.username,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'coinflip_sala_{sala_id}')

    print("✅ Todos los handlers de CoinFlip registrados correctamente")