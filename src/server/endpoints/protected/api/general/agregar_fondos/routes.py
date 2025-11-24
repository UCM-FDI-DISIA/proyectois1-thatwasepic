from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Apuesta, Estadistica, IngresoFondos
from datetime import datetime

bp = Blueprint('agregar_fondos', __name__, url_prefix='/api')

@bp.route('/agregar_fondos', methods=['POST'])
@login_required
def agregar_fondos():
    try:
        data = request.get_json()
        
        if not data or 'cantidad' not in data:
            return jsonify({'error': 'Falta el campo "cantidad"'}), 400
            
        cantidad = float(data['cantidad'])
        
        if cantidad <= 0:
            return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
        elif cantidad > 5000:
            return jsonify({'error': 'La cantidad no puede superar $5000.00'}), 400
        
        # Registrar el ingreso
        nuevo_ingreso = IngresoFondos(
            user_id=current_user.id,
            cantidad=cantidad,
            metodo='manual',
            descripcion='Ingreso manual desde el perfil'
        )
        
        # Actualizar balance
        current_user.balance += cantidad
        
        db.session.add(nuevo_ingreso)
        db.session.commit()
        
        # Obtener los últimos 8 ingresos para actualizar la tabla
        ultimos_ingresos = IngresoFondos.query.filter_by(user_id=current_user.id)\
            .order_by(IngresoFondos.fecha.desc())\
            .limit(8).all()
        
        # Calcular nuevo total
        nuevo_total = db.session.query(db.func.sum(IngresoFondos.cantidad))\
            .filter_by(user_id=current_user.id).scalar() or 0
        
        total_transacciones = IngresoFondos.query.filter_by(user_id=current_user.id).count()
        
        html_tabla = render_template('partials/tabla_ingresos_recientes.html', 
                                    ingresos_fondos=ultimos_ingresos)
        
        return jsonify({
            'nuevo_balance': current_user.balance,
            'mensaje': f'Se agregaron ${cantidad:.2f} a tu cuenta',
            'actualizar_ui': True,
            'html_tabla': html_tabla,
            'datos_actualizados': {
                'total_ingresado': float(nuevo_total),
                'total_transacciones': total_transacciones,
                'ultimo_ingreso': f"${cantidad:.2f}",
                'ultima_fecha': nuevo_ingreso.fecha.strftime('%d/%m/%Y')
            }
        })
        
    except Exception as e:
        print(f"Error en agregar_fondos: {str(e)}")
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

# Los otros endpoints permanecen igual...
@bp.route('/account/state', methods=['GET'])
@login_required
def account_state():
    stats = Estadistica.query.filter_by(user_id=current_user.id, juego="ruleta").first()
    return jsonify({
        'ok': True,
        'balance': int(current_user.balance * 100),
        'balance_float': float(current_user.balance),
        'ruleta_stats': {
            'partidas_jugadas': stats.partidas_jugadas,
            'partidas_ganadas': stats.partidas_ganadas,
            'ganancia_total': stats.ganancia_total,
            'apuesta_total': stats.apuesta_total
        } if stats else None
    })

@bp.route('/balance', methods=['GET'])
@login_required
def obtener_balance():
    return jsonify({'balance': current_user.balance})