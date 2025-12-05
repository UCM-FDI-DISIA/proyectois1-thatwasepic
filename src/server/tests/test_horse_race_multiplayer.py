import pytest
from flask_socketio import SocketIOTestClient

from app import socketio
from models import db, SalaMultijugador, UsuarioSala, User, Apuesta
from endpoints.protected.api.juegos.multiplayer.caballos import socket_handlers as caballos_handlers


@pytest.fixture
def sala_multijugador_caballos(app, test_user):
    """Crear sala multijugador de caballos donde el usuario es creador."""
    with app.app_context():
        sala = SalaMultijugador(
            nombre="Sala test caballos",
            juego="caballos",
            capacidad=4,
            creador_id=test_user.id,
            apuesta_minima=10.0,
        )
        db.session.add(sala)
        db.session.commit()

        # Registrar al creador como jugador conectado
        usuario_sala = UsuarioSala(
            usuario_id=test_user.id,
            sala_id=sala.id,
            estado="conectado",
        )
        db.session.add(usuario_sala)
        db.session.commit()

        yield sala


def _login_and_socket_client(app, client, username, password) -> SocketIOTestClient:
    """Login via HTTP client and return a bound SocketIO test client."""
    resp = client.post("/login", data={"username": username, "password": password}, follow_redirects=True)
    assert resp.status_code == 200
    return socketio.test_client(app, flask_test_client=client, namespace="/")


def test_join_caballos_room_emits_state(app, client, sala_multijugador_caballos, test_user, monkeypatch):
    caballos_handlers.salas_caballos.clear()
    sio_client = _login_and_socket_client(app, client, test_user.username, "password123")

    sio_client.emit("join_caballos_room", {"sala_id": sala_multijugador_caballos.id})
    events = sio_client.get_received()

    estado_events = [e for e in events if e["name"] == "estado_sala_actualizado"]
    assert estado_events, "join_caballos_room should broadcast estado_sala_actualizado"
    payload = estado_events[-1]["args"][0]
    assert any(j["id"] == test_user.id for j in payload["jugadores"])


def test_place_bet_deducts_balance_and_notifies(app, client, sala_multijugador_caballos, test_user, monkeypatch):
    caballos_handlers.salas_caballos.clear()
    sio_client = _login_and_socket_client(app, client, test_user.username, "password123")

    # Entrar a la sala y limpiar eventos previos
    sio_client.emit("join_caballos_room", {"sala_id": sala_multijugador_caballos.id})
    sio_client.get_received()

    apuesta = 100
    sio_client.emit("caballos_place_bet", {"sala_id": sala_multijugador_caballos.id, "caballo": 1, "cantidad": apuesta})
    events = sio_client.get_received()

    names = [e["name"] for e in events]
    assert "estado_sala_actualizado" in names
    assert "todos_apostaron" in names

    with app.app_context():
        user = User.query.get(test_user.id)
        assert user.balance == pytest.approx(test_user.balance - apuesta)


def test_iniciar_carrera_emits_results_and_creates_apuestas(
    app, client, sala_multijugador_caballos, test_user, monkeypatch
):
    caballos_handlers.salas_caballos.clear()
    # Hacer determinista el ganador y evitar esperas largas
    monkeypatch.setattr(caballos_handlers, "elegir_ganador", lambda: 1)
    socketio_instance = app.extensions["socketio"]
    monkeypatch.setattr(socketio_instance, "sleep", lambda secs: None)
    monkeypatch.setattr(socketio_instance, "start_background_task", lambda fn, *a, **k: fn(*a, **k))

    sio_client = _login_and_socket_client(app, client, test_user.username, "password123")
    sio_client.emit("join_caballos_room", {"sala_id": sala_multijugador_caballos.id})
    sio_client.get_received()

    sio_client.emit(
        "caballos_place_bet",
        {"sala_id": sala_multijugador_caballos.id, "caballo": 1, "cantidad": 50},
    )
    sio_client.get_received()

    sio_client.emit("iniciar_carrera", {"sala_id": sala_multijugador_caballos.id})
    events = sio_client.get_received()

    names = [e["name"] for e in events]
    assert "start_race" in names
    race_result_events = [e for e in events if e["name"] == "race_result"]
    assert race_result_events, "race_result should be emitted after iniciar_carrera"
    resultados = race_result_events[0]["args"][0]["resultados"]

    keys = set(resultados.keys())
    assert str(test_user.id) in keys or test_user.id in keys

    with app.app_context():
        apuesta = (
            Apuesta.query.filter_by(user_id=test_user.id, juego="caballos")
            .order_by(Apuesta.id.desc())
            .first()
        )
        assert apuesta is not None
        assert apuesta.resultado in ("ganada", "perdida")
        assert apuesta.cantidad == 50
