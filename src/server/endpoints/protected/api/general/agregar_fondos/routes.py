from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Blueprint, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Apuesta, Estadistica, IngresoFondos, DepositoLimite
from datetime import datetime, timedelta
from endpoints.protected.ui.general.estadisticas.routes import obtener_pagina_transacciones

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

        # Validación del límite de depósitos
        limite = DepositoLimite.query.filter_by(user_id=current_user.id).first()

        if limite:

            ahora = datetime.utcnow()
            periodo = timedelta(days=limite.periodo_dias)

            # Mover T0 hacia adelante si los ciclos ya vencieron
            while ahora >= limite.fecha_establecido + periodo:
                limite.fecha_establecido += periodo

            db.session.commit()

            # Recalcular periodo activo
            inicio_periodo = limite.fecha_establecido

            total_periodo = (
                db.session.query(db.func.sum(IngresoFondos.cantidad))
                .filter(IngresoFondos.user_id == current_user.id)
                .filter(IngresoFondos.fecha >= inicio_periodo)
                .scalar() or 0
            )

            if total_periodo + cantidad > limite.limite_monto:
                disponible = limite.limite_monto - total_periodo
                return jsonify({
                    'error': f"Límite alcanzado. Puedes agregar hasta ${max(disponible,0):.2f} en este periodo."
                }), 403
        
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
        
        # Calcular nuevo total
        nuevo_total = db.session.query(db.func.sum(IngresoFondos.cantidad))\
            .filter_by(user_id=current_user.id).scalar() or 0
        
        total_transacciones = IngresoFondos.query.filter_by(user_id=current_user.id).count()

        # Obtener historial de ingresos de fondos con paginación
        ingresos_pag = obtener_pagina_transacciones(8, current_user.id)
        html_tabla = render_template("partials/tabla_ingresos.html", ingresos=ingresos_pag)
        
        return jsonify({
            'nuevo_balance': current_user.balance,
            'mensaje': f'Se agregaron ${cantidad:.2f} a tu cuenta.{f" Puedes agregar hasta {(limite.limite_monto - total_periodo - cantidad):.2f} más en este periodo, por tu configuración del límite de depósito." if limite else ""}',
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