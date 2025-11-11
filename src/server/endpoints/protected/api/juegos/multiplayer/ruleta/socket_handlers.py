from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room, emit
from models import db, SalaMultijugador, UsuarioSala, User, Apuesta, Estadistica
from datetime import datetime
import random, time

# Estado en memoria por sala para la ruleta multijugador
salas_ruleta = {}

def register_ruleta_handlers(socketio, app):
    print("✅ Registrando handlers de Ruleta multijugador")

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

        emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)
        emit('user_joined_ruleta', {'user_id': current_user.id, 'username': current_user.username}, room=room_name)

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
            emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)

    @socketio.on('ruleta_place_bet')
    def handle_place(data):
        sala_id = data.get('sala_id')
        bets = data.get('bets')
        if not sala_id or not bets:
            emit('error', {'message': 'sala_id y bets requeridos'}, room=request.sid)
            return

        sala = SalaMultijugador.query.get(sala_id)
        if not sala:
            emit('error', {'message': 'Sala no encontrada'}, room=request.sid)
            return

        # calcular total
        total_cents = sum(int(b.get('amount', 0)) for b in bets)
        total_euros = total_cents / 100.0
        if total_euros > current_user.balance:
            emit('error_apuesta', {'message': 'Fondos insuficientes'}, room=request.sid)
            return

        # descontar balance y guardar apuesta en memoria (secreta)
        current_user.balance -= total_euros
        db.session.commit()

        st = salas_ruleta.setdefault(sala_id, {'jugadores': [], 'estado': 'esperando', 'apuestas': []})
        room_name = f'ruleta_sala_{sala_id}'
        # actualizar/apilar la apuesta secreta (no emitir detalles a otros)
        existing = next((a for a in st['apuestas'] if a['usuario_id'] == current_user.id), None)
        if existing:
            existing['bets'] = bets
            existing['amount_cents'] = total_cents
            existing['submitted_at'] = datetime.utcnow().isoformat()
            existing['has_spun'] = False
        else:
            st['apuestas'].append({'usuario_id': current_user.id, 'bets': bets, 'amount_cents': total_cents, 'submitted_at': datetime.utcnow().isoformat(), 'has_spun': False})

        # notificar estado (sin revelar apuestas)
        emit('apuesta_recibida', {'sala_id': sala_id, 'user_id': current_user.id}, room=room_name)
        emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)

    @socketio.on('ruleta_spin')
    def handle_spin(data):
        sala_id = data.get('sala_id')
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

        # chequear si todos listos o 30s desde la primera apuesta
        # Considerar el número de jugadores actualmente conectados en la sala
        required = len(st['jugadores']) if len(st.get('jugadores', [])) > 0 else sala.capacidad
        ready_count = sum(1 for j in st['jugadores'] if j.get('ready'))
        created_at = None
        if st['apuestas']:
            # tomar timestamp de la primera apuesta
            created_at = datetime.fromisoformat(st['apuestas'][0].get('submitted_at'))
        elapsed = (datetime.utcnow() - created_at).total_seconds() if created_at else 0
        auto_spin = elapsed >= 30

        if ready_count < required and not auto_spin:
            emit('spin_ack', {'ok': True, 'spun': False, 'players_ready': ready_count, 'players_needed': required, 'seconds_elapsed': int(elapsed)}, room=request.sid)
            emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)
            return

        # realizar giro
        result_number = random.randint(0,36)
        REDS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        PAYOUT = {'straight':35,'split':17,'street':11,'corner':8,'line':5,'dozen':2,'column':2,'even':1}

        results = []
        for a in st['apuestas']:
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
                'username': user.username if user else None,
                'bet_total_euros': total_bet_euros,
                'win_euros': total_win_euros,
                'payout_euros': total_payout_euros,
                'nuevo_balance': user.balance if user else None
            })

        # commit DB
        db.session.commit()

        # limpiar estado y notificar
        st['apuestas'] = []
        for j in st['jugadores']:
            j['ready'] = False
        st['estado'] = 'esperando'

        emit('ruleta_girada', {'result': result_number, 'results': results}, room=room_name)
        emit('estado_sala_actualizado', {'sala_id': sala_id, 'jugadores': st['jugadores'], 'apuestas_count': len(st['apuestas']), 'estado': st['estado']}, room=room_name)

    @socketio.on('ruleta_chat')
    def handle_chat(data):
        sala_id = data.get('sala_id')
        msg = data.get('message')
        room_name = f'ruleta_sala_{sala_id}'
        emit('new_ruleta_message', {'user_id': current_user.id, 'username': current_user.username, 'message': msg, 'timestamp': datetime.utcnow().isoformat()}, room=room_name)

    print("✅ Todos los handlers de Ruleta registrados correctamente")
