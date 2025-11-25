# routes.py - Versión actualizada con edición y eliminación
from flask import Blueprint, render_template, request, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Apuesta, Estadistica, SalaMultijugador, UsuarioSala, IngresoFondos
from endpoints.protected.ui.admin.utils import require_admin
from datetime import datetime, timedelta
from endpoints.protected.ui.general.estadisticas.routes import obtener_pagina_transacciones

bp = Blueprint('admin_usuarios', __name__)

@bp.route('/admin/usuarios')
@login_required
@require_admin()
def home():
    """Gestión de usuarios con estadísticas"""
    try:
        usuarios = User.query.order_by(User.created_at.desc()).all()
        
        # Calcular estadísticas (solo balances no negativos)
        usuarios_no_negativos = [user for user in usuarios if user.balance >= 0]
        total_balance = sum(user.balance for user in usuarios_no_negativos)
        usuarios_positivos = sum(1 for user in usuarios_no_negativos if user.balance > 0)
        usuarios_negativos = sum(1 for user in usuarios if user.balance < 0)  # Solo para info
        usuarios_cero = sum(1 for user in usuarios_no_negativos if user.balance == 0)
        
        # Usuarios registrados hoy
        hoy = datetime.now().date()
        usuarios_hoy = sum(1 for user in usuarios_no_negativos if user.created_at.date() == hoy)
        
        # Usuarios activos este mes
        hace_30_dias = datetime.now() - timedelta(days=30)
        usuarios_activos = sum(1 for user in usuarios_no_negativos if user.created_at >= hace_30_dias)
        
        return render_template('pages/admin/usuarios/usuarios.html', 
                             usuarios=usuarios_no_negativos,  # Solo usuarios no negativos
                             total_balance=total_balance,
                             usuarios_positivos=usuarios_positivos,
                             usuarios_negativos=usuarios_negativos,
                             usuarios_cero=usuarios_cero,
                             usuarios_hoy=usuarios_hoy,
                             usuarios_activos=usuarios_activos,
                             now=datetime.now())
                             
    except Exception as e:
        flash(f'Error al cargar la gestión de usuarios: {str(e)}', 'error')
        return redirect(url_for('admin_panel.home'))

