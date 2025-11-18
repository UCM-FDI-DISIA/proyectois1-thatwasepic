import random
import json
from datetime import datetime

from flask_login import current_user
from flask_socketio import join_room, leave_room, emit

from models import db, SalaMultijugador, UsuarioSala, PartidaMultijugador

# ⚠️ Si este archivo no está en el mismo paquete que routes.py,
# cambia el import al path correcto
from .routes import (
    _obtener_o_crear_partida,
    _cargar_estado,
    _guardar_estado,
    _sanitizar_estado_para_usuario,
    _crear_mazo,          # reutilizamos tu mismo mazo (dict con valor/palo)
    _resolver_si_todos_han_actuado
)


def init_socket_handlers(socketio):
    """
    Llamar una vez desde app.py:
        from socket_handlers_poker import init_poker_socket_handlers
        init_poker_socket_handlers(socketio)
    """

    # --------- helpers internos ---------

    def _nombre_room_poker(sala_id: int) -> str:
        return f"poker_{sala_id}"

    def _es_miembro_de_sala(usuario_id: int, sala_id: int) -> bool:
        return UsuarioSala.query.filter_by(
            sala_id=sala_id,
            usuario_id=usuario_id
        ).first() is not None

    def _crear_estado_nueva_mano(sala: SalaMultijugador) -> dict:
        """
        Misma estructura que usas en iniciar_mano() de routes.py
        pero aquí para sockets.
        """
        mazo = _crear_mazo()
        random.shuffle(mazo)

        comunitarias = [mazo.pop() for _ in range(5)]

        jugadores_estado = {}
        jugadores_sala = UsuarioSala.query.filter_by(sala_id=sala.id).all()

        for us in jugadores_sala:
            cartas = [mazo.pop(), mazo.pop()]
            jugadores_estado[str(us.usuario_id)] = {
                'user_id': us.usuario_id,
                'username': getattr(us, "player", None).username
                    if hasattr(us, "player") and us.player
                    else f'Usuario {us.usuario_id}',
                'stack': 1000.0,
                'apuesta_actual': 0.0,
                'estado': 'activo',
                'ultima_accion': '---',
                'ha_actuado': False,
                'cartas': cartas,
                'cartas_visibles': None
            }

        estado = {
            'juego': 'poker',
            'fase': 'apuestas',
            'cartas_comunitarias': comunitarias,
            'jugadores': jugadores_estado,
            'bote': 0.0,
            'ganador': None
        }

        return estado

    def _crear_o_reiniciar_partida_poker(sala: SalaMultijugador) -> PartidaMultijugador:
        """
        Igual idea que en routes.py pero usando el estado con cartas ya repartidas.
        """
        partida = PartidaMultijugador.query.filter_by(
            sala_id=sala.id,
            estado='activa'
        ).order_by(PartidaMultijugador.fecha_inicio.desc()).first()

        nuevo_estado = _crear_estado_nueva_mano(sala)

        if partida is None:
            partida = PartidaMultijugador(
                sala_id=sala.id,
                estado='activa',
                datos_juego=json.dumps(nuevo_estado)
            )
            db.session.add(partida)
        else:
            partida.datos_juego = json.dumps(nuevo_estado)

        db.session.commit()
        return partida

    # --------- eventos socket.io ---------

    @socketio.on("poker_join")
    def handle_poker_join(data):
        if not current_user.is_authenticated:
            emit("poker_error", {"mensaje": "No autenticado"})
            return

        sala_id = data.get("sala_id")
        if sala_id is None:
            emit("poker_error", {"mensaje": "Falta sala_id"})
            return

        sala = SalaMultijugador.query.get(sala_id)
        if sala is None:
            emit("poker_error", {"mensaje": "Sala no encontrada"})
            return

        if not _es_miembro_de_sala(current_user.id, sala_id):
            emit("poker_error", {"mensaje": "No perteneces a esta sala"})
            return

        room = _nombre_room_poker(sala_id)
        join_room(room)

        # Recuperamos/creamos partida como en routes.py
        partida = _obtener_o_crear_partida(sala)
        estado = _cargar_estado(partida)

        emit("poker_estado", _sanitizar_estado_para_usuario(estado, current_user.id))

    @socketio.on("poker_leave")
    def handle_poker_leave(data):
        if not current_user.is_authenticated:
            return

        sala_id = data.get("sala_id")
        if sala_id is None:
            return

        room = _nombre_room_poker(sala_id)
        leave_room(room)

    @socketio.on("poker_iniciar")
    def handle_poker_iniciar(data):
        if not current_user.is_authenticated:
            emit("poker_error", {"mensaje": "No autenticado"})
            return

        sala_id = data.get("sala_id")
        if sala_id is None:
            emit("poker_error", {"mensaje": "Falta sala_id"})
            return

        sala = SalaMultijugador.query.get(sala_id)
        if sala is None:
            emit("poker_error", {"mensaje": "Sala no encontrada"})
            return

        # Solo el creador de la sala puede iniciar
        if sala.creador_id != current_user.id:
            emit("poker_error", {"mensaje": "Solo el creador puede iniciar la mano"})
            return

        if not _es_miembro_de_sala(current_user.id, sala_id):
            emit("poker_error", {"mensaje": "No perteneces a esta sala"})
            return

        partida = _crear_o_reiniciar_partida_poker(sala)
        estado = _cargar_estado(partida)

        room = _nombre_room_poker(sala_id)
        socketio.emit(
            "poker_estado",
            _sanitizar_estado_para_usuario(estado, current_user.id),
            room=room
        )

    @socketio.on("poker_accion")
    def handle_poker_accion(data):
        if not current_user.is_authenticated:
            emit("poker_error", {"mensaje": "No autenticado"})
            return

        sala_id = data.get("sala_id")
        if sala_id is None:
            emit("poker_error", {"mensaje": "Falta sala_id"})
            return

        accion = data.get("accion")
        cantidad = data.get("cantidad", 0)

        if accion not in ("apostar", "pasar", "retirarse"):
            emit("poker_error", {"mensaje": "Acción no válida"})
            return

        sala = SalaMultijugador.query.get(sala_id)
        if sala is None:
            emit("poker_error", {"mensaje": "Sala no encontrada"})
            return

        if not _es_miembro_de_sala(current_user.id, sala_id):
            emit("poker_error", {"mensaje": "No perteneces a esta sala"})
            return

        partida = _obtener_o_crear_partida(sala)
        estado = _cargar_estado(partida)

        if estado.get('fase') not in ('apuestas',):
            emit("poker_error", {"mensaje": "No se pueden realizar acciones ahora"})
            return

        jugadores = estado.setdefault('jugadores', {})
        jugador = jugadores.get(str(current_user.id))
        if jugador is None:
            emit("poker_error", {"mensaje": "No estás registrado como jugador en esta mano"})
            return

        if jugador.get('estado') != 'activo':
            emit("poker_error", {"mensaje": "Ya no participas en esta mano"})
            return

        # ----- aplicar acción -----
        if accion == "apostar":
            try:
                cantidad = float(cantidad)
            except (ValueError, TypeError):
                emit("poker_error", {"mensaje": "Cantidad de apuesta no válida"})
                return
            if cantidad <= 0:
                emit("poker_error", {"mensaje": "La cantidad debe ser positiva"})
                return

            apuesta_minima = sala.apuesta_minima or 10.0
            if cantidad < apuesta_minima:
                emit("poker_error", {"mensaje": f"La apuesta mínima es {apuesta_minima}"})
                return

            jugador['apuesta_actual'] = float(jugador.get('apuesta_actual', 0.0)) + cantidad
            estado['bote'] = float(estado.get('bote', 0.0)) + cantidad
            jugador['ultima_accion'] = f'apuesta {cantidad:.2f}€'

        elif accion == "pasar":
            jugador['ultima_accion'] = 'pasa'

        elif accion == "retirarse":
            jugador['estado'] = 'retirado'
            jugador['ultima_accion'] = 'se retira'

        jugador['ha_actuado'] = True

        # Resolver mano si todos han actuado (reutilizamos tu función)
        _resolver_si_todos_han_actuado(estado)
        _guardar_estado(partida, estado)

        room = _nombre_room_poker(sala_id)
        socketio.emit(
            "poker_estado",
            _sanitizar_estado_para_usuario(estado, current_user.id),
            room=room
        )
