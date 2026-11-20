
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.models.usuario import Usuario

usuarios_bp = Blueprint("usuarios", __name__)

@usuarios_bp.route("/usuarios")
@login_required
def listar_usuarios():

    # Solo los administradores pueden consultar los usuarios
    if current_user.rol != "ADMIN":
        abort(403)

    usuarios = Usuario.query.order_by(
        Usuario.fecha_registro.desc()
    ).all()

    return render_template(
        "usuarios.html",
        usuarios=usuarios
    )