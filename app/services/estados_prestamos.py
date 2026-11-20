
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.prestamo import Prestamo


def actualizar_estados_prestamos():
    """
    Actualiza automáticamente el estado de los préstamos.

    PAGADO:
        Cuando el saldo pendiente es menor o igual a cero.

    VENCIDO:
        Cuando existe saldo pendiente y la fecha actual
        es posterior a la fecha de vencimiento.

    ACTIVO:
        Cuando existe saldo pendiente y la fecha actual
        es igual o anterior a la fecha de vencimiento.

    Un préstamo PAGADO conserva ese estado.
    Esta función no realiza commit; la ruta que la utiliza
    controla la transacción.
    """

    # Obtener la fecha actual de Colombia.
    fecha_actual = datetime.now(
        ZoneInfo("America/Bogota")
    ).date()

    prestamos = Prestamo.query.all()

    hubo_cambios = False

    for prestamo in prestamos:

        # Un préstamo sin saldo pendiente está pagado.
        if prestamo.saldo_pendiente <= 0:
            nuevo_estado = "PAGADO"

        # Un préstamo pagado no vuelve a otro estado.
        elif prestamo.estado == "PAGADO":
            nuevo_estado = "PAGADO"

        # Verificar si ya pasó la fecha de vencimiento.
        elif (
            prestamo.fecha_vencimiento is not None
            and fecha_actual > prestamo.fecha_vencimiento
        ):
            nuevo_estado = "VENCIDO"

        # Si todavía no vence, permanece activo.
        else:
            nuevo_estado = "ACTIVO"

        # Actualizar únicamente cuando el estado sea diferente.
        if prestamo.estado != nuevo_estado:
            prestamo.estado = nuevo_estado
            hubo_cambios = True

    return hubo_cambios
