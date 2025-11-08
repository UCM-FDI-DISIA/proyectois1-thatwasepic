from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, SalaMultijugador, UsuarioSala

# CAMBIAR NOMBRE DEL BLUEPRINT
bp = Blueprint('salas_espera', __name__)

# Lista de juegos permitidos con sus capacidades máximas
JUEGOS_PERMITIDOS = {
    'blackjack': {'nombre': 'Blackjack', 'max_jugadores': 4},
    'ruleta': {'nombre': 'Ruleta', 'max_jugadores': 4},
    'coinflip': {'nombre': 'Coinflip', 'max_jugadores': 2},
    'carrera_caballos': {'nombre': 'Carrera de Caballos', 'max_jugadores': 4}
}

# CAMBIAR RUTA PRINCIPAL
@bp.route('/salas-espera')
@login_required
def lobby():
    """Página principal del lobby de salas de espera"""
    page = request.args.get("page", 1, type=int)
    salas_pag = SalaMultijugador.query.paginate(page=page, per_page=8)
    return render_template('salas_espera/lobby.html', salas=salas_pag, juegos_permitidos=JUEGOS_PERMITIDOS)

# CAMBIAR RUTA
@bp.route('/salas-espera/crear-sala', methods=['POST'])
@login_required
def crear_sala():
    """Crear una nueva sala de juego"""
    nombre = request.form.get('nombre')
    juego = request.form.get('juego')
    capacidad = int(request.form.get('capacidad', 4))
    apuesta_minima = float(request.form.get('apuesta_minima', 10.0))
    
    # Validaciones
    if not nombre or not juego:
        flash('Nombre y juego son requeridos', 'error')
        return redirect(url_for('salas_espera.lobby'))  # CAMBIAR REFERENCIA
    
    # Validar que el juego esté permitido
    if juego not in JUEGOS_PERMITIDOS:
        flash('Juego no permitido', 'error')
        return redirect(url_for('salas_espera.lobby'))  # CAMBIAR REFERENCIA
    
    # Validar capacidad según el juego
    max_jugadores = JUEGOS_PERMITIDOS[juego]['max_jugadores']
    if capacidad < 2 or capacidad > max_jugadores:
        flash(f'La capacidad para {JUEGOS_PERMITIDOS[juego]["nombre"]} debe ser entre 2 y {max_jugadores} jugadores', 'error')
        return redirect(url_for('salas_espera.lobby'))  # CAMBIAR REFERENCIA
    
    # Crear sala
    nueva_sala = SalaMultijugador(
        nombre=nombre,
        juego=juego,
        capacidad=capacidad,
        apuesta_minima=apuesta_minima,
        creador_id=current_user.id
    )
    
    db.session.add(nueva_sala)
    db.session.commit()
    
    # El creador se une automáticamente
    usuario_sala = UsuarioSala(
        usuario_id=current_user.id,
        sala_id=nueva_sala.id,
        posicion=0
    )
    db.session.add(usuario_sala)
    nueva_sala.jugadores_actuales = 1
    db.session.commit()
    
    flash('¡Sala creada exitosamente!', 'success')
    return redirect(url_for('salas_espera.sala', sala_id=nueva_sala.id))  # CAMBIAR REFERENCIA

# CAMBIAR RUTA
@bp.route('/salas-espera/sala/<int:sala_id>')
@login_required
def sala(sala_id):
    """Página de una sala específica - REDIRECCIÓN AUTOMÁTICA"""
    sala = SalaMultijugador.query.get_or_404(sala_id)
    
    # Verificar si el usuario está en la sala
    usuario_en_sala = UsuarioSala.query.filter_by(
        usuario_id=current_user.id, 
        sala_id=sala_id
    ).first()
    
    if not usuario_en_sala:
        if sala.jugadores_actuales >= sala.capacidad:
            flash('La sala está llena', 'error')
            return redirect(url_for('salas_espera.lobby'))  # CAMBIAR REFERENCIA
        
        # Unirse a la sala
        usuario_sala = UsuarioSala(
            usuario_id=current_user.id,
            sala_id=sala_id,
            posicion=sala.jugadores_actuales
        )
        db.session.add(usuario_sala)
        sala.jugadores_actuales += 1
        db.session.commit()
    
    # REDIRECCIÓN AUTOMÁTICA cuando la sala esté llena y el creador inicie
    if sala.estado == 'jugando':
        if sala.juego == 'coinflip':
            return redirect(url_for('api_multijugador_coinflip.sala_coinflip', sala_id=sala_id))
        # Aquí agregarías redirecciones para otros juegos
    
    # Si no está jugando, mostrar sala de espera
    return render_template('salas_espera/sala_base.html', sala=sala)  # CAMBIAR RUTA TEMPLATE

# CAMBIAR RUTA
@bp.route('/salas-espera/salir-sala/<int:sala_id>', methods=['POST'])
@login_required
def salir_sala(sala_id):
    """Salir de una sala"""
    usuario_sala = UsuarioSala.query.filter_by(
        usuario_id=current_user.id, 
        sala_id=sala_id
    ).first()
    
    if usuario_sala:
        sala = SalaMultijugador.query.get(sala_id)
        sala.jugadores_actuales -= 1
        
        # Si no quedan jugadores, eliminar la sala
        if sala.jugadores_actuales == 0:
            db.session.delete(sala)
        else:
            db.session.delete(usuario_sala)
        
        db.session.commit()
        flash('Has salido de la sala', 'info')
    
    return redirect(url_for('salas_espera.lobby'))  # CAMBIAR REFERENCIA