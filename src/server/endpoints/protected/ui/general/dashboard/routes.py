from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import SalaMultijugador
from endpoints.protected.ui.general.salas_espera.routes import obtener_pagina_salas

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def home():
    salas_pag = obtener_pagina_salas(3)

    # Necesario para actualización automática de la lista de salas.
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("salas_espera/lista_salas.html", salas=salas_pag, compact_view=True)

    return render_template("pages/casino/dashboard/dashboard.html", realtime_required=True, user=current_user, salas=salas_pag)