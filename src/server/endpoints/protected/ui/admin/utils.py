from flask import flash, redirect, url_for
from flask_login import current_user
from functools import wraps

# CONFIGURACIÓN DE ADMINISTRADORES
ADMIN_USERS = ['admin', 'administrador', 'logbait']

def is_admin_user():
    """Verifica si el usuario actual es administrador"""
    return current_user.is_authenticated and current_user.username in ADMIN_USERS

def require_admin():
    """Decorator para requerir que el usuario sea administrador"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debes iniciar sesión para acceder al panel administrativo.')
                return redirect(url_for('login'))
            if not is_admin_user():
                flash('Acceso denegado. Se requieren privilegios de administrador.')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator