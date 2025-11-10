import time, random
from collections import deque
from flask_login import current_user
from flask_socketio import join_room, leave_room, emit
from models import db, User, SalaMultijugador

# ================== Estado en memoria por sala ==================
salas_blackjack = {}
# Estructura:
# {
#   'jugadores': { uid: {'username','balance','mano':[],'apuesta':0.0,'estado':'espera|jugando|bust|plantado'} },
#   'dealer': [],
#   'mazo': deque([...]),
#   'orden_turnos': [uid,...],
#   'turno_idx': int|None,
#   'fase': 'esperando_apuestas|turnos|crupier|fin',
#   'deadline_ts': float|None,
#   'votos_revancha': set(uid),
#   '_timer_activo': bool
# }

# ================== Utilidades ==================
def nueva_baraja():
    palos = ['♠','♥','♦','♣']
    valores = [(str(n), n) for n in range(2,11)] + [('J',10),('Q',10),('K',10),('A',11)]
    mazo = [(v,p,pts) for (v,pts) in valores for p in palos]
    random.shuffle(mazo)
    return deque(mazo)

def valor_mano(mano):
    total = sum(c[2] for c in mano)
    ases = sum(1 for c in mano if c[0] == 'A')
    while total > 21 and ases:
        total -= 10
        ases -= 1
    return total

def es_blackjack(mano):
    # Natural: exactamente 2 cartas sumando 21
    return len(mano) == 2 and valor_mano(mano) == 21

def turno_vivo(st, uid):
    j = st['jugadores'][uid]
    return j['estado'] == 'jugando' and valor_mano(j['mano']) <= 21

def avanzar_turno(st):
    n = len(st['orden_turnos'])
    if n == 0:
        st['turno_idx'] = None
        st['fase'] = 'crupier'
        return
    start = 0 if st['turno_idx'] is None else (st['turno_idx'] + 1)
    for k in range(n):
        idx = (start + k) % n
        uid = st['orden_turnos'][idx]
        if turno_vivo(st, uid):
            st['turno_idx'] = idx
            st['deadline_ts'] = time.time() + 15
            return
    st['turno_idx'] = None
    st['fase'] = 'crupier'

def emitir_estado(sala_id):
    st = salas_blackjack[sala_id]
    room = f"blackjack_sala_{sala_id}"
    emit("estado_blackjack", {
        "jugadores": {
            str(uid): {
                "username": j["username"],
                "balance": j["balance"],
                "apuesta": j["apuesta"],
                "mano": j["mano"],
                "estado": j["estado"],
                "total": valor_mano(j["mano"])
            } for uid, j in st["jugadores"].items()
        },
        "dealer": st["dealer"],
        "dealer_total": valor_mano(st["dealer"]) if st["fase"] in ("crupier","fin") else None,
        "orden_turnos": st["orden_turnos"],
        "turno_actual": (st["orden_turnos"][st["turno_idx"]] if st["turno_idx"] is not None else None),
        "fase": st["fase"],
        "deadline_ts": st["deadline_ts"],
        "votos_revancha": list(st["votos_revancha"]),
    }, room=room)

# ================== Temporizador de turnos ==================
def start_timer_if_needed(socketio, sala_id, app):
    st = salas_blackjack[sala_id]
    if st.get("_timer_activo") or st["fase"] != "turnos":
        return

    st["_timer_activo"] = True
    def _loop():
        with app.app_context():
            try:
                while True:
                    st = salas_blackjack.get(sala_id)
                    if not st or st["fase"] != "turnos":
                        break
                    if st["deadline_ts"] and time.time() >= st["deadline_ts"]:
                        # Auto-plantarse si se acaba el tiempo
                        if st["turno_idx"] is not None:
                            uid_turno = st["orden_turnos"][st["turno_idx"]]
                            st["jugadores"][uid_turno]["estado"] = "plantado"
                            avanzar_turno(st)
                            if st["fase"] == "crupier":
                                ejecutar_crupier_y_resolver(sala_id)
                        emitir_estado(sala_id)
                    socketio.sleep(0.5)
            finally:
                st = salas_blackjack.get(sala_id)
                if st:
                    st["_timer_activo"] = False
    socketio.start_background_task(_loop)

