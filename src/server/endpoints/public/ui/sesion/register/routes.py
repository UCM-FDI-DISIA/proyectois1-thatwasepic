from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User

bp = Blueprint('register', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            if User.query.filter_by(username=username).first():
                flash('El nombre de usuario ya existe')
                return redirect(url_for('register.home'))
            
            if User.query.filter_by(email=email).first():
                flash('El email ya está registrado')
                return redirect(url_for('register.home'))
            
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registro exitoso. Ahora puedes iniciar sesión.')
            return redirect(url_for('login.home'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error en el registro: {str(e)}')
            return redirect(url_for('register.home'))
    
    return render_template('register.html')