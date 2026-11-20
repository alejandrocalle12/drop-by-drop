
from flask import Flask, redirect, url_for
from flask_login import current_user

from config import Config
from app.extensions import db, login_manager


def create_app():

    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # Importar modelos
    from app.models.usuario import Usuario
    from app.models.prestamo import Prestamo
    from app.models.pago import Pago

    # Importar rutas
    from app.routes.registro import registro_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.usuarios import usuarios_bp
    from app.routes.prestamos import prestamos_bp
    from app.routes.pagos import pagos_bp
    from app.routes.reportes import reportes_bp

    # Registrar Blueprints
    app.register_blueprint(registro_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(prestamos_bp)
    app.register_blueprint(pagos_bp)
    app.register_blueprint(reportes_bp)

    # Cargar usuario de la sesión
    @login_manager.user_loader
    def cargar_usuario(id_usuario):
        return db.session.get(Usuario, int(id_usuario))

    with app.app_context():
        db.create_all()

    @app.route("/")
    def inicio():

        if current_user.is_authenticated:
            return redirect(url_for("dashboard.panel"))

        return redirect(url_for("auth.login"))

    return app
