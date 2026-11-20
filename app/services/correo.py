
import smtplib
import ssl
from email.message import EmailMessage
from flask import current_app


def enviar_comprobante(
    destinatario,
    asunto,
    mensaje,
    archivo_pdf,
    nombre_archivo
):
    """
    Envía un comprobante PDF mediante Gmail SMTP SSL.
    El PDF se adjunta directamente desde memoria.
    """

    servidor = current_app.config.get("MAIL_SERVER")
    usuario = current_app.config.get("MAIL_USERNAME")
    contrasena = current_app.config.get("MAIL_PASSWORD")
    remitente = current_app.config.get("MAIL_DEFAULT_SENDER")

    if not all([servidor, usuario, contrasena, remitente]):
        raise ValueError(
            "La configuración del correo electrónico está incompleta."
        )

    if not destinatario:
        raise ValueError(
            "El cliente no tiene un correo electrónico registrado."
        )

    contenido_pdf = archivo_pdf.getvalue()

    if not contenido_pdf:
        raise ValueError("El comprobante PDF está vacío.")

    correo = EmailMessage()
    correo["Subject"] = asunto
    correo["From"] = remitente
    correo["To"] = destinatario
    correo.set_content(mensaje)

    correo.add_attachment(
        contenido_pdf,
        maintype="application",
        subtype="pdf",
        filename=nombre_archivo
    )

    contexto = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        servidor,
        465,
        context=contexto,
        timeout=30
    ) as conexion:

        conexion.ehlo()
        conexion.login(usuario, contrasena)
        conexion.send_message(correo)

    return True
