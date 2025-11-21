import random
from collections import deque

import pytest
from flask_socketio import SocketIOTestClient

from app import app as flask_app, socketio
from models import db, User, SalaMultijugador
from endpoints.protected.api.juegos.multiplayer.blackjack.socket_handlers import salas_blackjack, valor_mano


# Helpers

def _crear_usuario(app, username: str, balance: float = 100.0) -> User:
    """Create and persist a user with the given balance."""
    with app.app_context():
        usuario = User(username=username, email=f"{username}@example.com", balance=balance)
        usuario.set_password("password123")
        db.session.add(usuario)
        db.session.commit()
        return usuario


def _crear_sala_blackjack(app, creador_id: int, nombre: str = "Sala BJ Test") -> SalaMultijugador:
    """Create a blackjack room in estado 'esperando'."""
    with app.app_context():
        sala = SalaMultijugador(
            nombre=nombre,
            juego="blackjack",
            creador_id=creador_id,
            capacidad=4,
            estado="esperando",
            apuesta_minima=1.0,
        )
        db.session.add(sala)
        db.session.commit()
        return sala


def _socket_client_para_usuario(app, user: User) -> SocketIOTestClient:
    """Build a SocketIO test client with the Flask session autenticada for the user."""
    flask_test_client = app.test_client()
    with flask_test_client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
    client = socketio.test_client(app, flask_test_client=flask_test_client)
    return client


def _limpiar_sala_db(app, sala_id: int):
    with app.app_context():
        sala = SalaMultijugador.query.get(sala_id)
        if sala:
            db.session.delete(sala)
            db.session.commit()


@pytest.fixture(autouse=True)
def limpiar_estado_blackjack():
    salas_blackjack.clear()
    yield
    salas_blackjack.clear()


@pytest.fixture
def dos_usuarios(app):
    u1 = _crear_usuario(app, "bj_user_1", balance=150.0)
    u2 = _crear_usuario(app, "bj_user_2", balance=120.0)
    yield u1, u2
    with app.app_context():
        for u in (u1, u2):
            db.session.delete(User.query.get(u.id))
        db.session.commit()


@pytest.fixture
def sala_y_clients(app, dos_usuarios):
    user1, user2 = dos_usuarios
    sala = _crear_sala_blackjack(app, creador_id=user1.id, nombre="Sala Extensa de Pruebas")
    random.seed(123)
    c1 = _socket_client_para_usuario(app, user1)
    c2 = _socket_client_para_usuario(app, user2)
    c1.emit("join_sala_blackjack", {"sala_id": sala.id})
    c2.emit("join_sala_blackjack", {"sala_id": sala.id})
    yield sala, (c1, c2), (user1, user2)
    c1.disconnect()
    c2.disconnect()
    _limpiar_sala_db(app, sala.id)


def test_join_registra_jugadores_y_orden_turnos(app, sala_y_clients):
    sala, _, (user1, user2) = sala_y_clients
    assert sala.id in salas_blackjack
    estado = salas_blackjack[sala.id]

    assert user1.id in estado["jugadores"], "Primer usuario debe estar registrado en memoria"
    assert user2.id in estado["jugadores"], "Segundo usuario debe estar registrado en memoria"
    assert estado["orden_turnos"] == [user1.id, user2.id]
    assert estado["fase"] == "esperando_apuestas"
    assert estado["turno_idx"] is None
    assert estado["dealer"] == []


def test_apostar_descuenta_saldo_y_rechaza_insuficiente(app, sala_y_clients):
    sala, (c1, c2), (user1, user2) = sala_y_clients

    c1.emit("apostar_blackjack", {"sala_id": sala.id, "cantidad": 20})
    with app.app_context():
        refreshed = User.query.get(user1.id)
        assert refreshed.balance == pytest.approx(130.0)

    c2.get_received()  # limpiar cola previa
    c2.emit("apostar_blackjack", {"sala_id": sala.id, "cantidad": 9999})
    mensajes = c2.get_received()
    assert any(m["name"] == "error_blackjack" for m in mensajes), "Debe emitir error por saldo insuficiente"


def test_iniciar_ronda_requiere_dos_apuestas_y_reparte_cartas(app, sala_y_clients):
    sala, (c1, c2), _ = sala_y_clients

    c1.emit("apostar_blackjack", {"sala_id": sala.id, "cantidad": 15})
    c1.emit("iniciar_ronda_blackjack", {"sala_id": sala.id})
    recibidos = c1.get_received()
    assert any(evt["name"] == "error_blackjack" for evt in recibidos), "Debe rechazarse si solo apuesta un jugador"

    c2.emit("apostar_blackjack", {"sala_id": sala.id, "cantidad": 10})
    c1.emit("iniciar_ronda_blackjack", {"sala_id": sala.id})

    estado = salas_blackjack[sala.id]
    assert estado["fase"] == "turnos"
    assert estado["dealer"] and len(estado["dealer"]) == 2
    activos = [j for j in estado["jugadores"].values() if j["apuesta"] > 0]
    assert all(len(j["mano"]) == 2 for j in activos)
    assert estado["turno_idx"] == 0
    assert estado["deadline_ts"] is not None


