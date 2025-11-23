import random
from datetime import datetime, timedelta

import pytest

from app import socketio
from models import db, User, SalaMultijugador, Apuesta, Estadistica
from endpoints.protected.api.juegos.multiplayer.ruleta import socket_handlers as ruleta_handlers
from endpoints.protected.api.juegos.multiplayer.ruleta.socket_handlers import salas_ruleta, AVAILABLE_COLORS


def _crear_usuario(app, username: str, balance: float = 100.0) -> User:
    """Crea y persiste un usuario de prueba con balance configurable."""
    with app.app_context():
        user = User(username=username, email=f"{username}@example.com", balance=balance)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user


def _crear_sala_ruleta(app, creador_id: int, capacidad: int = 2) -> SalaMultijugador:
    """Genera una sala de ruleta lista para aceptar conexiones de socket."""
    with app.app_context():
        sala = SalaMultijugador(
            nombre="Sala Ruleta Test",
            juego="ruleta",
            capacidad=capacidad,
            estado="jugando",
            apuesta_minima=1.0,
            creador_id=creador_id,
            jugadores_actuales=0,
        )
        db.session.add(sala)
        db.session.commit()
        return sala


def _socket_client_para_usuario(app, user: User):
    """Devuelve un cliente de socket autenticado en sesion Flask para el usuario."""
    flask_client = app.test_client()
    with flask_client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
    return socketio.test_client(app, flask_test_client=flask_client)


@pytest.fixture(autouse=True)
def limpiar_estado_ruleta():
    salas_ruleta.clear()
    yield
    salas_ruleta.clear()


@pytest.fixture
def sala_y_clientes(app):
    """Crea dos usuarios, sala y clientes de socket listos para emitir eventos."""
    u1 = _crear_usuario(app, "ruleta_user_1", balance=120.0)
    u2 = _crear_usuario(app, "ruleta_user_2", balance=150.0)
    sala = _crear_sala_ruleta(app, creador_id=u1.id, capacidad=2)

    c1 = _socket_client_para_usuario(app, u1)
    c2 = _socket_client_para_usuario(app, u2)
    c1.emit("join_ruleta_room", {"sala_id": sala.id})
    c2.emit("join_ruleta_room", {"sala_id": sala.id})

    yield sala, (c1, c2), (u1, u2)

    c1.disconnect()
    c2.disconnect()
    with app.app_context():
        for u in (u1, u2):
            Apuesta.query.filter_by(user_id=u.id).delete()
            Estadistica.query.filter_by(user_id=u.id, juego="ruleta").delete()
            db.session.delete(User.query.get(u.id))
        db.session.delete(SalaMultijugador.query.get(sala.id))
        db.session.commit()


def test_join_registra_jugadores_y_colores_unicos(sala_y_clientes):
    sala, (c1, _), (u1, u2) = sala_y_clientes

    estado = salas_ruleta.get(sala.id)
    assert estado is not None
    assert len(estado["jugadores"]) == 2
    assert all(j["ready"] is False for j in estado["jugadores"])

    colores = estado.get("color_map")
    assert colores is not None
    assert set(colores.values()).issubset(set(AVAILABLE_COLORS))
    assert colores[u1.id] != colores[u2.id], "Cada jugador debe tener color unico"

    eventos = c1.get_received()
    nombres = [evt["name"] for evt in eventos]
    assert "players_colors_update" in nombres
    payload = next(evt for evt in eventos if evt["name"] == "players_colors_update")["args"][0]
    user_ids_con_color = {c["usuario_id"] for c in payload["colors"]}
    assert {u1.id, u2.id}.issubset(user_ids_con_color)


def test_cambiar_color_rechaza_color_duplicado(sala_y_clientes):
    sala, (c1, c2), (u1, u2) = sala_y_clientes
    estado = salas_ruleta[sala.id]
    color_u1 = estado["color_map"][u1.id]
    color_u2_inicial = estado["color_map"][u2.id]

    c2.get_received()
    c2.emit("cambiar_color", {"sala_id": sala.id, "color": color_u1})
    mensajes = c2.get_received()

    assert any(evt["name"] == "error" for evt in mensajes), "Debe emitir error cuando el color ya esta tomado"
    assert estado["color_map"][u2.id] == color_u2_inicial

    # Confirmar que el jugador 1 puede seguir cambiando a un color libre
    nuevo_color = next(col for col in AVAILABLE_COLORS if col not in {color_u1, color_u2_inicial})
    c1.emit("cambiar_color", {"sala_id": sala.id, "color": nuevo_color})
    assert estado["color_map"][u1.id] == nuevo_color


