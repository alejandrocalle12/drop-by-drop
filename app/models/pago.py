
from datetime import datetime

from app.extensions import db


class Pago(db.Model):

    __tablename__ = "pagos"

    id_pago = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    prestamo_id = db.Column(
        db.Integer,
        db.ForeignKey("prestamos.id_prestamo"),
        nullable=False
    )

    valor_pago = db.Column(db.Numeric(15, 2), nullable=False)

    fecha_pago = db.Column(db.Date, nullable=False)

    observacion = db.Column(db.String(255), nullable=True)

    fecha_registro = db.Column(
        db.DateTime,
        nullable=True,
        default=datetime.utcnow
    )

    # Relación con préstamo
    prestamo = db.relationship(
        "Prestamo",
        back_populates="pagos"
    )

    def __repr__(self):
        return f"<Pago {self.id_pago}>"
