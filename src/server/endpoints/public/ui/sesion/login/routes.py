from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import User

bp = Blueprint('login', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('dashboard.home'))
            else:
                flash('Usuario o contraseña incorrectos')
        except Exception as e:
            flash(f'Error en el login: {str(e)}')
    
    return render_template('login.html')