from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

bp = Blueprint('blackjack', __name__)

@bp.route('/blackjack')
@login_required
def home():
    return render_template('blackjack.html')