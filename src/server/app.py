from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Apuesta, Estadistica
from sqlalchemy import text
import random
import os
from datetime import datetime

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

# Configuración
app.config['SECRET_KEY'] = 'clave-secreta-casino-educativo-2024'

# Configuración de base de datos - SQLite local
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///casino.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# RUTAS PÚBLICAS
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            if User.query.filter_by(username=username).first():
                flash('El nombre de usuario ya existe')
                return redirect(url_for('register'))
            
            if User.query.filter_by(email=email).first():
                flash('El email ya está registrado')
                return redirect(url_for('register'))
            
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registro exitoso. Ahora puedes iniciar sesión.')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error en el registro: {str(e)}')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Usuario o contraseña incorrectos')
        except Exception as e:
            flash(f'Error en el login: {str(e)}')
    
    return render_template('login.html')

# RUTAS PROTEGIDAS
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/estadisticas')
@login_required
def estadisticas():
    stats = Estadistica.query.filter_by(user_id=current_user.id).all()
    apuestas_recientes = Apuesta.query.filter_by(user_id=current_user.id).order_by(Apuesta.fecha.desc()).limit(10).all()
    
    return render_template('estadisticas.html', 
                         stats=stats, 
                         apuestas=apuestas_recientes,
                         user=current_user)

@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    stats = Estadistica.query.filter_by(user_id=current_user.id).all()
    
    if request.method == 'POST':
        nuevo_username = request.form.get('username')
        nuevo_email = request.form.get('email')
        nueva_password = request.form.get('password')
        
        if nuevo_username and nuevo_username != current_user.username:
            usuario_existente = User.query.filter_by(username=nuevo_username).first()
            if usuario_existente:
                flash('El nombre de usuario ya está en uso')
                return redirect(url_for('perfil'))
            current_user.username = nuevo_username
        
        if nuevo_email and nuevo_email != current_user.email:
            email_existente = User.query.filter_by(email=nuevo_email).first()
            if email_existente:
                flash('El email ya está en uso')
                return redirect(url_for('perfil'))
            current_user.email = nuevo_email
        
        if nueva_password:
            if len(nueva_password) < 6:
                flash('La contraseña debe tener al menos 6 caracteres')
                return redirect(url_for('perfil'))
            current_user.set_password(nueva_password)
        
        db.session.commit()
        flash('Perfil actualizado correctamente')
        return redirect(url_for('perfil'))
    
    return render_template('perfil.html', user=current_user, stats=stats)

# API ENDPOINTS
@app.route('/api/agregar_fondos', methods=['POST'])
@login_required
def agregar_fondos():
    data = request.get_json()
    cantidad = float(data['cantidad'])
    
    if cantidad <= 0:
        return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
    
    current_user.balance += cantidad
    db.session.commit()
    
    return jsonify({
        'nuevo_balance': current_user.balance,
        'mensaje': f'Se agregaron ${cantidad:.2f} a tu cuenta'
    })

# Inicializar la base de datos al iniciar
with app.app_context():
    try:
        db.create_all()
        print("✅ Base de datos inicializada")
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")

if __name__ == '__main__':
    app.run(debug=True)