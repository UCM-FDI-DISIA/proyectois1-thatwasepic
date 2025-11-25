from flask import request
from flask_login import current_user
from flask_socketio import join_room, emit, rooms
from models import db, User, Apuesta, SalaMultijugador
import random
import threading
import time

salas_caballos = {}


def elegir_ganador():
    """Elegir ganador con probabilidades basadas en singleplayer."""
    puntuaciones = {
        1: 0.85 * 0.7 + 0.70 * 0.3,
        2: 0.75 * 0.7 + 0.80 * 0.3,
        3: 0.65 * 0.7 + 0.85 * 0.3,
        4: 0.45 * 0.7 + 0.95 * 0.3,
    }
    total = sum(puntuaciones.values())
    probs = [puntuaciones[i] / total for i in range(1, 5)]
    r = random.random()
    acum = 0
    for i, p in enumerate(probs, start=1):
        acum += p
        if r <= acum:
            return i
    return 4


def register_caballos_handlers(socketio, app):
    print("✅ Registrando handlers de Caballos multijugador")

    @socketio.on('join_caballos_room')
    def handle_join(data):
        if not current_user.is_authenticated:
            return
        sala_id = int(data.get('sala_id'))
        room_name = f'caballos_sala_{sala_id}'
        join_room(room_name)
        st = salas_caballos.setdefault(sala_id, {'jugadores': [], 'apuestas': {}, 'estado': 'esperando'})
        if current_user.id not in [j['id'] for j in st['jugadores']]:
            st['jugadores'].append({'id': current_user.id, 'username': current_user.username, 'balance': current_user.balance})
        emit('estado_sala_actualizado', {'jugadores': st['jugadores'], 'apuestas': st['apuestas'], 'estado': st['estado']}, room=room_name)

    @socketio.on('caballos_place_bet')
    def handle_place_bet(data):
        sala_id = int(data.get('sala_id'))
        caballo = int(data.get('caballo'))
        cantidad = float(data.get('cantidad', 0))
        room_name = f'caballos_sala_{sala_id}'
        st = salas_caballos.setdefault(sala_id, {'jugadores': [], 'apuestas': {}, 'estado': 'esperando'})
        if cantidad > current_user.balance:
            emit('error_apuesta', {'message': 'Fondos insuficientes'}, room=request.sid)
            return
        # Deduce la apuesta inmediatamente
        current_user.balance -= cantidad
        db.session.commit()
        st['apuestas'][current_user.id] = {'caballo': caballo, 'cantidad': cantidad, 'username': current_user.username}
        # Notificar nuevo estado a la sala
        emit('estado_sala_actualizado', {'jugadores': st['jugadores'], 'apuestas': st['apuestas'], 'estado': st['estado']}, room=room_name)

        # Si todos han apostado, notificar a la sala
        if len(st['apuestas']) == len(st['jugadores']):
            st['estado'] = 'listo_para_iniciar'
            emit('todos_apostaron', {}, room=room_name)

    @socketio.on('iniciar_carrera')
    def handle_iniciar(data):
        print(f"🔥 handle_iniciar llamado con data={data}")
        sala_id = int(data.get('sala_id'))
        room_name = f'caballos_sala_{sala_id}'

        # Verificar que la sala existe y que el que solicita es el creador
        sala = SalaMultijugador.query.get(sala_id)
        if sala and sala.creador_id and sala.creador_id != current_user.id:
            print(f"❌ No eres creador. Creador: {sala.creador_id}, Actual: {current_user.id}")
            emit('error_general', {'message': 'Solo el creador puede iniciar la carrera'}, room=request.sid)
            return

        st = salas_caballos.get(sala_id)
        if not st or len(st.get('apuestas', {})) == 0:
            print(f"❌ No hay apuestas en sala {sala_id}")
            emit('error_general', {'message': 'No hay apuestas'}, room=request.sid)
            return

        print(f"✅ Iniciando carrera en sala {sala_id} con {len(st['apuestas'])} apuestas")
        st['estado'] = 'corriendo'

        # Elegir ganador en servidor
        ganador = elegir_ganador()
        print(f"🐴 Ganador elegido: {ganador}")

        # Procesar resultados y actualizar DB
        resultados = {}
        for uid, apuesta in st['apuestas'].items():
            user = User.query.get(uid)
            if not user:
                print(f"⚠️  Usuario {uid} no encontrado")
                continue
            if apuesta['caballo'] == ganador:
                mult = {1: 1.5, 2: 2.0, 3: 3.0, 4: 6.0}.get(apuesta['caballo'], 1)
                ganancia = apuesta['cantidad'] * mult
                user.balance += ganancia
                resultado = 'ganada'
                print(f"✅ Usuario {uid} ({user.username}) ganó {ganancia} (caballo {apuesta['caballo']})")
            else:
                ganancia = 0
                resultado = 'perdida'
                print(f"❌ Usuario {uid} ({user.username}) perdió (caballo {apuesta['caballo']})")
            db.session.add(Apuesta(user_id=uid, juego='caballos', cantidad=apuesta['cantidad'], resultado=resultado, ganancia=ganancia))
            db.session.commit()
            resultados[uid] = {'has_ganado': apuesta['caballo'] == ganador, 'nuevo_balance': user.balance}

        st['estado'] = 'finalizada'

        # Emitir inicio de carrera con duración (ms) para sincronizar animación en clientes
        duracion_ms = 4000
        emit('start_race', {'ganador': ganador, 'duracion': duracion_ms}, room=room_name)
        print(f"✅ Emitido start_race: ganador={ganador}, duracion={duracion_ms}ms, room={room_name}")

        # Enviar resultados después de la duración para que los clientes muestren los saldos
        def delayed_emit():
            print(f"⏳ Esperando {duracion_ms}ms antes de emitir race_result...")
            time.sleep(duracion_ms / 1000.0)
            print(f"✅ Emitiendo race_result a room {room_name}: ganador={ganador}, resultados={resultados}")
            # Usar socketio.emit directamente - debe funcionar con skip_sid=False
            try:
                socketio.emit('race_result', 
                              {'ganador': ganador, 'resultados': resultados}, 
                              room=room_name,
                              namespace='/')
                print("✅ race_result emitido exitosamente")
            except Exception as e:
                print(f"❌ Error emitiendo race_result: {e}")

        threading.Thread(target=delayed_emit, daemon=True).start()

