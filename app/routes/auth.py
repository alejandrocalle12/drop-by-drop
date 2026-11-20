
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

from app.models.usuario import Usuario

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard.panel"))

    if request.method == "POST":

        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        if not usuario or not password:
            flash("Ingresa tu usuario y contraseña.", "error")
            return render_template("login.html")

        usuario_db = Usuario.query.filter_by(
            usuario=usuario
        ).first()

        if usuario_db and usuario_db.verificar_password(password):

            if usuario_db.estado != "ACTIVO":
                flash("Tu cuenta se encuentra inactiva.", "error")
                return render_template("login.html")

            login_user(usuario_db)

            return redirect(url_for("dashboard.panel"))

        flash("Usuario o contraseña incorrectos.", "error")

    return render_template("login.html")

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()

    flash("Has cerrado sesión correctamente.", "success")

    return redirect(url_for("auth.login"))