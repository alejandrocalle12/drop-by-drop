
from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.usuario import Usuario

registro_bp = Blueprint("registro", __name__)


@registro_bp.route("/registro", methods=["GET", "POST"])
def registro():

    if request.method == "POST":

        nombres = request.form.get("nombres", "").strip()
        apellidos = request.form.get("apellidos", "").strip()
        usuario = request.form.get("usuario", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        telefono = request.form.get("telefono", "").strip()
        cedula = request.form.get("cedula", "").strip()
        password = request.form.get("password", "")
        confirmar_password = request.form.get("confirmar_password", "")

        # Validar campos obligatorios
        if not all([
            nombres, apellidos, usuario, correo,
            telefono, cedula, password, confirmar_password
        ]):
            flash("Todos los campos son obligatorios.", "error")
            return render_template("registro.html")

        # Validar longitud de contraseña
        if len(password) < 8:
            flash("La contraseña debe tener mínimo 8 caracteres.", "error")
            return render_template("registro.html")

        # Confirmar contraseña
        if password != confirmar_password:
            flash("Las contraseñas no coinciden.", "error")
            return render_template("registro.html")

        # Verificar usuario, correo o cédula duplicados
        existente = Usuario.query.filter(
            or_(
                Usuario.usuario == usuario,
                Usuario.correo == correo,
                Usuario.cedula == cedula
            )
        ).first()

        if existente:
            if existente.usuario == usuario:
                flash("Este nombre de usuario ya está registrado.", "error")
            elif existente.correo == correo:
                flash("Este correo electrónico ya está registrado.", "error")
            else:
                flash("Esta cédula ya está registrada.", "error")

            return render_template("registro.html")

        # Crear usuario
        nuevo_usuario = Usuario(
            nombres=nombres,
            apellidos=apellidos,
            usuario=usuario,
            correo=correo,
            telefono=telefono,
            cedula=cedula,
            rol="USER",
            estado="ACTIVO"
        )

        # Guardar contraseña protegida
        nuevo_usuario.establecer_password(password)

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()

            flash(
                "Registro exitoso. Ya puedes iniciar sesión.",
                "success"
            )

            return redirect(url_for("registro.registro"))

        except IntegrityError:
            db.session.rollback()
            flash(
                "El usuario, correo o cédula ya se encuentran registrados.",
                "error"
            )

        except Exception:
            db.session.rollback()
            flash(
                "Ocurrió un error al guardar el registro. Intenta nuevamente.",
                "error"
            )

    return render_template("registro.html")
