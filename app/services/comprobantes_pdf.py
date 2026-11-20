
from io import BytesIO
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)


COLOR_PRINCIPAL = colors.HexColor("#173B57")
COLOR_SECUNDARIO = colors.HexColor("#64748B")
COLOR_FONDO = colors.HexColor("#F1F5F9")
COLOR_BORDE = colors.HexColor("#CBD5E1")


def formato_moneda(valor):
    """Formatea un valor como moneda colombiana."""
    valor = Decimal(str(valor or 0))
    return f"$ {valor:,.2f}"


def formato_fecha(fecha):
    """Convierte una fecha al formato día/mes/año."""
    if fecha:
        return fecha.strftime("%d/%m/%Y")
    return "No registrada"


def texto_seguro(valor):
    """Escapa caracteres especiales para utilizarlos en Paragraph."""
    return escape(str(valor if valor is not None else "No disponible"))


def crear_documento(titulo_documento):
    """Prepara el documento PDF y sus estilos."""

    archivo = BytesIO()

    documento = SimpleDocTemplate(
        archivo,
        pagesize=letter,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=titulo_documento,
        author="Drop by Drop"
    )

    estilos = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloDrop",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        textColor=COLOR_PRINCIPAL,
        alignment=TA_CENTER,
        spaceAfter=5
    )

    subtitulo = ParagraphStyle(
        "SubtituloDrop",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=COLOR_SECUNDARIO,
        alignment=TA_CENTER,
        spaceAfter=15
    )

    encabezado_seccion = ParagraphStyle(
        "EncabezadoSeccion",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=COLOR_PRINCIPAL,
        spaceBefore=12,
        spaceAfter=7
    )

    texto = ParagraphStyle(
        "TextoDrop",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )

    texto_derecha = ParagraphStyle(
        "TextoDerecha",
        parent=texto,
        alignment=TA_RIGHT
    )

    nota = ParagraphStyle(
        "NotaFinal",
        parent=texto,
        fontSize=8,
        textColor=COLOR_SECUNDARIO,
        alignment=TA_CENTER,
        leading=11
    )

    return archivo, documento, {
        "titulo": titulo,
        "subtitulo": subtitulo,
        "seccion": encabezado_seccion,
        "texto": texto,
        "derecha": texto_derecha,
        "nota": nota
    }


def agregar_encabezado(elementos, estilos, subtitulo):
    """Agrega el encabezado institucional."""

    elementos.append(
        Paragraph("DROP BY DROP", estilos["titulo"])
    )

    elementos.append(
        Paragraph(subtitulo, estilos["subtitulo"])
    )

    elementos.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=COLOR_PRINCIPAL,
            spaceAfter=12
        )
    )


def crear_tabla(datos, anchos, encabezado=False):
    """Construye una tabla con el diseño de Drop by Drop."""

    tabla = Table(datos, colWidths=anchos)

    instrucciones = [
        ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
    ]

    if encabezado:
        instrucciones.extend([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRINCIPAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")
        ])
    else:
        instrucciones.append(
            ("BACKGROUND", (0, 0), (0, -1), COLOR_FONDO)
        )

    tabla.setStyle(TableStyle(instrucciones))

    return tabla


def agregar_pie(elementos, estilos):
    """Agrega el texto final del comprobante."""

    elementos.append(Spacer(1, 20))

    elementos.append(
        Paragraph(
            "Este documento es un comprobante informativo de la "
            "operación registrada en el sistema Drop by Drop. "
            "Los valores corresponden a la información almacenada "
            "en el momento de generar este documento.",
            estilos["nota"]
        )
    )

    elementos.append(Spacer(1, 12))

    elementos.append(
        Paragraph(
            "<b>DROP BY DROP - Gestión financiera</b>",
            estilos["nota"]
        )
    )


