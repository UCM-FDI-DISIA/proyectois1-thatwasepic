from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room, emit
from models import db, SalaMultijugador, UsuarioSala, User, Apuesta, Estadistica
from datetime import datetime
import random, time
import threading

# Estado en memoria por sala para la ruleta multijugador
salas_ruleta = {}
# Paleta de colores disponibles
AVAILABLE_COLORS = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3', '#F38181', '#A8EDEA']

def register_ruleta_handlers(socketio, app):
    print("✅ Registrando handlers de Ruleta multijugador")

    # --- Helpers for countdown and performing the spin (to reuse from handlers) ---
    def perform_spin(sala_id):
        st = salas_ruleta.setdefault(sala_id, {'jugadores': [], 'estado': 'esperando', 'apuestas': []})
        room_name = f'ruleta_sala_{sala_id}'
        # Guardar y resetear flags de countdown
        st['spin_countdown_cancel'] = True
        st['countdown_thread'] = None

        # realizar giro (mismo algoritmo que antes)
        result_number = random.randint(0,36)
        REDS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        PAYOUT = {'straight':35,'split':17,'street':11,'corner':8,'line':5,'dozen':2,'column':2,'even':1}

        results = []
        for a in st.get('apuestas', []):
            inner_bets = a.get('bets', [])
            total_bet_cents = 0
            total_win_cents = 0
            total_returned_cents = 0
            for bet in inner_bets:
                tipo = bet.get('type')
                cantidad = int(bet.get('amount',0))
                numeros = set(bet.get('set',[]))
                label = bet.get('label','').lower()
                total_bet_cents += cantidad
                gana = False
                if tipo == 'even':
                    if ('rojo' in label and result_number in REDS) \
                    or ('negro' in label and result_number not in REDS and result_number != 0) \
                    or ('par' in label and result_number % 2 == 0 and result_number != 0) \
                    or ('impar' in label and result_number % 2 == 1) \
                    or ('1-18' in label and 1 <= result_number <= 18) \
                    or ('19-36' in label and 19 <= result_number <= 36):
                        gana = True
                elif result_number in numeros:
                    gana = True
                if gana:
                    total_win_cents += cantidad * PAYOUT.get(tipo,0)
                    total_returned_cents += cantidad

            total_bet_euros = total_bet_cents / 100.0
            total_win_euros = total_win_cents / 100.0
            total_returned_euros = total_returned_cents / 100.0
            total_payout_euros = total_win_euros + total_returned_euros

            user = User.query.get(a['usuario_id'])
            if user:
                user.balance += total_payout_euros
            apuesta_db = Apuesta.query.filter_by(user_id=a['usuario_id'], juego='ruleta', resultado='PENDIENTE').order_by(Apuesta.id.desc()).first()
            if apuesta_db:
                apuesta_db.ganancia = total_win_euros
                apuesta_db.resultado = f'Número {result_number} - Ganancia: {total_win_euros:.2f}€'
            stats = Estadistica.query.filter_by(user_id=a['usuario_id'], juego='ruleta').first()
            if not stats:
                stats = Estadistica(user_id=a['usuario_id'], juego='ruleta', partidas_jugadas=0, partidas_ganadas=0, ganancia_total=0.0, apuesta_total=0.0)
                db.session.add(stats)
            stats.partidas_jugadas += 1
            stats.apuesta_total += total_bet_euros
            stats.ganancia_total += total_win_euros
            if total_win_euros > 0:
                stats.partidas_ganadas += 1

            results.append({
                'usuario_id': a['usuario_id'],
                'username': (User.query.get(a['usuario_id']).username) if User.query.get(a['usuario_id']) else None,
                'bet_total_euros': total_bet_euros,
                'win_euros': total_win_euros,
                'payout_euros': total_payout_euros,
                'nuevo_balance': User.query.get(a['usuario_id']).balance if User.query.get(a['usuario_id']) else None
            })

        # commit DB
        db.session.commit()

        # actualizar balances en el estado en memoria (jugadores)
        uid_to_newbal = {r['usuario_id']: r.get('nuevo_balance') for r in results}
        for j in st.get('jugadores', []):
            if j['id'] in uid_to_newbal and uid_to_newbal[j['id']] is not None:
                # nuevo_balance viene en euros (float)
                j['balance'] = uid_to_newbal[j['id']]

        # preparar mensaje resumen para el chat y el log
        try:
            summary_parts = []
            for r in results:
                uname = r.get('username') or f"Usuario {r.get('usuario_id')}"
                win = r.get('win_euros', 0.0)
                payout = r.get('payout_euros', 0.0)
                part = f"{uname}: ganancia {win:.2f}€, total recibido {payout:.2f}€"
                summary_parts.append(part)
            summary_msg = f"Resultado: {result_number}. " + " | ".join(summary_parts) if summary_parts else f"Resultado: {result_number}."
            # emitir mensaje de chat local para que todos lo vean
            socketio.emit('new_ruleta_message', {'user_id': None, 'username': 'Sistema', 'message': summary_msg, 'timestamp': datetime.utcnow().isoformat()}, room=room_name)
        except Exception:
            pass

        # limpiar estado y notificar: borrar apuestas pero mantener el mapa de colores
        st['apuestas'] = []
        for j in st.get('jugadores', []):
            j['ready'] = False
        st['estado'] = 'esperando'

        # emitir evento con resultado y lista de resultados detallados
        socketio.emit('ruleta_girada', {'result': result_number, 'results': results}, room=room_name)
        socketio.emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)

    def start_spin_countdown(sala_id, seconds=15):
        st = salas_ruleta.setdefault(sala_id, {'jugadores': [], 'estado': 'esperando', 'apuestas': []})
        if st.get('countdown_thread'):
            return
        st['spin_countdown_cancel'] = False

        def runner():
            remaining = seconds
            room_name = f'ruleta_sala_{sala_id}'
            while remaining >= 0 and not st.get('spin_countdown_cancel'):
                try:
                    socketio.emit('spin_countdown', {'seconds_remaining': remaining}, room=room_name)
                except Exception:
                    pass
                if remaining == 0:
                    # trigger auto-spin
                    try:
                        perform_spin(sala_id)
                    except Exception as e:
                        print('Error performing auto spin:', e)
                    break
                # use socketio.sleep for compatibility with different async modes
                try:
                    socketio.sleep(1)
                except Exception:
                    time.sleep(1)
                remaining -= 1
            st['countdown_thread'] = None

        # start background task via socketio to be compatible with eventlet/gevent
        try:
            st['countdown_thread'] = socketio.start_background_task(runner)
        except Exception:
            # fallback to threading
            th = threading.Thread(target=runner, daemon=True)
            st['countdown_thread'] = th
            th.start()

    @socketio.on('connect')
    def handle_connect():
        if current_user.is_authenticated:
            print(f"🔗 Usuario {current_user.username} conectado a Ruleta (SID: {request.sid})")

    @socketio.on('join_ruleta_room')
    def handle_join(data):
        if not current_user.is_authenticated:
            return
        sala_id = data.get('sala_id')
        sala = SalaMultijugador.query.get(sala_id)
        if not sala or sala.juego != 'ruleta':
            emit('error', {'message': 'Sala no encontrada o juego incorrecto'}, room=request.sid)
            return

        room_name = f'ruleta_sala_{sala_id}'
        join_room(room_name)

        # inicializar estado en memoria si hace falta
        st = salas_ruleta.setdefault(sala_id, {'jugadores': [], 'estado': 'esperando', 'apuestas': []})

        # añadir jugador si no está
        if not any(j['id'] == current_user.id for j in st['jugadores']):
            st['jugadores'].append({'id': current_user.id, 'username': current_user.username, 'balance': current_user.balance, 'ready': False})

        # asignar color fijo automáticamente si no tiene uno
        if 'color_map' not in st:
            st['color_map'] = {}
        # compute available color
        assigned = set(st['color_map'].values())
        available = [c for c in AVAILABLE_COLORS if c not in assigned]
        if current_user.id not in st['color_map']:
            chosen = available[0] if available else AVAILABLE_COLORS[0]
            st['color_map'][current_user.id] = chosen

        # emitir colores actuales junto con estado para que clientes conozcan su color
        colors_list = [{'usuario_id': uid, 'color': col} for uid, col in st['color_map'].items()]
        emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)
        emit('players_colors_update', {'colors': colors_list, 'jugadores': st['jugadores']}, room=room_name)
        emit('user_joined_ruleta', {'user_id': current_user.id, 'username': current_user.username}, room=room_name)

    @socketio.on('cambiar_color')
    def handle_cambiar_color(data):
        if not current_user.is_authenticated:
            return
        sala_id = data.get('sala_id')
        color = data.get('color')
        
        if color not in AVAILABLE_COLORS:
            emit('error', {'message': 'Color inválido'}, room=request.sid)
            return
        
        st = salas_ruleta.get(sala_id)
        if not st:
            emit('error', {'message': 'Sala no encontrada'}, room=request.sid)
            return
        
        room_name = f'ruleta_sala_{sala_id}'
        
        # Inicializar color_map si no existe
        if 'color_map' not in st:
            st['color_map'] = {}
        
        # Validar que el color no esté usado por otro jugador
        for user_id, user_color in st['color_map'].items():
            if user_id != current_user.id and user_color == color:
                emit('error', {'message': 'Color ya está siendo usado'}, room=request.sid)
                return
        
        # Asignar color
        st['color_map'][current_user.id] = color
        
        # Broadcast actualizado de colores y jugadores
        colors_list = [
            {'usuario_id': uid, 'color': col}
            for uid, col in st['color_map'].items()
        ]
        
        emit('players_colors_update', {
            'colors': colors_list,
            'jugadores': st['jugadores']
        }, room=room_name)

    @socketio.on('leave_ruleta_room')
    def handle_leave(data):
        if not current_user.is_authenticated:
            return
        sala_id = data.get('sala_id')
        room_name = f'ruleta_sala_{sala_id}'
        leave_room(room_name)
        st = salas_ruleta.get(sala_id)
        if st:
            st['jugadores'] = [j for j in st['jugadores'] if j['id'] != current_user.id]
            st['apuestas'] = [a for a in st['apuestas'] if a['usuario_id'] != current_user.id]
            # Limpiar color del mapa
            if 'color_map' in st and current_user.id in st['color_map']:
                del st['color_map'][current_user.id]
            emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)

    @socketio.on('ruleta_place_bet')
    def handle_place(data):
        sala_id = data.get('sala_id')
        apuestas = data.get('apuestas')  # Lista de apuestas del frontend
        if not sala_id or not apuestas:
            emit('error', {'message': 'sala_id y apuestas requeridos'}, room=request.sid)
            return

        sala = SalaMultijugador.query.get(sala_id)
        if not sala:
            emit('error', {'message': 'Sala no encontrada'}, room=request.sid)
            return

        # calcular total desde apuestas (cantidad en céntimos puede venir en 'amount' o 'value')
        total_cents = 0
        for bet in apuestas:
            try:
                total_cents += int(bet.get('amount', bet.get('value', 0)))
            except Exception:
                pass
        total_euros = total_cents / 100.0
        
        if total_euros > current_user.balance:
            emit('error_apuesta', {'message': 'Fondos insuficientes'}, room=request.sid)
            return
        # descontar balance y guardar apuesta en DB y en memoria (secreta)
        current_user.balance -= total_euros
        # crear registro de apuesta en la base de datos para que la vista de estadísticas lo recoja
        apuesta_db = Apuesta(user_id=current_user.id, juego='ruleta', cantidad=total_euros, resultado='PENDIENTE', ganancia=0.0)
        db.session.add(apuesta_db)
        db.session.commit()

        st = salas_ruleta.setdefault(sala_id, {'jugadores': [], 'estado': 'esperando', 'apuestas': []})
        room_name = f'ruleta_sala_{sala_id}'
        # actualizar/apilar la apuesta secreta (no emitir detalles a otros)
        existing = next((a for a in st['apuestas'] if a['usuario_id'] == current_user.id), None)
        if existing:
            existing['bets'] = apuestas
            existing['amount_cents'] = total_cents
            existing['submitted_at'] = datetime.utcnow().isoformat()
            existing['has_spun'] = False
            existing['apuesta_id'] = apuesta_db.id
        else:
            st['apuestas'].append({'usuario_id': current_user.id, 'bets': apuestas, 'amount_cents': total_cents, 'submitted_at': datetime.utcnow().isoformat(), 'has_spun': False, 'apuesta_id': apuesta_db.id})

        print(f"[ruleta] handle_place: usuario={current_user.username} sala={sala_id} total_cents={total_cents} apuestas_count={len(apuestas)}")
        # notificar estado (sin revelar apuestas)
        # incluir resumen para mostrar en el chat/log (etiquetas y total en céntimos)
        labels = [b.get('label') for b in apuestas]
        # incluir bet_id para que el cliente pueda correlacionar con recentBets/estadísticas
        emit('apuesta_recibida', {
            'sala_id': sala_id,
            'user_id': current_user.id,
            'username': current_user.username,
            'bet_id': apuesta_db.id,
            'summary': {'labels': labels, 'amount_cents': total_cents}
        }, room=room_name)
        emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)

    @socketio.on('ruleta_spin')
    def handle_spin(data):
        sala_id = data.get('sala_id')
        force = bool(data.get('force'))
        sala = SalaMultijugador.query.get(sala_id)
        if not sala:
            emit('error', {'message': 'Sala no encontrada'}, room=request.sid)
            return

        st = salas_ruleta.setdefault(sala_id, {'jugadores': [], 'estado': 'esperando', 'apuestas': []})
        room_name = f'ruleta_sala_{sala_id}'
        # marcar ready para el jugador
        for j in st['jugadores']:
            if j['id'] == current_user.id:
                j['ready'] = True
        for a in st['apuestas']:
            if a['usuario_id'] == current_user.id:
                a['has_spun'] = True

        # Aviso a toda la sala de quién ha pedido giro y cuánto lleva apostado
        try:
            my_bet_cents = 0
            for a in st.get('apuestas', []):
                if a.get('usuario_id') == current_user.id:
                    my_bet_cents = a.get('amount_cents', 0)
                    break
            socketio.emit('spin_notice', {
                'sala_id': sala_id,
                'usuario_id': current_user.id,
                'username': current_user.username,
                'bet_cents': my_bet_cents
            }, room=room_name)
        except Exception:
            pass

        # Si se fuerza (countdown agotado), girar sin más siempre que existan apuestas
        if force:
            if not st.get('apuestas'):
                emit('spin_ack', {'ok': False, 'message': 'No hay apuestas en la sala'}, room=request.sid)
                return
            try:
                st['spin_countdown_cancel'] = True
            except Exception:
                pass
            perform_spin(sala_id)
            return

        # chequear si todos los que apostaron están listos o si ya expiró el tiempo
        bettors_ids = {a.get('usuario_id') for a in st.get('apuestas', []) if a.get('usuario_id')}
        total_bettors = len(bettors_ids)
        if total_bettors == 0:
            emit('spin_ack', {'ok': False, 'message': 'Debes tener apuesta para girar'}, room=request.sid)
            return

        ready_count = sum(1 for j in st['jugadores'] if j.get('ready') and j.get('id') in bettors_ids)

        # Si solo hay un apostador, iniciar countdown y dejar que el giro ocurra al expirar
        if total_bettors == 1:
            try:
                if not st.get('countdown_thread'):
                    print(f"[ruleta] iniciando countdown 15s (solo un apostador)")
                    start_spin_countdown(sala_id, seconds=15)
            except Exception as e:
                print('Error starting countdown from spin (1 bettor):', e)
            emit('spin_ack', {'ok': True, 'spun': False, 'players_ready': ready_count, 'players_needed': 2}, room=request.sid)
            emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)
            return

        # Si hay 2+ apostadores pero falta alguno por pulsar, arrancar countdown compartido
        if ready_count < total_bettors:
            try:
                if not st.get('countdown_thread'):
                    print(f"[ruleta] iniciando countdown 15s para sala {sala_id} (faltan jugadores listos)")
                    start_spin_countdown(sala_id, seconds=15)
            except Exception as e:
                print('Error starting countdown from spin:', e)
            emit('spin_ack', {'ok': True, 'spun': False, 'players_ready': ready_count, 'players_needed': total_bettors}, room=request.sid)
            socketio.emit('spin_wait', {'players_ready': ready_count, 'players_needed': total_bettors}, room=room_name)
            emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)
            return

        # cancelar contador si estaba corriendo y ejecutar el giro
        try:
            st['spin_countdown_cancel'] = True
        except Exception:
            pass
        try:
            perform_spin(sala_id)
        except Exception as e:
            print('Error performing spin from handler:', e)

    @socketio.on('ruleta_bet_placed')
    def handle_bet_placed(data):
        """Recibir evento de apuesta en tiempo real desde el frontend"""
        if not current_user.is_authenticated:
            return
        sala_id = data.get('sala_id')
        target = data.get('target')
        amount = data.get('amount')
        try:
            amount = int(amount)
        except Exception:
            amount = 0
        color = data.get('color')
        
        room_name = f'ruleta_sala_{sala_id}'
        # Propagar a todos los jugadores en la sala
        emit('ruleta_bet_placed', {
            'usuario_id': current_user.id,
            'username': current_user.username,
            'target': target,
            'target_label': target.get('label') if isinstance(target, dict) else None,
            'amount': amount,
            'color': color
        }, room=room_name)

    @socketio.on('ruleta_clear_bets')
    def handle_clear_bets(data):
        """Broadcast that a user cleared their visual/local bets (no server-side wager state change)."""
        sala_id = data.get('sala_id')
        usuario_id = data.get('usuario_id')
        room_name = f'ruleta_sala_{sala_id}'
        emit('ruleta_clear_bets', {'sala_id': sala_id, 'usuario_id': usuario_id}, room=room_name)

    @socketio.on('ruleta_chat')
    def handle_chat(data):
        sala_id = data.get('sala_id')
        msg = data.get('message')
        room_name = f'ruleta_sala_{sala_id}'
        emit('new_ruleta_message', {'user_id': current_user.id, 'username': current_user.username, 'message': msg, 'timestamp': datetime.utcnow().isoformat()}, room=room_name)

    print("✅ Todos los handlers de Ruleta registrados correctamente")