# ================== Liquidación ==================
def ejecutar_crupier_y_resolver(sala_id):
    st = salas_blackjack[sala_id]
    st["fase"] = "crupier"

    # Roba hasta 17
    while valor_mano(st["dealer"]) < 17:
        st["dealer"].append(st["mazo"].popleft())
    dealer_val = valor_mano(st["dealer"])
    dealer_bj = es_blackjack(st["dealer"])

    # Payouts con apuesta ya descontada al principio:
    # - perdida: 0
    # - empate: 1× apuesta (se devuelve)
    # - ganada: 2× apuesta (apuesta + beneficio)
    # - blackjack natural: 2.5× apuesta (3:2)
    for uid, j in st["jugadores"].items():
        if j["apuesta"] <= 0:
            continue
        pj = valor_mano(j["mano"])
        pago_total = 0.0

        if pj > 21:
            pago_total = 0.0
        elif es_blackjack(j["mano"]):
            if dealer_bj:
                pago_total = j["apuesta"]  # push si ambos blackjack
            else:
                pago_total = j["apuesta"] * 2.5  # 3:2
        elif dealer_val > 21 or pj > dealer_val:
            pago_total = j["apuesta"] * 2.0
        elif pj == dealer_val:
            pago_total = j["apuesta"]
        else:
            pago_total = 0.0

        # Actualizar saldo real en DB y en memoria
        user = User.query.get(uid)
        if user:
            user.balance = (user.balance or 0) + pago_total
            db.session.add(user)
            # Mantener memoria alineada con DB para el header
            j["balance"] = float(user.balance)

        j["apuesta"] = 0.0

    db.session.commit()
    st["fase"] = "fin"

