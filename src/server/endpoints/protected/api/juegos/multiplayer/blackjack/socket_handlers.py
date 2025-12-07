import time, random
from collections import deque
from flask_login import current_user
from flask_socketio import join_room, leave_room, emit
from models import db, User, SalaMultijugador, Apuesta, Estadistica
from flask import request
from sqlalchemy import func


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

def serializar_stats(stats_obj, extras=None):
    """Devuelve un diccionario con las estadisticas normalizadas."""
    extras = extras or {}
    if not stats_obj:
        base = {
            "partidas_jugadas": 0,
            "partidas_ganadas": 0,
            "apuesta_total": 0.0,
            "ganancia_total": 0.0,
        }
    else:
        base = {
            "partidas_jugadas": stats_obj.partidas_jugadas or 0,
            "partidas_ganadas": stats_obj.partidas_ganadas or 0,
            "apuesta_total": float(stats_obj.apuesta_total or 0),
            "ganancia_total": float(stats_obj.ganancia_total or 0),
        }

    empates = extras.get("empates", 0)
    perdidas = extras.get("perdidas")
    if perdidas is None:
        perdidas = max(0, base["partidas_jugadas"] - base["partidas_ganadas"] - empates)

    base.update({
        "victorias": base["partidas_ganadas"],
        "ganadas": base["partidas_ganadas"],
        "derrotas": perdidas,
        "perdidas": perdidas,
        "empates": empates,
        "blackjacks": extras.get("blackjacks", 0),
    })
    return base

def _stats_base():
    """Estadisticas en cero para una sala recien creada (no arrastrar de otras salas)."""
    return {
        "partidas_jugadas": 0,
        "partidas_ganadas": 0,
        "ganancia_total": 0.0,
        "apuesta_total": 0.0,
        "victorias": 0,
        "ganadas": 0,
        "derrotas": 0,
        "perdidas": 0,
        "empates": 0,
        "blackjacks": 0,
    }

def _refrescar_aliases(stats_dict):
    perdidas = max(0, stats_dict["partidas_jugadas"] - stats_dict["partidas_ganadas"] - stats_dict.get("empates", 0))
    stats_dict["victorias"] = stats_dict["partidas_ganadas"]
    stats_dict["ganadas"] = stats_dict["partidas_ganadas"]
    stats_dict["derrotas"] = perdidas
    stats_dict["perdidas"] = perdidas
    stats_dict["empates"] = stats_dict.get("empates", 0)
    return stats_dict

def refrescar_estadisticas_jugadores(st):
    """
    Carga las estadisticas consolidadas de blackjack para los jugadores de la sala
    y las deja en memoria para emitirlas al cliente.
    """
    uids = list(st["jugadores"].keys())
    if not uids:
        st["estadisticas_jugadores"] = {}
        return st["estadisticas_jugadores"]

    conteos = {uid: {"empates": 0, "perdidas": 0, "blackjacks": 0} for uid in uids}
    rows = db.session.query(
        Apuesta.user_id,
        Apuesta.resultado,
        func.count(Apuesta.id)
    ).filter(
        Apuesta.user_id.in_(uids),
        Apuesta.juego.in_(["blackjack", "blackjack_multijugador"]),
        Apuesta.tipo_juego == 'multiplayer'
    ).group_by(Apuesta.user_id, Apuesta.resultado).all()

    for uid, res, count in rows:
        res_low = (res or "").lower()
        if "empate" in res_low:
            conteos[uid]["empates"] = count
        elif "perd" in res_low:
            conteos[uid]["perdidas"] = count
        elif "blackjack" in res_low:
            conteos[uid]["blackjacks"] = count

    stats_db = Estadistica.query.filter(
        Estadistica.user_id.in_(uids),
        Estadistica.juego == "blackjack",
        Estadistica.tipo_juego == 'multiplayer'

    ).all()
    stats_map = {s.user_id: s for s in stats_db}

    payload = {
        uid: serializar_stats(stats_map.get(uid), conteos.get(uid, {}))
        for uid in uids
    }
    st["estadisticas_jugadores"] = payload
    for uid, stats in payload.items():
        if uid in st["jugadores"]:
            st["jugadores"][uid]["estadisticas"] = stats
    return payload

