from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.usuario import Usuario
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.services.estados_prestamos import actualizar_estados_prestamos


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/panel")
@login_required
def panel():
    # Actualizar automáticamente los estados de los préstamos.
    hubo_cambios = actualizar_estados_prestamos()
    if hubo_cambios:
        db.session.commit()

    if current_user.rol == "ADMIN":
        total_usuarios = Usuario.query.count()
        usuarios_activos = Usuario.query.filter_by(estado="ACTIVO").count()
        total_prestamos = Prestamo.query.count()

        saldo_pendiente = db.session.query(
            func.coalesce(func.sum(Prestamo.saldo_pendiente), 0)
        ).scalar()

        return render_template(
            "dashboard.html",
            total_usuarios=total_usuarios,
            usuarios_activos=usuarios_activos,
            total_prestamos=total_prestamos,
            saldo_pendiente=saldo_pendiente,
            prestamos_usuario=[],
            total_abonado=0,
            prestamos_activos=0,
            prestamos_pagados=0,
            prestamos_vencidos=0,
        )

    # El usuario USER solo consulta los préstamos asociados a su propia cuenta.
    prestamos_usuario = Prestamo.query.options(
        joinedload(Prestamo.pagos)
    ).filter_by(
        usuario_id=current_user.id_usuario
    ).order_by(
        Prestamo.fecha_prestamo.desc(),
        Prestamo.id_prestamo.desc()
    ).all()

    total_prestamos = len(prestamos_usuario)
    saldo_pendiente = sum(
        (prestamo.saldo_pendiente or 0 for prestamo in prestamos_usuario),
        start=0
    )
    total_abonado = sum(
        (
            pago.valor_pago or 0
            for prestamo in prestamos_usuario
            for pago in prestamo.pagos
        ),
        start=0
    )

    prestamos_activos = sum(
        1 for prestamo in prestamos_usuario if prestamo.estado == "ACTIVO"
    )
    prestamos_pagados = sum(
        1 for prestamo in prestamos_usuario if prestamo.estado == "PAGADO"
    )
    prestamos_vencidos = sum(
        1 for prestamo in prestamos_usuario if prestamo.estado == "VENCIDO"
    )

    # Ordenar los pagos de cada crédito del más reciente al más antiguo.
    for prestamo in prestamos_usuario:
        prestamo.pagos_ordenados = sorted(
            prestamo.pagos,
            key=lambda pago: (pago.fecha_pago, pago.id_pago),
            reverse=True
        )
        prestamo.total_abonado = sum(
            (pago.valor_pago or 0 for pago in prestamo.pagos),
            start=0
        )

    return render_template(
        "dashboard.html",
        total_usuarios=0,
        usuarios_activos=0,
        total_prestamos=total_prestamos,
        saldo_pendiente=saldo_pendiente,
        prestamos_usuario=prestamos_usuario,
        total_abonado=total_abonado,
        prestamos_activos=prestamos_activos,
        prestamos_pagados=prestamos_pagados,
        prestamos_vencidos=prestamos_vencidos,
    )
