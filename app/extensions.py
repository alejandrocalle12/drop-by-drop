
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Conexión centralizada con MySQL
db = SQLAlchemy()

# Administración de sesiones
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = "auth.login"
login_manager.login_message = "Debes iniciar sesión para acceder."
login_manager.login_message_category = "error"
