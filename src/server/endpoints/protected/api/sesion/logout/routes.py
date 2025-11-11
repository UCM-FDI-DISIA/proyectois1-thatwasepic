from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

bp = Blueprint('logout', __name__)

@bp.route('/logout')
@login_required
def home():
    logout_user()
    return redirect(url_for('index.home'))