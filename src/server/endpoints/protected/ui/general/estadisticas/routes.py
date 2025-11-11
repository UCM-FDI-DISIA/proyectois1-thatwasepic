from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import Apuesta, Estadistica

bp = Blueprint('estadisticas', __name__)

@bp.route('/estadisticas')
@login_required
def home():
    stats = Estadistica.query.filter_by(user_id=current_user.id).all()
    apuestas_recientes = Apuesta.query.filter_by(user_id=current_user.id).order_by(Apuesta.fecha.desc()).limit(10).all()
    
    return render_template('estadisticas.html', 
                         stats=stats, 
                         apuestas=apuestas_recientes,
                         user=current_user)