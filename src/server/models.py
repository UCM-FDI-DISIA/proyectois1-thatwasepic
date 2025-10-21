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
    partidas_jugadas = db.Column(db.Integer, default=0)
    partidas_ganadas = db.Column(db.Integer, default=0)
    ganancia_total = db.Column(db.Float, default=0.0)
    apuesta_total = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f'<Estadistica {self.juego} {self.partidas_jugadas}>'