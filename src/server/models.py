from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    apuestas = db.relationship('Apuesta', backref='user', lazy=True)
    estadisticas = db.relationship('Estadistica', backref='user', lazy=True)
    salas_creadas = db.relationship('SalaMultijugador', backref='owner', lazy=True)
    salas_unidas = db.relationship('UsuarioSala', backref='player', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Apuesta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    juego = db.Column(db.String(50), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    resultado = db.Column(db.String(20), nullable=False)
    ganancia = db.Column(db.Float, default=0.0)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Apuesta {self.juego} {self.cantidad} {self.resultado}>'

class Estadistica(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    juego = db.Column(db.String(50), nullable=False)
    partidas_jugadas = db.Column(db.Integer, default=0, nullable=False)
    partidas_ganadas = db.Column(db.Integer, default=0, nullable=False)  
    ganancia_total = db.Column(db.Float, default=0.0, nullable=False) 
    apuesta_total = db.Column(db.Float, default=0.0, nullable=False)

# Añadir al final de models.py
class SalaMultijugador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    juego = db.Column(db.String(50), nullable=False)
    capacidad = db.Column(db.Integer, default=4)
    jugadores_actuales = db.Column(db.Integer, default=0)
    estado = db.Column(db.String(20), default='esperando')  # esperando, jugando, terminada, eliminada
    creador_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    apuesta_minima = db.Column(db.Float, default=10.0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    jugadores = db.relationship('UsuarioSala', backref='sala_juego', lazy=True, cascade='all, delete-orphan')
    partidas = db.relationship('PartidaMultijugador', backref='partida_sala', lazy=True)

class UsuarioSala(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sala_id = db.Column(db.Integer, db.ForeignKey('sala_multijugador.id'))
    posicion = db.Column(db.Integer)
    estado = db.Column(db.String(20), default='conectado')  # conectado, desconectado
    fecha_union = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_conexion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 'jugador' está definido en User.salas_unidas
    # 'sala_juego' está definido en SalaMultijugador.jugadores

class PartidaMultijugador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sala_id = db.Column(db.Integer, db.ForeignKey('sala_multijugador.id'))
    estado = db.Column(db.String(20), default='activa')
    datos_juego = db.Column(db.Text)  # JSON serializado del estado del juego
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime)
    
    # 'partida_sala' está definido en SalaMultijugador.partidas