# ================== Registro de handlers ==================
def register_blackjack_handlers(socketio, app):

    @socketio.on("join_sala_blackjack")
    def join_sala(data):
        sala_id = int(data["sala_id"])
        sala = SalaMultijugador.query.get(sala_id)
        if not sala or sala.juego != "blackjack":
            return
        room = f"blackjack_sala_{sala_id}"
        join_room(room)

        st = salas_blackjack.setdefault(sala_id, {
            "jugadores": {},
            "dealer": [],
            "mazo": nueva_baraja(),
            "orden_turnos": [],
            "turno_idx": None,
            "fase": "esperando_apuestas",
            "deadline_ts": None,
            "votos_revancha": set(),
            "_timer_activo": False
        })

        if current_user.id not in st["jugadores"]:
            st["jugadores"][current_user.id] = {
                "username": current_user.username,
                "balance": float(current_user.balance or 0),
                "mano": [],
                "apuesta": 0.0,
                "estado": "espera"
            }
            st["orden_turnos"].append(current_user.id)

        emitir_estado(sala_id)

    @socketio.on("leave_sala_blackjack")
    def leave_sala(data):
        sala_id = int(data["sala_id"])
        room = f"blackjack_sala_{sala_id}"
        leave_room(room)

        st = salas_blackjack.get(sala_id)
        if not st:
            return
        uid = current_user.id
        if uid in st["jugadores"]:
            # Si se va en medio de una ronda: la apuesta queda y se resuelve normal.
            st["jugadores"].pop(uid, None)
        if uid in st["orden_turnos"]:
            st["orden_turnos"].remove(uid)
        if not st["jugadores"]:
            salas_blackjack.pop(sala_id, None)
        else:
            emitir_estado(sala_id)

    @socketio.on("apostar_blackjack")
    def apostar(data):
        sala_id = int(data["sala_id"])
        cantidad = float(data["cantidad"])
        st = salas_blackjack.get(sala_id)
        if not st or st["fase"] != "esperando_apuestas":
            return
        j = st["jugadores"].get(current_user.id)
        if not j or cantidad <= 0:
            return

        # Comprobar saldo en DB
        user = User.query.get(current_user.id)
        if not user or (user.balance or 0) < cantidad:
            emit("error_blackjack", {"msg": "Saldo insuficiente."}, to=f"blackjack_sala_{sala_id}")
            return

        # Descontar apuesta del saldo REAL y sincronizar memoria
        user.balance = float(user.balance) - cantidad
        db.session.add(user)
        db.session.commit()

        j["apuesta"] = cantidad
        j["balance"] = float(user.balance)
        j["estado"] = "jugando"
        emitir_estado(sala_id)

    @socketio.on("iniciar_ronda_blackjack")
    def iniciar(data):
        sala_id = int(data["sala_id"])
        st = salas_blackjack.get(sala_id)
        if not st or st["fase"] != "esperando_apuestas":
            return

        # Mínimo 2 jugadores con apuesta
        if sum(1 for j in st["jugadores"].values() if j["apuesta"] > 0) < 2:
            emit("error_blackjack", {"msg": "Se necesitan al menos 2 jugadores con apuesta."},
                 to=f"blackjack_sala_{sala_id}")
            return

        # Reparto inicial
        st["dealer"] = [st["mazo"].popleft(), st["mazo"].popleft()]
        for j in st["jugadores"].values():
            if j["apuesta"] > 0:
                j["mano"] = [st["mazo"].popleft(), st["mazo"].popleft()]
                j["estado"] = "jugando"
            else:
                j["mano"] = []
                j["estado"] = "espera"

        st["fase"] = "turnos"
        st["turno_idx"] = None
        avanzar_turno(st)
        emitir_estado(sala_id)
        start_timer_if_needed(socketio, sala_id, app)

    @socketio.on("hit_blackjack")
    def hit(data):
        sala_id = int(data["sala_id"])
        st = salas_blackjack.get(sala_id)
        if not st or st["fase"] != "turnos" or st["turno_idx"] is None:
            return
        uid_turno = st["orden_turnos"][st["turno_idx"]]
        if current_user.id != uid_turno:
            return
        st["jugadores"][uid_turno]["mano"].append(st["mazo"].popleft())
        if valor_mano(st["jugadores"][uid_turno]["mano"]) > 21:
            st["jugadores"][uid_turno]["estado"] = "bust"
            avanzar_turno(st)
            if st["fase"] == "crupier":
                ejecutar_crupier_y_resolver(sala_id)
        emitir_estado(sala_id)

    @socketio.on("stand_blackjack")
    def stand(data):
        sala_id = int(data["sala_id"])
        st = salas_blackjack.get(sala_id)
        if not st or st["fase"] != "turnos" or st["turno_idx"] is None:
            return
        uid_turno = st["orden_turnos"][st["turno_idx"]]
        if current_user.id != uid_turno:
            return
        st["jugadores"][uid_turno]["estado"] = "plantado"
        avanzar_turno(st)
        if st["fase"] == "crupier":
            ejecutar_crupier_y_resolver(sala_id)
        emitir_estado(sala_id)

    @socketio.on("voto_revancha")
    def voto_revancha(data):
        sala_id = int(data["sala_id"])
        st = salas_blackjack.get(sala_id)
        if not st or st["fase"] != "fin":
            return
        st["votos_revancha"].add(current_user.id)
        if len(st["votos_revancha"]) >= 2 and len(st["jugadores"]) >= 2:
            reset_para_nueva_ronda(st)
        emitir_estado(sala_id)

# ================== Reset de ronda ==================
def reset_para_nueva_ronda(st):
    st["dealer"].clear()
    for j in st["jugadores"].values():
        j["mano"] = []
        j["apuesta"] = 0.0
        j["estado"] = "espera"
    st["mazo"] = nueva_baraja()
    st["orden_turnos"] = list(st["jugadores"].keys())
    st["turno_idx"] = None
    st["fase"] = "esperando_apuestas"
    st["deadline_ts"] = None
    st["votos_revancha"].clear()


