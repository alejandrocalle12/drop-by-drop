
import calendar
from datetime import date, datetime
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
from app.models.usuario import Usuario
from app.models.prestamo import Prestamo
from app.services.estados_prestamos import actualizar_estados_prestamos
from app.services.comprobantes_pdf import generar_comprobante_prestamo
from app.services.correo import enviar_comprobante


prestamos_bp = Blueprint("prestamos", __name__)


def redondear_millar(valor):
    """Redondea al millar más cercano, como MROUND de Excel."""
    millar = Decimal("1000")

    return (
        (valor / millar).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        ) * millar
    )


def calcular_fecha_vencimiento(fecha_inicio, numero_meses):
    """
    Calcula la fecha de vencimiento sumando meses.
    Si el día no existe en el mes de destino,
    utiliza el último día de ese mes.
    """
    indice_mes = fecha_inicio.year * 12 + fecha_inicio.month - 1
    indice_mes += numero_meses

    nuevo_anio, nuevo_mes = divmod(indice_mes, 12)
    nuevo_mes += 1

    ultimo_dia = calendar.monthrange(nuevo_anio, nuevo_mes)[1]
    nuevo_dia = min(fecha_inicio.day, ultimo_dia)

    return date(nuevo_anio, nuevo_mes, nuevo_dia)


