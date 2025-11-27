from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, SalaMultijugador, UsuarioSala
from datetime import datetime, timedelta

bp = Blueprint('salas_espera', __name__)

JUEGOS_PERMITIDOS = {
    'blackjack': {'nombre': 'Blackjack', 'max_jugadores': 4},
    'ruleta': {'nombre': 'Ruleta', 'max_jugadores': 4},
    'coinflip': {'nombre': 'Coinflip', 'max_jugadores': 2},
    'caballos': {'nombre': 'Carrera de Caballos', 'max_jugadores': 4},
    'poker': {'nombre': 'Póker', 'max_jugadores': 6},
}


def limpiar_salas_antiguas():
    """Eliminar salas terminadas o con usuarios desconectados por mucho tiempo"""
    una_hora_atras = datetime.utcnow() - timedelta(hours=1)
    cinco_minutos_atras = datetime.utcnow() - timedelta(minutes=5)
    
    # Eliminar salas terminadas con más de 1 hora
    salas_terminadas = SalaMultijugador.query.filter(
        SalaMultijugador.estado == 'terminada',
        SalaMultijugador.fecha_creacion < una_hora_atras
    ).all()
    
    # Eliminar usuarios desconectados por más de 5 minutos
    usuarios_desconectados = UsuarioSala.query.filter(
        UsuarioSala.estado == 'desconectado',
        UsuarioSala.ultima_conexion < cinco_minutos_atras
    ).all()
    
    for usuario_sala in usuarios_desconectados:
        print(f"🧹 Limpieza: eliminando usuario desconectado {usuario_sala.usuario_id}")
        sala = SalaMultijugador.query.get(usuario_sala.sala_id)
        if sala:
            sala.jugadores_actuales -= 1
        db.session.delete(usuario_sala)
    
    # Eliminar salas vacías
    salas_vacias = SalaMultijugador.query.filter(
        SalaMultijugador.jugadores_actuales == 0,
        SalaMultijugador.fecha_creacion < una_hora_atras
    ).all()
    
    salas_a_eliminar = salas_terminadas + salas_vacias
    
    for sala in salas_a_eliminar:
        print(f"🧹 Limpieza: eliminando sala vacía {sala.id}")
        db.session.delete(sala)
    
    if salas_a_eliminar or usuarios_desconectados:
        db.session.commit()
        print(f"🧹 Limpieza: resumen: {len(salas_a_eliminar)} salas, {len(usuarios_desconectados)} usuarios")

def obtener_pagina_salas(num_por_pagina):
    limpiar_salas_antiguas()
    
    page = request.args.get("page", 1, type=int)
    
    salas_pag = SalaMultijugador.query.filter(
        SalaMultijugador.estado == 'esperando',
        SalaMultijugador.jugadores_actuales > 0
    ).paginate(page=page, per_page=num_por_pagina)

    return salas_pag

@bp.route('/salas-espera')
@login_required
def lobby():
    """Página principal del lobby de salas de espera"""    
    salas_pag = obtener_pagina_salas(8)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("partials/lista_salas.html", salas=salas_pag)

    return render_template('pages/casino/salas/lobby.html', realtime_required=True, salas=salas_pag, juegos_permitidos=JUEGOS_PERMITIDOS)

