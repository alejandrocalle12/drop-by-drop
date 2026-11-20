
from datetime import datetime

from app.extensions import db


class Prestamo(db.Model):

    __tablename__ = "prestamos"

    id_prestamo = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario"),
        nullable=False
    )

    capital = db.Column(db.Numeric(15, 2), nullable=False)
    porcentaje_interes = db.Column(db.Numeric(5, 2), nullable=False)
    numero_cuotas = db.Column(db.Integer, nullable=False)

    interes_mensual = db.Column(db.Numeric(15, 2), nullable=False)
    interes_acumulado = db.Column(db.Numeric(15, 2), nullable=False)

    pago_total = db.Column(db.Numeric(15, 2), nullable=False)
    cuota_mensual = db.Column(db.Numeric(15, 2), nullable=False)
    cuota_real = db.Column(db.Numeric(15, 2), nullable=False)

    saldo_pendiente = db.Column(db.Numeric(15, 2), nullable=False)

    fecha_prestamo = db.Column(db.Date, nullable=False)

    fecha_vencimiento = db.Column(
        db.Date,
        nullable=True
    )

    estado = db.Column(
        db.Enum("ACTIVO", "PAGADO", "VENCIDO"),
        nullable=False,
        default="ACTIVO"
    )

    fecha_registro = db.Column(
        db.DateTime,
        nullable=True,
        default=datetime.utcnow
    )

    # Relación con usuario
    usuario = db.relationship(
        "Usuario",
        back_populates="prestamos"
    )

    # Relación con pagos
    pagos = db.relationship(
        "Pago",
        back_populates="prestamo",
        lazy=True
    )

    def __repr__(self):
        return f"<Prestamo {self.id_prestamo}>"