def test_place_bet_descuenta_balance_y_registra_apuesta(app, sala_y_clientes):
    sala, (c1, _), (u1, _) = sala_y_clientes
    balance_inicial = u1.balance
    apuesta_payload = {
        "sala_id": sala.id,
        "apuestas": [
            {"type": "straight", "set": [7], "label": "7", "amount": 250},
            {"type": "even", "set": list(range(1, 19)), "label": "1-18", "amount": 100},
        ],
    }

    c1.get_received()
    c1.emit("ruleta_place_bet", apuesta_payload)
    eventos = c1.get_received()
    nombres = [evt["name"] for evt in eventos]
    assert "apuesta_recibida" in nombres
    assert "estado_sala_actualizado" in nombres

    estado = salas_ruleta[sala.id]
    assert len(estado["apuestas"]) == 1
    apuesta_estado = estado["apuestas"][0]
    assert apuesta_estado["usuario_id"] == u1.id
    assert apuesta_estado["amount_cents"] == 350
    assert apuesta_estado["apuesta_id"] is not None
    assert estado.get("countdown_thread") is not None
    estado["spin_countdown_cancel"] = True  # evitar auto giro en pruebas

    with app.app_context():
        user_db = User.query.get(u1.id)
        assert user_db.balance == pytest.approx(balance_inicial - 3.5)
        apuesta_db = Apuesta.query.filter_by(user_id=u1.id, juego="ruleta").order_by(Apuesta.id.desc()).first()
        assert apuesta_db is not None
        assert apuesta_db.resultado == "PENDIENTE"
        assert apuesta_db.cantidad == pytest.approx(3.5)


def test_spin_requiere_todos_listos_y_liquida_apuestas(app, sala_y_clientes, monkeypatch):
    sala, (c1, c2), (u1, u2) = sala_y_clientes
    base_u1, base_u2 = u1.balance, u2.balance
    # Preparar apuestas sencillas: jugador 1 a Rojo, jugador 2 a un numero perdedor
    c1.emit("ruleta_place_bet", {"sala_id": sala.id, "apuestas": [{"type": "even", "set": list(range(1, 37, 2)), "label": "Rojo", "amount": 100}]})
    c2.emit("ruleta_place_bet", {"sala_id": sala.id, "apuestas": [{"type": "straight", "set": [0], "label": "0", "amount": 200}]})
    c1.get_received()
    c2.get_received()

    # Forzar resultado determinista
    monkeypatch.setattr(ruleta_handlers.random, "randint", lambda a, b: 3)

    c1.emit("ruleta_spin", {"sala_id": sala.id})
    ack_events = [evt for evt in c1.get_received() if evt["name"] == "spin_ack"]
    assert ack_events, "Debe avisar que aun faltan jugadores listos"
    ack_payload = ack_events[0]["args"][0]
    assert ack_payload["spun"] is False
    assert ack_payload["players_ready"] == 1
    assert ack_payload["players_needed"] == 2

    c2.emit("ruleta_spin", {"sala_id": sala.id})
    eventos_c1 = c1.get_received()
    nombres = [evt["name"] for evt in eventos_c1]
    assert "ruleta_girada" in nombres
    resultado_evento = next(evt for evt in eventos_c1 if evt["name"] == "ruleta_girada")["args"][0]
    assert resultado_evento["result"] == 3
    assert len(resultado_evento["results"]) == 2

    estado = salas_ruleta[sala.id]
    assert estado["apuestas"] == []
    assert estado["estado"] == "esperando"
    assert all(not j.get("ready") for j in estado["jugadores"])

    with app.app_context():
        u1_db = User.query.get(u1.id)
        u2_db = User.query.get(u2.id)
        assert u1_db.balance == pytest.approx(base_u1 + 1.0)  # gano 1 euro neto (recibe 2 tras apostar 1)
        assert u2_db.balance == pytest.approx(base_u2 - 2.0)

        apuesta1 = Apuesta.query.filter_by(user_id=u1.id, juego="ruleta").order_by(Apuesta.id.desc()).first()
        apuesta2 = Apuesta.query.filter_by(user_id=u2.id, juego="ruleta").order_by(Apuesta.id.desc()).first()
        assert str(3) in (apuesta1.resultado or "")
        assert str(3) in (apuesta2.resultado or "")
        stats1 = Estadistica.query.filter_by(user_id=u1.id, juego="ruleta").first()
        stats2 = Estadistica.query.filter_by(user_id=u2.id, juego="ruleta").first()
        assert stats1.partidas_jugadas == 1
        assert stats1.partidas_ganadas == 1
        assert stats1.apuesta_total == pytest.approx(1.0)
        assert stats1.ganancia_total == pytest.approx(1.0)
        assert stats2.partidas_jugadas == 1
        assert stats2.partidas_ganadas == 0
        assert stats2.apuesta_total == pytest.approx(2.0)
        assert stats2.ganancia_total == pytest.approx(0.0)


