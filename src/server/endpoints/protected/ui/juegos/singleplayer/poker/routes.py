from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

bp = Blueprint('poker', __name__)

@bp.route('/poker')
@login_required
def home():
    return render_template('pages/casino/juegos/singleplayer/poker.html')