def generar_comprobante_prestamo(prestamo):
    """
    Genera el comprobante PDF de un préstamo.
    Recibe una instancia del modelo Prestamo.
    Devuelve un archivo PDF en memoria.
    """

    archivo, documento, estilos = crear_documento(
        f"Comprobante de prestamo {prestamo.id_prestamo}"
    )

    elementos = []

    usuario = prestamo.usuario

    nombre_cliente = (
        f"{usuario.nombres} {usuario.apellidos}"
        if usuario else "No disponible"
    )

    cedula_cliente = usuario.cedula if usuario else "No disponible"
    correo_cliente = usuario.correo if usuario else "No disponible"
    telefono_cliente = usuario.telefono if usuario else "No disponible"

    agregar_encabezado(
        elementos,
        estilos,
        "COMPROBANTE DE PRÉSTAMO"
    )

    fecha_generacion = datetime.now(
        ZoneInfo("America/Bogota")
    ).date()

    elementos.append(
        Paragraph(
            f"<b>Comprobante N.º:</b> {prestamo.id_prestamo}",
            estilos["texto"]
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Fecha de generación:</b> "
            f"{formato_fecha(fecha_generacion)}",
            estilos["texto"]
        )
    )

    elementos.append(Spacer(1, 10))

    elementos.append(
        Paragraph("INFORMACIÓN DEL CLIENTE", estilos["seccion"])
    )

    datos_cliente = [
        [
            Paragraph("<b>Nombre completo</b>", estilos["texto"]),
            Paragraph(texto_seguro(nombre_cliente), estilos["texto"])
        ],
        [
            Paragraph("<b>Cédula</b>", estilos["texto"]),
            Paragraph(texto_seguro(cedula_cliente), estilos["texto"])
        ],
        [
            Paragraph("<b>Teléfono</b>", estilos["texto"]),
            Paragraph(texto_seguro(telefono_cliente), estilos["texto"])
        ],
        [
            Paragraph("<b>Correo electrónico</b>", estilos["texto"]),
            Paragraph(texto_seguro(correo_cliente), estilos["texto"])
        ]
    ]

    elementos.append(
        crear_tabla(datos_cliente, [48 * mm, 125 * mm])
    )

    elementos.append(
        Paragraph("DETALLE DEL PRÉSTAMO", estilos["seccion"])
    )

    datos_prestamo = [
        [
            Paragraph("<b>Concepto</b>", estilos["texto"]),
            Paragraph("<b>Valor</b>", estilos["texto"])
        ],
        ["Capital prestado", formato_moneda(prestamo.capital)],
        [
            "Interés mensual",
            f"{Decimal(str(prestamo.porcentaje_interes)) * 100:.2f} %"
        ],
        ["Número de cuotas", str(prestamo.numero_cuotas)],
        [
            "Interés mensual en pesos",
            formato_moneda(prestamo.interes_mensual)
        ],
        [
            "Interés acumulado",
            formato_moneda(prestamo.interes_acumulado)
        ],
        ["Pago total", formato_moneda(prestamo.pago_total)],
        [
            "Cuota mensual exacta",
            formato_moneda(prestamo.cuota_mensual)
        ],
        ["Cuota mensual real", formato_moneda(prestamo.cuota_real)],
        ["Saldo pendiente", formato_moneda(prestamo.saldo_pendiente)]
    ]

    elementos.append(
        crear_tabla(datos_prestamo, [105 * mm, 68 * mm], True)
    )

    elementos.append(
        Paragraph("FECHAS Y ESTADO", estilos["seccion"])
    )

    datos_fechas = [
        [
            Paragraph("<b>Fecha del préstamo</b>", estilos["texto"]),
            Paragraph(
                formato_fecha(prestamo.fecha_prestamo),
                estilos["derecha"]
            )
        ],
        [
            Paragraph("<b>Fecha de vencimiento</b>", estilos["texto"]),
            Paragraph(
                formato_fecha(prestamo.fecha_vencimiento),
                estilos["derecha"]
            )
        ],
        [
            Paragraph("<b>Estado actual</b>", estilos["texto"]),
            Paragraph(
                f"<b>{texto_seguro(prestamo.estado)}</b>",
                estilos["derecha"]
            )
        ]
    ]

    elementos.append(
        crear_tabla(datos_fechas, [85 * mm, 88 * mm])
    )

    agregar_pie(elementos, estilos)

    documento.build(elementos)

    archivo.seek(0)

    return archivo


def calcular_saldos_pago(pago):
    """
    Calcula el saldo anterior y posterior al pago seleccionado.

    Se reconstruye el historial desde el pago total del préstamo,
    ordenando los movimientos por fecha e identificador.

    No modifica la base de datos.
    """

    prestamo = pago.prestamo

    saldo = Decimal(str(prestamo.pago_total))

    pagos_ordenados = sorted(
        prestamo.pagos,
        key=lambda movimiento: (
            movimiento.fecha_pago,
            movimiento.id_pago
        )
    )

    saldo_anterior = None
    saldo_restante = None

    for movimiento in pagos_ordenados:

        valor_movimiento = Decimal(str(movimiento.valor_pago))

        if movimiento.id_pago == pago.id_pago:
            saldo_anterior = saldo
            saldo_restante = saldo - valor_movimiento
            break

        saldo -= valor_movimiento

    if saldo_anterior is None:
        raise ValueError(
            "No se encontró el pago dentro del historial del préstamo."
        )

    if saldo_anterior < 0 or saldo_restante < 0:
        raise ValueError(
            "El historial de pagos presenta valores inconsistentes."
        )

    return (
        saldo_anterior.quantize(Decimal("0.01")),
        saldo_restante.quantize(Decimal("0.01"))
    )