def test_flujo_hit_stand_resuelve_y_actualiza_balances(app, sala_y_clients):
    sala, (c1, c2), (user1, user2) = sala_y_clients
    estado = salas_blackjack[sala.id]

    estado["mazo"] = deque([
        ("5", "S", 5), ("10", "H", 10),
        ("9", "C", 9), ("2", "D", 2),
        ("8", "C", 8), ("7", "H", 7),
        ("K", "S", 10),
        ("6", "H", 6),
    ])

    c1.emit("apostar_blackjack", {"sala_id": sala.id, "cantidad": 10})
    c2.emit("apostar_blackjack", {"sala_id": sala.id, "cantidad": 10})
    c1.emit("iniciar_ronda_blackjack", {"sala_id": sala.id})

    estado = salas_blackjack[sala.id]
    assert valor_mano(estado["jugadores"][user1.id]["mano"]) == 11
    assert valor_mano(estado["jugadores"][user2.id]["mano"]) == 15
    assert valor_mano(estado["dealer"]) == 15

    c1.emit("hit_blackjack", {"sala_id": sala.id})
    estado = salas_blackjack[sala.id]
    assert valor_mano(estado["jugadores"][user1.id]["mano"]) == 21
    assert estado["turno_idx"] == 0

    c1.emit("stand_blackjack", {"sala_id": sala.id})
    estado = salas_blackjack[sala.id]
    assert estado["turno_idx"] == 1
    assert estado["fase"] == "turnos"

    c2.emit("stand_blackjack", {"sala_id": sala.id})
    estado = salas_blackjack[sala.id]
    assert estado["fase"] == "fin"
    assert valor_mano(estado["dealer"]) == 21

    with app.app_context():
        u1 = User.query.get(user1.id)
        u2 = User.query.get(user2.id)
        assert u1.balance == pytest.approx(150.0)
        assert u2.balance == pytest.approx(110.0)


def test_revancha_resetea_estado_y_mazo(app, sala_y_clients):
    sala, (c1, c2), _ = sala_y_clients

    c1.emit("apostar_blackjack", {"sala_id": sala.id, "cantidad": 5})
    c2.emit("apostar_blackjack", {"sala_id": sala.id, "cantidad": 5})
    c1.emit("iniciar_ronda_blackjack", {"sala_id": sala.id})
    c1.emit("stand_blackjack", {"sala_id": sala.id})
    c2.emit("stand_blackjack", {"sala_id": sala.id})

    estado = salas_blackjack[sala.id]
    assert estado["fase"] == "fin"

    c1.emit("voto_revancha", {"sala_id": sala.id})
    c2.emit("voto_revancha", {"sala_id": sala.id})

    estado = salas_blackjack[sala.id]
    assert estado["fase"] == "esperando_apuestas"
    assert estado["dealer"] == []
    assert all(j["mano"] == [] for j in estado["jugadores"].values())
    assert all(j["apuesta"] == 0 for j in estado["jugadores"].values())
    assert estado["votos_revancha"] == set()


def test_no_permite_mas_de_cuatro_jugadores(app, sala_y_clients):
    sala, (c1, c2), (user1, user2) = sala_y_clients

    extras = []
    clients_extra = []
    try:
        # Se pueden unir dos jugadores adicionales (total 4)
        for idx in range(3, 5):
            usuario = _crear_usuario(app, f"bj_user_{idx}", balance=50.0)
            extras.append(usuario)
            cli = _socket_client_para_usuario(app, usuario)
            clients_extra.append(cli)
            cli.emit("join_sala_blackjack", {"sala_id": sala.id})

        estado = salas_blackjack[sala.id]
        assert len(estado["jugadores"]) == 4
        assert estado["orden_turnos"] == [user1.id, user2.id, extras[0].id, extras[1].id]

        # Quinto jugador debe recibir error y no entrar en la sala
        u5 = _crear_usuario(app, "bj_user_5", balance=50.0)
        extras.append(u5)
        c5 = _socket_client_para_usuario(app, u5)
        clients_extra.append(c5)
        c5.emit("join_sala_blackjack", {"sala_id": sala.id})
        mensajes = c5.get_received()
        assert any(evt["name"] == "error_blackjack" for evt in mensajes), "Debe avisar sala llena"
        assert len(estado["jugadores"]) == 4, "No debe agregar quinto jugador"
    finally:
        for cli in clients_extra:
            try:
                cli.disconnect()
            except Exception:
                pass
        with app.app_context():
            for u in extras:
                db.session.delete(User.query.get(u.id))
            db.session.commit()