@bp.route('/salas-espera/crear-sala', methods=['POST'])
@login_required
def crear_sala():
    """Crear una nueva sala de juego"""
    nombre = request.form.get('nombre')
    juego = request.form.get('juego')
    capacidad = int(request.form.get('capacidad', 4))
    apuesta_minima = float(request.form.get('apuesta_minima', 10.0))
    
    if not nombre or not juego:
        flash('Nombre y juego son requeridos', 'error')
        return redirect(url_for('salas_espera.lobby'))
    
    if juego not in JUEGOS_PERMITIDOS:
        flash('Juego no permitido', 'error')
        return redirect(url_for('salas_espera.lobby'))
    
    max_jugadores = JUEGOS_PERMITIDOS[juego]['max_jugadores']
    if capacidad < 2 or capacidad > max_jugadores:
        flash(f'La capacidad para {JUEGOS_PERMITIDOS[juego]["nombre"]} debe ser entre 2 y {max_jugadores} jugadores', 'error')
        return redirect(url_for('salas_espera.lobby'))
    
    nueva_sala = SalaMultijugador(
        nombre=nombre,
        juego=juego,
        capacidad=capacidad,
        apuesta_minima=apuesta_minima,
        creador_id=current_user.id
    )
    
    db.session.add(nueva_sala)
    db.session.commit()
    
    usuario_sala = UsuarioSala(
        usuario_id=current_user.id,
        sala_id=nueva_sala.id,
        posicion=0,
        estado='conectado'
    )
    db.session.add(usuario_sala)
    nueva_sala.jugadores_actuales = 1
    db.session.commit()
    
    flash('¡Sala creada exitosamente!', 'success')
    return redirect(url_for('salas_espera.sala', sala_id=nueva_sala.id))

@bp.route('/salas-espera/sala/<int:sala_id>')
@login_required
def sala(sala_id):
    """Página de una sala específica - CON REDIRECCIÓN AUTOMÁTICA ORIGINAL"""
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    if sala.estado == 'terminada':
        flash('Esta sala ya ha terminado', 'info')
        return redirect(url_for('salas_espera.lobby'))
    
    usuario_en_sala = UsuarioSala.query.filter_by(
        usuario_id=current_user.id, 
        sala_id=sala_id
    ).first()
    
    if not usuario_en_sala:
        if sala.jugadores_actuales >= sala.capacidad:
            flash('La sala está llena', 'error')
            return redirect(url_for('salas_espera.lobby'))
        
        usuario_sala = UsuarioSala(
            usuario_id=current_user.id,
            sala_id=sala_id,
            posicion=sala.jugadores_actuales,
            estado='conectado'
        )
        db.session.add(usuario_sala)
        sala.jugadores_actuales += 1
        db.session.commit()
    else:
        usuario_en_sala.estado = 'conectado'
        usuario_en_sala.ultima_conexion = datetime.utcnow()
        db.session.commit()
    
    # REDIRECCIÓN CORREGIDA - MANTENER LA ORIGINAL
    if sala.estado == 'jugando':
        print(f"🔄 Redirigiendo automáticamente a juego: {sala.juego}")
        if sala.juego == 'coinflip':
            return redirect(f'/api/multijugador/coinflip/sala/{sala_id}')
        elif sala.juego == 'blackjack':
            return redirect(f'/blackjack/sala/{sala_id}')
        if sala.juego == 'poker':
            return redirect(f'/multijugador/partida/poker/{sala.id}')
        elif sala.juego == 'ruleta':
            return redirect(f'/ruleta/sala/{sala_id}')
        elif sala.juego == 'caballos':
            return redirect(f'/api/multijugador/caballos/sala/{sala_id}')
        else:
            return redirect(f'/multijugador/partida/{sala.juego}/{sala_id}')
    
    return render_template('pages/casino/salas/sala.html', sala=sala, realtime_required=True)

@bp.route('/salas-espera/salir-sala/<int:sala_id>', methods=['POST'])
@login_required
def salir_sala(sala_id):
    """Salir completamente de una sala"""
    usuario_sala = UsuarioSala.query.filter_by(
        usuario_id=current_user.id, 
        sala_id=sala_id
    ).first()
    
    if usuario_sala:
        sala = SalaMultijugador.query.get(sala_id)
        sala.jugadores_actuales -= 1
        db.session.delete(usuario_sala)
        
        if sala.jugadores_actuales == 0:
            sala.estado = 'terminada'
        
        db.session.commit()
        flash('Has salido de la sala', 'info')
    
    return redirect(url_for('salas_espera.lobby'))

@bp.route('/api/multijugador/terminar-sala/<int:sala_id>', methods=['POST'])
@login_required
def terminar_sala(sala_id):
    """Marcar una sala como terminada"""
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    if sala.creador_id != current_user.id:
        return jsonify({'error': 'No tienes permisos para terminar esta sala'}), 403
    
    sala.estado = 'terminada'
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Sala marcada como terminada'})