@prestamos_bp.route("/prestamos", methods=["GET", "POST"])
@login_required
def listar_prestamos():

    # La gestión de préstamos corresponde al administrador.
    if current_user.rol != "ADMIN":
        abort(403)

    usuarios = Usuario.query.filter_by(
        estado="ACTIVO",
        rol="USER"
    ).order_by(Usuario.nombres.asc()).all()

    if request.method == "POST":

        try:
            usuario_id = int(request.form.get("usuario_id", ""))
            capital = Decimal(request.form.get("capital", "0"))
            porcentaje = Decimal(
                request.form.get("porcentaje_interes", "0")
            )
            numero_cuotas = int(request.form.get("numero_cuotas", "0"))
            fecha_prestamo = date.fromisoformat(
                request.form.get("fecha_prestamo", "")
            )

            # Validar capital.
            if not capital.is_finite() or capital <= 0:
                raise ValueError("El capital debe ser mayor que cero.")

            # Validar porcentaje.
            if (
                not porcentaje.is_finite()
                or porcentaje <= 0
                or porcentaje > 100
            ):
                raise ValueError(
                    "El interés debe ser mayor que 0 y máximo 100 %."
                )

            # Validar cuotas.
            if numero_cuotas <= 0:
                raise ValueError(
                    "El número de cuotas debe ser mayor que cero."
                )

            # Comprobar que el usuario exista y esté activo.
            usuario = db.session.get(Usuario, usuario_id)

            if (
                usuario is None
                or usuario.estado != "ACTIVO"
                or usuario.rol != "USER"
            ):
                raise ValueError(
                    "El usuario seleccionado no existe o está inactivo."
                )

            # Convertir el porcentaje ingresado a fracción decimal.
            tasa = porcentaje / Decimal("100")

            # Cálculos equivalentes al Excel.
            interes_mensual = (
                capital * tasa
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            interes_acumulado = (
                interes_mensual * numero_cuotas
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            pago_total = (
                capital + interes_acumulado
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            cuota_mensual = (
                pago_total / Decimal(numero_cuotas)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            cuota_real = redondear_millar(cuota_mensual)

            # Calcular vencimiento según el número de cuotas.
            fecha_vencimiento = calcular_fecha_vencimiento(
                fecha_prestamo,
                numero_cuotas
            )

            nuevo_prestamo = Prestamo(
                usuario_id=usuario_id,
                capital=capital,
                porcentaje_interes=tasa,
                numero_cuotas=numero_cuotas,
                interes_mensual=interes_mensual,
                interes_acumulado=interes_acumulado,
                pago_total=pago_total,
                cuota_mensual=cuota_mensual,
                cuota_real=cuota_real,
                saldo_pendiente=pago_total,
                fecha_prestamo=fecha_prestamo,
                fecha_vencimiento=fecha_vencimiento,
                estado="ACTIVO"
            )

            db.session.add(nuevo_prestamo)
            db.session.commit()

            # El préstamo ya está guardado en MySQL.
            # El envío del correo se realiza por separado.
            try:
                archivo_pdf = generar_comprobante_prestamo(
                    nuevo_prestamo
                )

                nombre_archivo = (
                    f"comprobante_prestamo_"
                    f"{nuevo_prestamo.id_prestamo}.pdf"
                )

                enviar_comprobante(
                    destinatario=usuario.correo,
                    asunto=(
                        f"Comprobante de préstamo "
                        f"#{nuevo_prestamo.id_prestamo} - Drop by Drop"
                    ),
                    mensaje=(
                        f"Hola {usuario.nombres} {usuario.apellidos},\n\n"
                        "Tu préstamo ha sido registrado correctamente "
                        "en Drop by Drop.\n\n"
                        "Adjuntamos el comprobante PDF con los detalles "
                        "del préstamo para tu consulta.\n\n"
                        "Conserva este documento como soporte de la "
                        "operación.\n\n"
                        "Atentamente,\n"
                        "Equipo Drop by Drop"
                    ),
                    archivo_pdf=archivo_pdf,
                    nombre_archivo=nombre_archivo
                )

                flash(
                    "El préstamo se registró correctamente y "
                    "el comprobante fue enviado al correo del cliente.",
                    "success"
                )

            except Exception:
                current_app_logger = __import__("logging").getLogger(__name__)
                current_app_logger.exception(
                    "Error enviando comprobante del préstamo %s",
                    nuevo_prestamo.id_prestamo
                )

                flash(
                    "El préstamo se registró correctamente, pero no "
                    "fue posible enviar el comprobante por correo. "
                    "Puedes descargarlo desde el listado de préstamos.",
                    "warning"
                )

            return redirect(url_for("prestamos.listar_prestamos"))

        except (ValueError, InvalidOperation, TypeError):
            db.session.rollback()
            flash(
                "Verifica los datos ingresados. El préstamo no pudo registrarse.",
                "error"
            )

        except Exception:
            db.session.rollback()
            flash(
                "Ocurrió un error al guardar el préstamo. "
                "Verifica los datos e inténtalo nuevamente.",
                "error"
            )

    # Actualizar los estados antes de mostrar el listado.
    hubo_cambios = actualizar_estados_prestamos()

    if hubo_cambios:
        db.session.commit()

    prestamos = Prestamo.query.options(
        joinedload(Prestamo.usuario)
    ).order_by(
        Prestamo.id_prestamo.desc()
    ).all()

    fecha_actual = datetime.now(
        ZoneInfo("America/Bogota")
    ).date().isoformat()

    return render_template(
        "prestamos.html",
        usuarios=usuarios,
        prestamos=prestamos,
        fecha_actual=fecha_actual
    )


@prestamos_bp.route(
    "/prestamos/<int:prestamo_id>/comprobante",
    methods=["GET"]
)
@login_required
def descargar_comprobante(prestamo_id):

    # El administrador puede consultar cualquier comprobante.
    # El cliente únicamente puede consultar sus propios préstamos.
    consulta = Prestamo.query.options(
        joinedload(Prestamo.usuario)
    ).filter_by(
        id_prestamo=prestamo_id
    )

    if current_user.rol == "USER":
        consulta = consulta.filter_by(
            usuario_id=current_user.id_usuario
        )
    elif current_user.rol != "ADMIN":
        abort(403)

    prestamo = consulta.first()

    if prestamo is None:
        abort(404)

    try:
        # Generar el PDF en memoria.
        archivo_pdf = generar_comprobante_prestamo(prestamo)

        nombre_archivo = (
            f"comprobante_prestamo_{prestamo.id_prestamo}.pdf"
        )

        return send_file(
            archivo_pdf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=nombre_archivo
        )

    except Exception:
        flash(
            "No fue posible generar el comprobante PDF. "
            "Inténtalo nuevamente.",
            "error"
        )

        return redirect(url_for("prestamos.listar_prestamos"))