def test_broadcast_apuestas_visuales_y_limpieza(sala_y_clientes):
    sala, (c1, c2), (u1, _) = sala_y_clientes
    c1.get_received()
    c2.get_received()

    target = {"label": "13", "type": "straight", "set": [13]}
    c1.emit("ruleta_bet_placed", {"sala_id": sala.id, "target": target, "amount": 75, "color": "#FF6B6B"})
    eventos = c2.get_received()
    assert any(evt["name"] == "ruleta_bet_placed" for evt in eventos)
    payload = next(evt for evt in eventos if evt["name"] == "ruleta_bet_placed")["args"][0]
    assert payload["usuario_id"] == u1.id
    assert payload["target"]["set"] == target["set"]
    assert payload["amount"] == 75
    assert payload["target_label"] == "13"

    c1.emit("ruleta_clear_bets", {"sala_id": sala.id, "usuario_id": u1.id})
    eventos_limpieza = c2.get_received()
    assert any(evt["name"] == "ruleta_clear_bets" for evt in eventos_limpieza)


def test_fondos_insuficientes_emite_error_y_no_descuenta(app, sala_y_clientes):
    sala, (c1, _), (u1, _) = sala_y_clientes
    balance_inicial = u1.balance
    c1.get_received()
    c1.emit("ruleta_place_bet", {"sala_id": sala.id, "apuestas": [{"type": "straight", "set": [1], "label": "1", "amount": int((balance_inicial + 50) * 100)}]})
    mensajes = c1.get_received()
    assert any(evt["name"] == "error_apuesta" for evt in mensajes)
    with app.app_context():
        assert User.query.get(u1.id).balance == pytest.approx(balance_inicial)
        assert Apuesta.query.filter_by(user_id=u1.id, juego="ruleta").count() == 0


def test_leave_elimina_jugador_apuestas_y_color(sala_y_clientes):
    sala, (c1, c2), (u1, _) = sala_y_clientes
    c1.emit("ruleta_place_bet", {"sala_id": sala.id, "apuestas": [{"type": "straight", "set": [5], "label": "5", "amount": 100}]})
    c1.get_received()
    c2.get_received()

    c1.emit("leave_ruleta_room", {"sala_id": sala.id})
    estado = salas_ruleta[sala.id]
    assert all(j["id"] != u1.id for j in estado["jugadores"])
    assert all(a["usuario_id"] != u1.id for a in estado["apuestas"])
    assert u1.id not in estado.get("color_map", {})
    eventos_c2 = c2.get_received()
    assert any(evt["name"] == "estado_sala_actualizado" for evt in eventos_c2)


def test_spin_auto_por_tiempo_sin_todos_listos(app, sala_y_clientes, monkeypatch):
    sala, (c1, c2), (u1, u2) = sala_y_clientes
    base_u1, base_u2 = u1.balance, u2.balance
    c1.emit("ruleta_place_bet", {"sala_id": sala.id, "apuestas": [{"type": "even", "set": list(range(1, 37, 2)), "label": "Rojo", "amount": 100}]})
    # Solo un jugador listo; el otro no gira, pero el tiempo ya expiró
    estado = salas_ruleta[sala.id]
    estado["apuestas"][0]["submitted_at"] = (datetime.utcnow() - timedelta(seconds=35)).isoformat()
    monkeypatch.setattr(ruleta_handlers.random, "randint", lambda a, b: 9)

    c1.emit("ruleta_spin", {"sala_id": sala.id})
    eventos = c1.get_received()
    assert any(evt["name"] == "ruleta_girada" for evt in eventos), "Debe forzar giro tras 30s"
    resultados_evt = next(evt for evt in eventos if evt["name"] == "ruleta_girada")["args"][0]
    assert resultados_evt["result"] == 9

    with app.app_context():
        u1_db = User.query.get(u1.id)
        u2_db = User.query.get(u2.id)
        assert u1_db.balance == pytest.approx(base_u1 + 1.0)
        assert u2_db.balance == pytest.approx(base_u2)
