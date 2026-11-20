
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    send_file
)
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.services.estados_prestamos import actualizar_estados_prestamos
from app.services.comprobantes_pdf import generar_comprobante_pago
from app.services.correo import enviar_comprobante


pagos_bp = Blueprint("pagos", __name__)

logger = logging.getLogger(__name__)


@pagos_bp.route("/pagos", methods=["GET", "POST"])
@login_required
def listar_pagos():

    # Solo el administrador puede gestionar pagos.
    if current_user.rol != "ADMIN":
        abort(403)

    if request.method == "POST":

        try:
            prestamo_id = int(request.form.get("prestamo_id", "0"))

            valor_pago = Decimal(
                request.form.get("valor_pago", "0")
            )

            fecha_pago = datetime.strptime(
                request.form.get("fecha_pago", ""),
                "%Y-%m-%d"
            ).date()

            observacion = request.form.get(
                "observacion", ""
            ).strip()

            # Validar valor del pago.
            if not valor_pago.is_finite() or valor_pago <= 0:
                raise ValueError(
                    "El valor del pago debe ser mayor que cero."
                )

            # Limitar a dos decimales.
            valor_pago = valor_pago.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            if valor_pago <= 0:
                raise ValueError("El valor del pago no es válido.")

            if len(observacion) > 255:
                raise ValueError(
                    "La observación no puede superar los 255 caracteres."
                )

            # Bloquear temporalmente el préstamo mientras se registra
            # el abono para evitar actualizaciones simultáneas del saldo.
            prestamo = Prestamo.query.options(
                joinedload(Prestamo.usuario)
            ).filter_by(
                id_prestamo=prestamo_id
            ).with_for_update().first()

            if prestamo is None:
                raise ValueError(
                    "El préstamo seleccionado no existe."
                )

            saldo_anterior = Decimal(str(prestamo.saldo_pendiente))

            if saldo_anterior <= 0:
                raise ValueError(
                    "Este préstamo ya se encuentra completamente pagado."
                )

            if valor_pago > saldo_anterior:
                raise ValueError(
                    f"El pago supera el saldo pendiente de "
                    f"${saldo_anterior:,.2f}."
                )

            # Calcular nuevo saldo.
            nuevo_saldo = (
                saldo_anterior - valor_pago
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            # Crear movimiento de pago.
            nuevo_pago = Pago(
                prestamo_id=prestamo.id_prestamo,
                valor_pago=valor_pago,
                fecha_pago=fecha_pago,
                observacion=observacion or None
            )

            # Actualizar saldo del préstamo.
            prestamo.saldo_pendiente = nuevo_saldo

            # Agregar el pago a la transacción.
            db.session.add(nuevo_pago)

            # Actualizar automáticamente los estados.
            actualizar_estados_prestamos()

            # Guardar pago, saldo y estado en una sola transacción.
            db.session.commit()

            # El pago ya está guardado en MySQL.
            # El envío del correo se realiza por separado.
            try:
                archivo_pdf = generar_comprobante_pago(nuevo_pago)

                nombre_archivo = (
                    f"comprobante_pago_{nuevo_pago.id_pago}.pdf"
                )

                usuario = prestamo.usuario

                enviar_comprobante(
                    destinatario=usuario.correo,
                    asunto=(
                        f"Comprobante de pago "
                        f"#{nuevo_pago.id_pago} - Drop by Drop"
                    ),
                    mensaje=(
                        f"Hola {usuario.nombres} {usuario.apellidos},\n\n"
                        "Tu pago ha sido registrado correctamente "
                        "en Drop by Drop.\n\n"
                        "Adjuntamos el comprobante PDF con los detalles "
                        "del movimiento realizado.\n\n"
                        f"Valor del pago: ${valor_pago:,.2f}\n"
                        f"Saldo pendiente: ${nuevo_saldo:,.2f}\n\n"
                        "Conserva este documento como soporte de la "
                        "operación.\n\n"
                        "Atentamente,\n"
                        "Equipo Drop by Drop"
                    ),
                    archivo_pdf=archivo_pdf,
                    nombre_archivo=nombre_archivo
                )

                flash(
                    f"Pago registrado correctamente. "
                    f"Nuevo saldo: ${nuevo_saldo:,.2f}. "
                    "El comprobante fue enviado al correo del cliente.",
                    "success"
                )

            except Exception:
                logger.exception(
                    "Error enviando comprobante del pago %s",
                    nuevo_pago.id_pago
                )

                flash(
                    f"Pago registrado correctamente. "
                    f"Nuevo saldo: ${nuevo_saldo:,.2f}. "
                    "No fue posible enviar el comprobante por correo. "
                    "Puedes descargarlo desde el historial de pagos.",
                    "warning"
                )

            return redirect(
                url_for("pagos.listar_pagos")
            )

        except (ValueError, InvalidOperation, TypeError):
            db.session.rollback()

            flash(
                "No fue posible registrar el pago. "
                "Verifica los datos ingresados.",
                "error"
            )

        except Exception:
            db.session.rollback()

            logger.exception("Error registrando el pago")

            flash(
                "Ocurrió un error al guardar el pago. "
                "No se realizaron cambios.",
                "error"
            )

    # Actualizar los estados automáticamente al consultar el módulo.
    hubo_cambios = actualizar_estados_prestamos()

    if hubo_cambios:
        db.session.commit()

    # Consultar préstamos que todavía tienen saldo pendiente.
    prestamos_disponibles = Prestamo.query.options(
        joinedload(Prestamo.usuario)
    ).filter(
        Prestamo.saldo_pendiente > 0
    ).order_by(
        Prestamo.id_prestamo.desc()
    ).all()

    # Consultar historial completo de pagos.
    pagos = Pago.query.options(
        joinedload(Pago.prestamo).joinedload(Prestamo.usuario)
    ).order_by(
        Pago.id_pago.desc()
    ).all()

    # Calcular total recaudado.
    total_recaudado = db.session.query(
        db.func.coalesce(
            db.func.sum(Pago.valor_pago),
            0
        )
    ).scalar()

    # Obtener fecha actual de Colombia.
    fecha_actual = datetime.now(
        ZoneInfo("America/Bogota")
    ).date().isoformat()

    return render_template(
        "pagos.html",
        prestamos=prestamos_disponibles,
        pagos=pagos,
        total_recaudado=total_recaudado,
        fecha_actual=fecha_actual
    )


@pagos_bp.route(
    "/pagos/<int:pago_id>/comprobante",
    methods=["GET"]
)
@login_required
def descargar_comprobante_pago(pago_id):

    # El administrador puede consultar cualquier comprobante.
    # El cliente únicamente puede consultar pagos de sus propios préstamos.
    consulta = Pago.query.options(
        joinedload(Pago.prestamo).joinedload(Prestamo.usuario),
        joinedload(Pago.prestamo).joinedload(Prestamo.pagos)
    ).filter_by(
        id_pago=pago_id
    )

    if current_user.rol == "USER":
        consulta = consulta.join(
            Prestamo, Pago.prestamo_id == Prestamo.id_prestamo
        ).filter(
            Prestamo.usuario_id == current_user.id_usuario
        )
    elif current_user.rol != "ADMIN":
        abort(403)

    pago = consulta.first()

    if pago is None:
        abort(404)

    try:
        # Generar el comprobante PDF.
        archivo_pdf = generar_comprobante_pago(pago)

        nombre_archivo = (
            f"comprobante_pago_{pago.id_pago}.pdf"
        )

        return send_file(
            archivo_pdf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=nombre_archivo
        )

    except Exception:
        logger.exception(
            "Error generando comprobante del pago %s",
            pago_id
        )

        flash(
            "No fue posible generar el comprobante del pago. "
            "Inténtalo nuevamente.",
            "error"
        )

        if current_user.rol == "USER":
            return redirect(url_for("dashboard.panel"))
        return redirect(url_for("pagos.listar_pagos"))
