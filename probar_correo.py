
import smtplib
import ssl

from app import create_app

app = create_app()

with app.app_context():

    servidor = app.config["MAIL_SERVER"]
    usuario = app.config["MAIL_USERNAME"]
    contrasena = app.config["MAIL_PASSWORD"]

    conexion = None

    try:
        contexto = ssl.create_default_context()

        print("Conectando con Gmail...")

        conexion = smtplib.SMTP_SSL(
            servidor,
            465,
            context=contexto,
            timeout=30
        )

        conexion.ehlo()

        print("Conexión establecida.")
        print("Probando autenticación LOGIN...")

        def responder_desafio(desafio=None):
            if desafio is None:
                return usuario
            return contrasena

        respuesta = conexion.auth(
            "LOGIN",
            responder_desafio
        )

        print("Respuesta de autenticación:", respuesta[0])
        print("AUTENTICACIÓN EXITOSA.")

    except Exception as error:
        print("\nERROR:", type(error).__name__)
        print("DETALLE:", str(error))

    finally:
        if conexion:
            try:
                conexion.quit()
            except Exception:
                conexion.close()
