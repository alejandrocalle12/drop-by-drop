
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class Usuario(UserMixin, db.Model):

    __tablename__ = "usuarios"

    id_usuario = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)

    usuario = db.Column(db.String(50), unique=True, nullable=False)
    correo = db.Column(db.String(150), unique=True, nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    cedula = db.Column(db.String(30), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    rol = db.Column(
        db.Enum("ADMIN", "USER", name="rol_usuario"),
        nullable=False,
        default="USER"
    )

    estado = db.Column(
        db.Enum("ACTIVO", "INACTIVO", name="estado_usuario"),
        nullable=False,
        default="ACTIVO"
    )

    fecha_registro = db.Column(
        db.DateTime,
        nullable=True,
        default=datetime.utcnow
    )

    prestamos = db.relationship(
        "Prestamo",
        back_populates="usuario",
        lazy=True
    )

    # Identificador que utiliza Flask-Login
    def get_id(self):
        return str(self.id_usuario)

    def establecer_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario {self.usuario}>"