def generar_comprobante_pago(pago):
    """
    Genera el comprobante PDF de un pago.

    Recibe una instancia del modelo Pago.
    Devuelve un archivo PDF en memoria.
    No modifica la base de datos.
    """

    prestamo = pago.prestamo

    if prestamo is None:
        raise ValueError("El pago no tiene un préstamo asociado.")

    usuario = prestamo.usuario

    if usuario is None:
        raise ValueError("El préstamo no tiene un usuario asociado.")

    saldo_anterior, saldo_restante = calcular_saldos_pago(pago)

    archivo, documento, estilos = crear_documento(
        f"Comprobante de pago {pago.id_pago}"
    )

    elementos = []

    nombre_cliente = f"{usuario.nombres} {usuario.apellidos}"

    agregar_encabezado(
        elementos,
        estilos,
        "COMPROBANTE DE PAGO"
    )

    fecha_generacion = datetime.now(
        ZoneInfo("America/Bogota")
    ).date()

    elementos.append(
        Paragraph(
            f"<b>Comprobante de pago N.º:</b> {pago.id_pago}",
            estilos["texto"]
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Fecha de generación:</b> "
            f"{formato_fecha(fecha_generacion)}",
            estilos["texto"]
        )
    )

    elementos.append(Spacer(1, 10))

    elementos.append(
        Paragraph("INFORMACIÓN DEL CLIENTE", estilos["seccion"])
    )

    datos_cliente = [
        [
            Paragraph("<b>Nombre completo</b>", estilos["texto"]),
            Paragraph(texto_seguro(nombre_cliente), estilos["texto"])
        ],
        [
            Paragraph("<b>Cédula</b>", estilos["texto"]),
            Paragraph(texto_seguro(usuario.cedula), estilos["texto"])
        ],
        [
            Paragraph("<b>Teléfono</b>", estilos["texto"]),
            Paragraph(texto_seguro(usuario.telefono), estilos["texto"])
        ],
        [
            Paragraph("<b>Correo electrónico</b>", estilos["texto"]),
            Paragraph(texto_seguro(usuario.correo), estilos["texto"])
        ]
    ]

    elementos.append(
        crear_tabla(datos_cliente, [48 * mm, 125 * mm])
    )

    elementos.append(
        Paragraph("INFORMACIÓN DEL PRÉSTAMO", estilos["seccion"])
    )

    datos_prestamo = [
        [
            Paragraph("<b>Concepto</b>", estilos["texto"]),
            Paragraph("<b>Información</b>", estilos["texto"])
        ],
        ["Número de préstamo", str(prestamo.id_prestamo)],
        ["Fecha del préstamo", formato_fecha(prestamo.fecha_prestamo)],
        [
            "Fecha de vencimiento",
            formato_fecha(prestamo.fecha_vencimiento)
        ],
        ["Capital prestado", formato_moneda(prestamo.capital)],
        ["Valor total del préstamo", formato_moneda(prestamo.pago_total)]
    ]

    elementos.append(
        crear_tabla(datos_prestamo, [85 * mm, 88 * mm], True)
    )

    elementos.append(
        Paragraph("DETALLE DEL PAGO", estilos["seccion"])
    )

    datos_pago = [
        [
            Paragraph("<b>Concepto</b>", estilos["texto"]),
            Paragraph("<b>Valor</b>", estilos["texto"])
        ],
        ["Número de pago", str(pago.id_pago)],
        ["Fecha del pago", formato_fecha(pago.fecha_pago)],
        ["Valor abonado", formato_moneda(pago.valor_pago)],
        ["Saldo anterior", formato_moneda(saldo_anterior)],
        ["Saldo restante", formato_moneda(saldo_restante)]
    ]

    elementos.append(
        crear_tabla(datos_pago, [105 * mm, 68 * mm], True)
    )

    elementos.append(
        Paragraph("OBSERVACIÓN", estilos["seccion"])
    )

    observacion = texto_seguro(
        pago.observacion or "Sin observaciones"
    )

    elementos.append(
        Paragraph(observacion, estilos["texto"])
    )

    agregar_pie(elementos, estilos)

    documento.build(elementos)

    archivo.seek(0)

    return archivo
