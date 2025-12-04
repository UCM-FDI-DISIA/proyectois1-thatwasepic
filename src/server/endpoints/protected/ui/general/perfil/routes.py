from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Estadistica
from endpoints.protected.ui.admin.utils import is_admin_user

bp = Blueprint('perfil', __name__)

@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def home():
    stats = Estadistica.query.filter_by(user_id=current_user.id).all()
    mostrar_doom = False  # Variable para controlar si mostrar Doom
    
    if request.method == 'POST':
        nuevo_username = request.form.get('username')
        nuevo_email = request.form.get('email')
        nueva_password = request.form.get('password')
        
        # Verificar si el usuario intenta cambiar a "Doom"
        if nuevo_username and nuevo_username.lower() == "doom" and nuevo_username != current_user.username:
            flash('El nombre "Doom" está reservado. No puedes usar este nombre, pero... ¡disfruta del juego!', 'warning')
            mostrar_doom = True  # Mostrar Doom aunque no cambie el nombre
        
        # Solo permitir cambios si NO es a "Doom"
        elif nuevo_username and nuevo_username != current_user.username:
            usuario_existente = User.query.filter_by(username=nuevo_username).first()
            if usuario_existente:
                flash('El nombre de usuario ya está en uso')
                return redirect(url_for('perfil.home'))
            current_user.username = nuevo_username
        
        if nuevo_email and nuevo_email != current_user.email:
            email_existente = User.query.filter_by(email=nuevo_email).first()
            if email_existente:
                flash('El email ya está en uso')
                return redirect(url_for('perfil.home'))
            current_user.email = nuevo_email
        
        if nueva_password:
            if len(nueva_password) < 6:
                flash('La contraseña debe tener al menos 6 caracteres')
                return redirect(url_for('perfil.home'))
            current_user.set_password(nueva_password)
        
        db.session.commit()
        if not mostrar_doom:  # Solo mostrar éxito si no fue intento de Doom
            flash('Perfil actualizado correctamente')
        
        # Si intentó cambiarse a Doom, recargamos la página mostrando Doom
        return render_template('pages/casino/perfil/perfil.html', 
                             user=current_user, 
                             stats=stats,
                             is_admin=is_admin_user,
                             mostrar_doom=mostrar_doom)
    
    # GET request - verificar si ya se llama Doom
    mostrar_doom = current_user.username.lower() == "doom"
    
    return render_template('pages/casino/perfil/perfil.html', 
                         user=current_user, 
                         stats=stats,
                         is_admin=is_admin_user,
                         mostrar_doom=mostrar_doom)