@bp.route('/admin/usuarios/<int:user_id>/editar', methods=['POST'])
@login_required
@require_admin()
def editar_usuario(user_id):
    """Endpoint para editar usuario"""
    try:
        usuario = User.query.get_or_404(user_id)
        data = request.form
        
        # Validar que no se esté editando a sí mismo para ciertos campos
        if usuario.id == current_user.id:
            flash('No puedes modificar tu propio usuario desde aquí', 'info')
            return redirect(request.referrer or url_for('admin_usuarios.home'))
        
        # Campos editables
        if 'username' in data and data['username']:
            # Verificar que el username no esté en uso
            existing_user = User.query.filter(User.username == data['username'], User.id != user_id).first()
            if existing_user:
                flash('El nombre de usuario ya está en uso', 'info')
                return redirect(request.referrer or url_for('admin_usuarios.home'))
            usuario.username = data['username']
        
        if 'email' in data and data['email']:
            # Verificar que el email no esté en uso
            existing_email = User.query.filter(User.email == data['email'], User.id != user_id).first()
            if existing_email:
                flash('El email ya está en uso', 'info')
                return redirect(request.referrer or url_for('admin_usuarios.home'))
            usuario.email = data['email']
        
        if 'balance' in data:
            try:
                nuevo_balance = float(data['balance'])
                if nuevo_balance >= 0:  # Prevenir balances negativos
                    usuario.balance = nuevo_balance
                else:
                    flash('El balance no puede ser negativo', 'info')
                    return redirect(request.referrer or url_for('admin_usuarios.home'))
            except ValueError:
                return jsonify({'success': False, 'message': 'Balance inválido'})
        
        db.session.commit()
        
        flash('Usuario actualizado correctamente', 'info')
        return redirect(request.referrer or url_for('admin_usuarios.home'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar usuario: {str(e)}', 'info')
        return redirect(request.referrer or url_for('admin_usuarios.home'))
    
@bp.route('/admin/usuarios/<int:user_id>/cambiar-password', methods=['POST'])
@login_required
@require_admin()
def cambiar_password_usuario(user_id):
    """Endpoint para cambiar contraseña de usuario"""
    try:
        usuario = User.query.get_or_404(user_id)
        data = request.form
        
        # Prevenir auto-cambio de contraseña desde admin
        if usuario.id == current_user.id:
            flash('No puedes cambiar tu propia contraseña desde aquí. Usa la opción de perfil.', 'info')
            return redirect(request.referrer or url_for('admin_usuarios.home'))
        
        if 'password' in data and data['password']:
            nueva_password = data['password'].strip()
            
            # Cambiar la contraseña
            usuario.set_password(nueva_password)
            db.session.commit()
            
            flash('Contraseña actualizada correctamente', 'info')
            return redirect(request.referrer or url_for('admin_usuarios.home'))
        else:
            flash('La nueva contraseña es requerida', 'info')
            return redirect(request.referrer or url_for('admin_usuarios.home'))
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al cambiar contraseña: {str(e)}'})
    
@bp.route('/admin/usuarios/<int:user_id>/eliminar', methods=['POST'])
@login_required
@require_admin()
def eliminar_usuario(user_id):
    """Endpoint para eliminar usuario"""
    try:
        usuario = User.query.get_or_404(user_id)
        
        # Prevenir auto-eliminación
        if usuario.id == current_user.id:
            flash('No puedes eliminar tu propio usuario', 'info')
            return redirect(url_for('admin_usuarios.home'))
        
        # Guardar información para el mensaje
        username = usuario.username
        
        # Eliminar en cascada
        # 1. Eliminar apuestas del usuario
        Apuesta.query.filter_by(user_id=user_id).delete()
        
        # 2. Eliminar estadísticas del usuario
        Estadistica.query.filter_by(user_id=user_id).delete()
        
        # 3. Eliminar relaciones con salas multijugador
        UsuarioSala.query.filter_by(usuario_id=user_id).delete()
        
        # 4. Eliminar salas creadas por el usuario y sus relaciones
        salas_creadas = SalaMultijugador.query.filter_by(creador_id=user_id).all()
        for sala in salas_creadas:
            # Eliminar jugadores de estas salas
            UsuarioSala.query.filter_by(sala_id=sala.id).delete()
            # Eliminar la sala
            db.session.delete(sala)
        
        # 5. Finalmente eliminar el usuario
        db.session.delete(usuario)
        db.session.commit()

        flash(f'Usuario "{username}" eliminado correctamente', 'info')
        return redirect(url_for('admin_usuarios.home'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'info')
        return redirect(request.referrer or url_for('admin_usuarios.home'))

@bp.route('/admin/usuarios/<int:user_id>/detalle')
@login_required
@require_admin()
def detalle_usuario(user_id):
    """Página de detalle del usuario"""
    try:
        usuario = User.query.get_or_404(user_id)
        
        # Obtener estadísticas del usuario
        estadisticas = Estadistica.query.filter_by(user_id=user_id).all()
        
        # Obtener apuestas recientes
        apuestas_recientes = Apuesta.query.filter_by(user_id=user_id)\
            .order_by(Apuesta.fecha.desc())\
            .limit(10)\
            .all()
        
        # Obtener salas creadas
        salas_creadas = SalaMultijugador.query.filter_by(creador_id=user_id)\
            .order_by(SalaMultijugador.fecha_creacion.desc())\
            .all()
        
        # Obtener salas unidas
        salas_unidas = UsuarioSala.query.filter_by(usuario_id=user_id)\
            .join(SalaMultijugador)\
            .order_by(UsuarioSala.fecha_union.desc())\
            .all()

        # Obtener historial de ingresos de fondos con paginación
        ingresos_pag = obtener_pagina_transacciones(8)

        total_ingresado = db.session.query(db.func.sum(IngresoFondos.cantidad))\
            .filter_by(user_id=current_user.id).scalar() or 0

        # Necesario para actualización automática de la lista de transacciones.
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render_template("partials/tabla_ingresos.html", ingresos=ingresos_pag)
        
        return render_template('pages/admin/usuarios/usuarios_detalle.html',
                                user=usuario,
                                stats=estadisticas,
                                apuestas=apuestas_recientes,
                                salas_creadas=salas_creadas,
                                salas_unidas=salas_unidas,
                                now=datetime.now(),
                                total_ingresado=total_ingresado,
                                ingresos=ingresos_pag,
                                admin_page=True,
                                realtime_required=True)
                             
    except Exception as e:
        flash(f'Error al cargar el detalle del usuario: {str(e)}', 'error')
        return redirect(url_for('admin_usuarios.home'))
