from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import SalaMultijugador

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def home():
    page = request.args.get("page", 1, type=int)
    salas_pag = SalaMultijugador.query.paginate(page=page, per_page=3)
    return render_template("dashboard.html", user=current_user, salas=salas_pag)