def emitir_estado(sala_id):
    st = salas_blackjack[sala_id]
    room = f"blackjack_sala_{sala_id}"
    stats_por_jugador = st.get("estadisticas_jugadores", {})
    stats_payload = {str(uid): stats for uid, stats in stats_por_jugador.items()}
    emit("estado_blackjack", {
        "jugadores": {
            str(uid): {
                "username": j["username"],
                "balance": j["balance"],
                "apuesta": j["apuesta"],
                "mano": j["mano"],
                "estado": j["estado"],
                "total": valor_mano(j["mano"]),
                "estadisticas": stats_por_jugador.get(uid) or stats_por_jugador.get(str(uid))
            } for uid, j in st["jugadores"].items()
        },
        "dealer": st["dealer"],
        "dealer_total": valor_mano(st["dealer"]) if st["fase"] in ("crupier","fin") else None,
        "orden_turnos": st["orden_turnos"],
        "turno_actual": (st["orden_turnos"][st["turno_idx"]] if st["turno_idx"] is not None else None),
        "fase": st["fase"],
        "deadline_ts": st["deadline_ts"],
        "votos_revancha": list(st["votos_revancha"]),
        "estadisticas_jugadores": stats_payload,
        "stats_jugadores": stats_payload,
        "estadisticas": stats_payload,
        "stats": stats_payload,
        "resumen_estadisticas": stats_payload,
        "resumen": stats_payload,
        "resumen_stats": stats_payload,
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
        apuesta_monto = j["apuesta"]
        if apuesta_monto <= 0:
            continue
        pj = valor_mano(j["mano"])
        pago_total = 0.0

        if pj > 21:
            pago_total = 0.0
        elif es_blackjack(j["mano"]):
            if dealer_bj:
                pago_total = apuesta_monto  # push si ambos blackjack
            else:
                pago_total = apuesta_monto * 2.5  # 3:2
        elif dealer_val > 21 or pj > dealer_val:
            pago_total = apuesta_monto * 2.0
        elif pj == dealer_val:
            pago_total = apuesta_monto
        else:
            pago_total = 0.0

        # Actualizar saldo real en DB y en memoria
        user = User.query.get(uid)
        if user:
            user.balance = (user.balance or 0) + pago_total
            db.session.add(user)
            # Mantener memoria alineada con DB para el header
            j["balance"] = float(user.balance)
            
            # Registrar apuesta y estadisticas consolidando en blackjack
            resultado = "perdida"
            if pago_total > apuesta_monto:
                resultado = "ganada"
            elif pago_total == apuesta_monto:
                resultado = "empate"

            apuesta_db = Apuesta(
                user_id=uid,
                juego="blackjack_multijugador",
                tipo_juego='multiplayer',
                cantidad=apuesta_monto,
                resultado=resultado,
                ganancia=pago_total
            )
            db.session.add(apuesta_db)

            stats = Estadistica.query.filter_by(user_id=uid, juego="blackjack", tipo_juego='multiplayer').first()
            if not stats:
                stats = Estadistica(
                    user_id=uid,
                    juego="blackjack",
                    tipo_juego='multiplayer',
                    partidas_jugadas=0,
                    partidas_ganadas=0,
                    ganancia_total=0.0,
                    apuesta_total=0.0
                )
                db.session.add(stats)

            stats.partidas_jugadas += 1
            stats.apuesta_total += apuesta_monto
            stats.ganancia_total += pago_total
            if pago_total > apuesta_monto:
                stats.partidas_ganadas += 1

            # Estadisticas en memoria POR SALA (reiniciadas cuando la sala es nueva)
            stats_mem = st.setdefault("estadisticas_jugadores", {}).setdefault(uid, _stats_base())
            stats_mem["partidas_jugadas"] += 1
            stats_mem["apuesta_total"] += apuesta_monto
            stats_mem["ganancia_total"] += pago_total
            if pago_total > apuesta_monto:
                stats_mem["partidas_ganadas"] += 1
            elif pago_total == apuesta_monto:
                stats_mem["empates"] = stats_mem.get("empates", 0) + 1
            _refrescar_aliases(stats_mem)
            st["jugadores"][uid]["estadisticas"] = stats_mem

            emit("balance_update", {"balance": float(user.balance)}, room=f"blackjack_sala_{sala_id}")


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
        st = salas_blackjack.setdefault(sala_id, {
            "jugadores": {},
            "dealer": [],
            "mazo": nueva_baraja(),
            "orden_turnos": [],
            "turno_idx": None,
            "fase": "esperando_apuestas",
            "deadline_ts": None,
            "votos_revancha": set(),
            "estadisticas_jugadores": {},
            "_timer_activo": False
        })

        # Limitar sala a max. 4 jugadores nuevos; permitir reingreso del mismo usuario
        if current_user.id not in st["jugadores"] and len(st["jugadores"]) >= 4:
            emit("error_blackjack", {"msg": "Sala llena (maximo 4 jugadores)."}, room=request.sid)
            return

        join_room(room)

        if current_user.id not in st["jugadores"]:
            st["jugadores"][current_user.id] = {
                "username": current_user.username,
                "balance": float(current_user.balance or 0),
                "mano": [],
                "apuesta": 0.0,
                "estado": "espera"
            }
            st["orden_turnos"].append(current_user.id)

        # Estadisticas por sala arrancan en 0 (no reutilizar de otras salas)
        st["estadisticas_jugadores"].setdefault(current_user.id, _stats_base())
        st["jugadores"][current_user.id]["estadisticas"] = st["estadisticas_jugadores"][current_user.id]

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
        if "estadisticas_jugadores" in st:
            st["estadisticas_jugadores"].pop(uid, None)
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

        emit("balance_update", {"balance": float(user.balance)}, room=request.sid)

        emitir_estado(sala_id)

    @socketio.on("iniciar_ronda_blackjack")
    def iniciar(data):
        sala_id = int(data["sala_id"])
        st = salas_blackjack.get(sala_id)
        if not st or st["fase"] != "esperando_apuestas":
            return

        # Mínimo 2 jugadores con apuesta y aviso de quién falta por apostar
        jugadores_con_apuesta = [j for j in st["jugadores"].values() if j["apuesta"] > 0]
        jugadores_sin_apuesta = [j["username"] for j in st["jugadores"].values() if j["apuesta"] <= 0]

        if len(jugadores_con_apuesta) < 2:
            mensaje = "Se necesitan al menos 2 jugadores con apuesta."
            if jugadores_sin_apuesta:
                mensaje += " Falta apostar: " + ", ".join(jugadores_sin_apuesta)
            emit("error_blackjack", {
                "msg": mensaje,
                "faltan_apostar": jugadores_sin_apuesta
            }, to=f"blackjack_sala_{sala_id}")
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
        else:
            # Reinicia el temporizador a 15s si la acci��n no fue plantarse
            st["deadline_ts"] = time.time() + 15
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

    @socketio.on("rechazar_revancha")
    def rechazar_revancha(data):
        sala_id = int(data["sala_id"])
        st = salas_blackjack.get(sala_id)
        if not st or st["fase"] != "fin":
            return
        # Marcar sala cerrada y redirigir a todos al dashboard
        st["fase"] = "cerrada"
        emit("blackjack_redirect_dashboard", {}, room=f"blackjack_sala_{sala_id}")

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


