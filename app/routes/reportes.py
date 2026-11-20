from datetime import date
from decimal import Decimal
from io import BytesIO

from flask import Blueprint, abort, render_template, request, send_file
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)

from app.extensions import db
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.usuario import Usuario
from app.services.estados_prestamos import actualizar_estados_prestamos


reportes_bp = Blueprint("reportes", __name__)


def _decimal(valor):
    return valor if valor is not None else Decimal("0")


@reportes_bp.route("/reportes", methods=["GET"])
@login_required
def resumen_reportes():
    if current_user.rol != "ADMIN":
        abort(403)

    hoy = date.today()
    inicio_defecto = hoy.replace(day=1)

    try:
        fecha_desde = date.fromisoformat(request.args.get("desde", inicio_defecto.isoformat()))
        fecha_hasta = date.fromisoformat(request.args.get("hasta", hoy.isoformat()))
        if fecha_desde > fecha_hasta:
            raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
    except ValueError as error:
        fecha_desde = inicio_defecto
        fecha_hasta = hoy
        mensaje_error = str(error) or "Selecciona un rango de fechas válido."
    else:
        mensaje_error = None

    hubo_cambios = actualizar_estados_prestamos()
    if hubo_cambios:
        db.session.commit()

    prestamos_periodo = Prestamo.query.options(
        joinedload(Prestamo.usuario)
    ).filter(
        Prestamo.fecha_prestamo >= fecha_desde,
        Prestamo.fecha_prestamo <= fecha_hasta
    ).order_by(Prestamo.fecha_prestamo.desc(), Prestamo.id_prestamo.desc()).all()

    pagos_periodo = Pago.query.join(Pago.prestamo).options(
        joinedload(Pago.prestamo).joinedload(Prestamo.usuario)
    ).filter(
        Pago.fecha_pago >= fecha_desde,
        Pago.fecha_pago <= fecha_hasta
    ).order_by(Pago.fecha_pago.desc(), Pago.id_pago.desc()).all()

    capital_periodo = sum((_decimal(p.capital) for p in prestamos_periodo), Decimal("0"))
    intereses_periodo = sum((_decimal(p.interes_acumulado) for p in prestamos_periodo), Decimal("0"))
    recaudo_periodo = sum((_decimal(p.valor_pago) for p in pagos_periodo), Decimal("0"))

    # La cartera pendiente representa el saldo actual de todos los préstamos,
    # no un saldo histórico reconstruido al final del rango seleccionado.
    cartera_pendiente = db.session.query(
        func.coalesce(func.sum(Prestamo.saldo_pendiente), 0)
    ).filter(Prestamo.saldo_pendiente > 0).scalar()

    total_prestamos = Prestamo.query.count()
    prestamos_activos = Prestamo.query.filter_by(estado="ACTIVO").count()
    prestamos_pagados = Prestamo.query.filter_by(estado="PAGADO").count()
    prestamos_vencidos = Prestamo.query.filter_by(estado="VENCIDO").count()
    total_usuarios = Usuario.query.filter_by(rol="USER").count()

    return render_template(
        "reportes.html",
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        mensaje_error=mensaje_error,
        prestamos_periodo=prestamos_periodo,
        pagos_periodo=pagos_periodo,
        capital_periodo=capital_periodo,
        intereses_periodo=intereses_periodo,
        recaudo_periodo=recaudo_periodo,
        cartera_pendiente=_decimal(cartera_pendiente),
        total_prestamos=total_prestamos,
        prestamos_activos=prestamos_activos,
        prestamos_pagados=prestamos_pagados,
        prestamos_vencidos=prestamos_vencidos,
        total_usuarios=total_usuarios,
    )


@reportes_bp.route("/reportes/exportar-excel", methods=["GET"])
@login_required
def exportar_reportes_excel():
    """Genera un libro Excel con resumen, préstamos y pagos del período."""
    if current_user.rol != "ADMIN":
        abort(403)

    hoy = date.today()
    inicio_defecto = hoy.replace(day=1)

    try:
        fecha_desde = date.fromisoformat(
            request.args.get("desde", inicio_defecto.isoformat())
        )
        fecha_hasta = date.fromisoformat(
            request.args.get("hasta", hoy.isoformat())
        )
        if fecha_desde > fecha_hasta:
            abort(400, description="La fecha inicial no puede ser posterior a la fecha final.")
    except ValueError:
        abort(400, description="El rango de fechas no es válido.")

    hubo_cambios = actualizar_estados_prestamos()
    if hubo_cambios:
        db.session.commit()

    prestamos_periodo = Prestamo.query.options(
        joinedload(Prestamo.usuario)
    ).filter(
        Prestamo.fecha_prestamo >= fecha_desde,
        Prestamo.fecha_prestamo <= fecha_hasta
    ).order_by(Prestamo.fecha_prestamo.desc(), Prestamo.id_prestamo.desc()).all()

    pagos_periodo = Pago.query.join(Pago.prestamo).options(
        joinedload(Pago.prestamo).joinedload(Prestamo.usuario)
    ).filter(
        Pago.fecha_pago >= fecha_desde,
        Pago.fecha_pago <= fecha_hasta
    ).order_by(Pago.fecha_pago.desc(), Pago.id_pago.desc()).all()

    capital_periodo = sum((_decimal(p.capital) for p in prestamos_periodo), Decimal("0"))
    intereses_periodo = sum((_decimal(p.interes_acumulado) for p in prestamos_periodo), Decimal("0"))
    recaudo_periodo = sum((_decimal(p.valor_pago) for p in pagos_periodo), Decimal("0"))
    cartera_pendiente = _decimal(
        db.session.query(func.coalesce(func.sum(Prestamo.saldo_pendiente), 0))
        .filter(Prestamo.saldo_pendiente > 0).scalar()
    )

    total_prestamos = Prestamo.query.count()
    prestamos_activos = Prestamo.query.filter_by(estado="ACTIVO").count()
    prestamos_pagados = Prestamo.query.filter_by(estado="PAGADO").count()
    prestamos_vencidos = Prestamo.query.filter_by(estado="VENCIDO").count()
    total_usuarios = Usuario.query.filter_by(rol="USER").count()

    libro = Workbook()
    resumen = libro.active
    resumen.title = "Resumen financiero"
    prestamos_hoja = libro.create_sheet("Préstamos")
    pagos_hoja = libro.create_sheet("Pagos")

    color_titulo = "17324F"
    color_encabezado = "1CA58D"
    color_blanco = "FFFFFF"
    borde = Side(style="thin", color="D9E2F0")
    formato_moneda_excel = '"$" #,##0.00;[Red]-"$" #,##0.00'

    def aplicar_titulo(hoja, titulo, ultima_columna):
        hoja.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ultima_columna)
        celda = hoja.cell(row=1, column=1, value=titulo)
        celda.font = Font(name="Calibri", size=16, bold=True, color=color_blanco)
        celda.fill = PatternFill("solid", fgColor=color_titulo)
        celda.alignment = Alignment(vertical="center")
        hoja.row_dimensions[1].height = 28

    def aplicar_encabezados(hoja, fila, columnas):
        for indice, nombre in enumerate(columnas, start=1):
            celda = hoja.cell(row=fila, column=indice, value=nombre)
            celda.font = Font(bold=True, color=color_blanco)
            celda.fill = PatternFill("solid", fgColor=color_encabezado)
            celda.alignment = Alignment(horizontal="center", vertical="center")
            celda.border = Border(bottom=borde)

    def ajustar_columnas(hoja):
        for columna in hoja.columns:
            letra = get_column_letter(columna[0].column)
            longitud = max((len(str(c.value)) if c.value is not None else 0) for c in columna)
            hoja.column_dimensions[letra].width = min(max(longitud + 3, 14), 38)

    aplicar_titulo(resumen, "DROP BY DROP | RESUMEN FINANCIERO", 2)
    resumen.append([])
    resumen.append(["Período consultado", f"{fecha_desde:%d/%m/%Y} al {fecha_hasta:%d/%m/%Y}"])
    resumen.append(["Fecha de generación", date.today()])
    resumen.append([])
    aplicar_encabezados(resumen, 6, ["Indicador", "Valor"])
    indicadores = [
        ("Capital colocado en el período", float(capital_periodo)),
        ("Recaudo recibido en el período", float(recaudo_periodo)),
        ("Intereses generados en el período", float(intereses_periodo)),
        ("Cartera pendiente actual (todos los créditos)", float(cartera_pendiente)),
        ("Clientes registrados", total_usuarios),
        ("Préstamos registrados (total)", total_prestamos),
        ("Préstamos activos", prestamos_activos),
        ("Préstamos pagados", prestamos_pagados),
        ("Préstamos vencidos", prestamos_vencidos),
        ("Préstamos del período", len(prestamos_periodo)),
        ("Pagos del período", len(pagos_periodo)),
    ]
    for fila in indicadores:
        resumen.append(list(fila))
    for fila in range(7, 10):
        resumen.cell(row=fila, column=2).number_format = formato_moneda_excel
    resumen.freeze_panes = "A7"

    columnas_prestamos = [
        "Crédito", "ID cliente", "Cliente", "Usuario", "Fecha", "Capital",
        "Intereses", "Total crédito", "Número de cuotas", "Valor cuota",
        "Total abonado", "Saldo actual", "Vencimiento", "Estado"
    ]
    aplicar_titulo(prestamos_hoja, "DROP BY DROP | PRÉSTAMOS DEL PERÍODO", len(columnas_prestamos))
    aplicar_encabezados(prestamos_hoja, 3, columnas_prestamos)
    for prestamo in prestamos_periodo:
        total_abonado = sum((_decimal(p.valor_pago) for p in prestamo.pagos), Decimal("0"))
        prestamos_hoja.append([
            prestamo.id_prestamo, prestamo.usuario_id,
            f"{prestamo.usuario.nombres} {prestamo.usuario.apellidos}",
            prestamo.usuario.usuario, prestamo.fecha_prestamo,
            float(_decimal(prestamo.capital)), float(_decimal(prestamo.interes_acumulado)),
            float(_decimal(prestamo.pago_total)), prestamo.numero_cuotas,
            float(_decimal(prestamo.cuota_real)), float(total_abonado),
            float(_decimal(prestamo.saldo_pendiente)), prestamo.fecha_vencimiento,
            prestamo.estado
        ])
    for fila in prestamos_hoja.iter_rows(min_row=4, min_col=6, max_col=8):
        for celda in fila:
            celda.number_format = formato_moneda_excel
    for fila in prestamos_hoja.iter_rows(min_row=4, min_col=10, max_col=12):
        for celda in fila:
            celda.number_format = formato_moneda_excel
    for fila in range(4, prestamos_hoja.max_row + 1):
        prestamos_hoja.cell(fila, 5).number_format = "dd/mm/yyyy"
        prestamos_hoja.cell(fila, 13).number_format = "dd/mm/yyyy"
    prestamos_hoja.freeze_panes = "A4"
    if prestamos_hoja.max_row >= 4:
        prestamos_hoja.auto_filter.ref = f"A3:N{prestamos_hoja.max_row}"

    columnas_pagos = [
        "Pago", "Crédito", "ID cliente", "Cliente", "Usuario",
        "Fecha de pago", "Valor recibido", "Observación"
    ]
    aplicar_titulo(pagos_hoja, "DROP BY DROP | PAGOS DEL PERÍODO", len(columnas_pagos))
    aplicar_encabezados(pagos_hoja, 3, columnas_pagos)
    for pago in pagos_periodo:
        cliente = pago.prestamo.usuario
        pagos_hoja.append([
            pago.id_pago, pago.prestamo_id, cliente.id_usuario,
            f"{cliente.nombres} {cliente.apellidos}", cliente.usuario,
            pago.fecha_pago, float(_decimal(pago.valor_pago)),
            pago.observacion or "Sin observación"
        ])
    for fila in range(4, pagos_hoja.max_row + 1):
        pagos_hoja.cell(fila, 6).number_format = "dd/mm/yyyy"
        pagos_hoja.cell(fila, 7).number_format = formato_moneda_excel
    pagos_hoja.freeze_panes = "A4"
    if pagos_hoja.max_row >= 4:
        pagos_hoja.auto_filter.ref = f"A3:H{pagos_hoja.max_row}"

    for hoja in libro.worksheets:
        hoja.sheet_view.showGridLines = False
        ajustar_columnas(hoja)

    salida = BytesIO()
    libro.save(salida)
    salida.seek(0)
    nombre_archivo = f"reporte_drop_by_drop_{fecha_desde:%Y%m%d}_{fecha_hasta:%Y%m%d}.xlsx"

    return send_file(
        salida,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@reportes_bp.route("/reportes/exportar-pdf", methods=["GET"])
@login_required
def exportar_reportes_pdf():
    """Genera un informe financiero PDF con los datos del período consultado."""
    if current_user.rol != "ADMIN":
        abort(403)

    hoy = date.today()
    inicio_defecto = hoy.replace(day=1)

    try:
        fecha_desde = date.fromisoformat(
            request.args.get("desde", inicio_defecto.isoformat())
        )
        fecha_hasta = date.fromisoformat(
            request.args.get("hasta", hoy.isoformat())
        )
        if fecha_desde > fecha_hasta:
            abort(400, description="La fecha inicial no puede ser posterior a la fecha final.")
    except ValueError:
        abort(400, description="El rango de fechas no es válido.")

    hubo_cambios = actualizar_estados_prestamos()
    if hubo_cambios:
        db.session.commit()

    prestamos_periodo = Prestamo.query.options(
        joinedload(Prestamo.usuario), joinedload(Prestamo.pagos)
    ).filter(
        Prestamo.fecha_prestamo >= fecha_desde,
        Prestamo.fecha_prestamo <= fecha_hasta
    ).order_by(Prestamo.fecha_prestamo.desc(), Prestamo.id_prestamo.desc()).all()

    pagos_periodo = Pago.query.join(Pago.prestamo).options(
        joinedload(Pago.prestamo).joinedload(Prestamo.usuario)
    ).filter(
        Pago.fecha_pago >= fecha_desde,
        Pago.fecha_pago <= fecha_hasta
    ).order_by(Pago.fecha_pago.desc(), Pago.id_pago.desc()).all()

    capital_periodo = sum((_decimal(p.capital) for p in prestamos_periodo), Decimal("0"))
    intereses_periodo = sum((_decimal(p.interes_acumulado) for p in prestamos_periodo), Decimal("0"))
    recaudo_periodo = sum((_decimal(p.valor_pago) for p in pagos_periodo), Decimal("0"))
    cartera_pendiente = _decimal(
        db.session.query(func.coalesce(func.sum(Prestamo.saldo_pendiente), 0))
        .filter(Prestamo.saldo_pendiente > 0).scalar()
    )

    total_prestamos = Prestamo.query.count()
    prestamos_activos = Prestamo.query.filter_by(estado="ACTIVO").count()
    prestamos_pagados = Prestamo.query.filter_by(estado="PAGADO").count()
    prestamos_vencidos = Prestamo.query.filter_by(estado="VENCIDO").count()
    total_usuarios = Usuario.query.filter_by(rol="USER").count()

    def moneda(valor):
        return "$ " + f"{_decimal(valor):,.0f}"

    def fecha_texto(valor):
        return valor.strftime("%d/%m/%Y") if valor else "—"

    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=landscape(letter),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title="Informe financiero - Drop by Drop",
        author="Drop by Drop",
        subject=f"Informe del {fecha_texto(fecha_desde)} al {fecha_texto(fecha_hasta)}",
    )

    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(
        name="Marca", parent=estilos["Title"], fontName="Helvetica-Bold",
        fontSize=21, leading=25, textColor=colors.HexColor("#17324F"),
        alignment=TA_LEFT, spaceAfter=3
    ))
    estilos.add(ParagraphStyle(
        name="Submarca", parent=estilos["Normal"], fontSize=9,
        textColor=colors.HexColor("#60758C"), leading=13
    ))
    estilos.add(ParagraphStyle(
        name="Seccion", parent=estilos["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, textColor=colors.HexColor("#17324F"),
        spaceBefore=10, spaceAfter=7
    ))
    estilos.add(ParagraphStyle(
        name="Celda", parent=estilos["Normal"], fontSize=7.2,
        leading=9, textColor=colors.HexColor("#26384D")
    ))
    estilos.add(ParagraphStyle(
        name="CeldaPequena", parent=estilos["Normal"], fontSize=6.5,
        leading=8, textColor=colors.HexColor("#26384D")
    ))
    estilos.add(ParagraphStyle(
        name="Nota", parent=estilos["Normal"], fontSize=7.5,
        leading=10, textColor=colors.HexColor("#60758C")
    ))

    historia = []
    historia.append(Paragraph("DROP BY DROP", estilos["Marca"]))
    historia.append(Paragraph("INFORME FINANCIERO Y DE CARTERA", estilos["Submarca"]))
    historia.append(Spacer(1, 5 * mm))

    datos_periodo = [
        [Paragraph("<b>Período consultado</b>", estilos["Celda"]),
         Paragraph(f"{fecha_texto(fecha_desde)} al {fecha_texto(fecha_hasta)}", estilos["Celda"]),
         Paragraph("<b>Fecha de generación</b>", estilos["Celda"]),
         Paragraph(fecha_texto(date.today()), estilos["Celda"])],
    ]
    tabla_periodo = Table(datos_periodo, colWidths=[38*mm, 75*mm, 40*mm, 45*mm])
    tabla_periodo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6FA")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E2F0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    historia.append(tabla_periodo)
    historia.append(Paragraph("Resumen ejecutivo", estilos["Seccion"]))

    indicadores = [
        ["Capital colocado", moneda(capital_periodo), "Recaudo recibido", moneda(recaudo_periodo)],
        ["Intereses generados", moneda(intereses_periodo), "Cartera pendiente actual", moneda(cartera_pendiente)],
        ["Clientes registrados", str(total_usuarios), "Préstamos del período", str(len(prestamos_periodo))],
        ["Préstamos activos", str(prestamos_activos), "Préstamos pagados", str(prestamos_pagados)],
        ["Préstamos vencidos", str(prestamos_vencidos), "Pagos del período", str(len(pagos_periodo))],
    ]
    tabla_indicadores = Table(indicadores, colWidths=[55*mm, 45*mm, 55*mm, 45*mm])
    tabla_indicadores.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF0F7")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#EAF0F7")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#17324F")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E2F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    historia.append(tabla_indicadores)
    historia.append(Spacer(1, 3 * mm))
    historia.append(Paragraph(
        "La cartera pendiente corresponde al saldo actual de todos los créditos con saldo positivo; "
        "no representa una reconstrucción histórica al cierre del período.", estilos["Nota"]
    ))

    historia.append(Paragraph("Detalle de préstamos del período", estilos["Seccion"]))
    encabezados_prestamos = ["Crédito", "Cliente", "Usuario", "Fecha", "Capital", "Intereses", "Total", "Abonado", "Saldo", "Vencimiento", "Estado"]
    filas_prestamos = [[Paragraph(f"<b>{h}</b>", estilos["Celda"]) for h in encabezados_prestamos]]
    for prestamo in prestamos_periodo:
        abonado = sum((_decimal(p.valor_pago) for p in prestamo.pagos), Decimal("0"))
        cliente = f"{prestamo.usuario.nombres} {prestamo.usuario.apellidos}"
        filas_prestamos.append([
            f"#{prestamo.id_prestamo}",
            Paragraph(cliente, estilos["CeldaPequena"]),
            Paragraph(prestamo.usuario.usuario or "", estilos["CeldaPequena"]),
            fecha_texto(prestamo.fecha_prestamo), moneda(prestamo.capital),
            moneda(prestamo.interes_acumulado), moneda(prestamo.pago_total),
            moneda(abonado), moneda(prestamo.saldo_pendiente),
            fecha_texto(prestamo.fecha_vencimiento), prestamo.estado
        ])
    if not prestamos_periodo:
        filas_prestamos.append([Paragraph("No hay préstamos registrados en este período.", estilos["Celda"])] + [""] * 10)
    tabla_prestamos = Table(
        filas_prestamos,
        colWidths=[12*mm, 34*mm, 18*mm, 18*mm, 22*mm, 22*mm, 22*mm, 22*mm, 22*mm, 18*mm, 17*mm],
        repeatRows=1, hAlign="LEFT"
    )
    tabla_prestamos.setStyle(TableStyle([
        ("SPAN", (0, 1), (-1, 1)) if not prestamos_periodo else ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1CA58D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    historia.append(tabla_prestamos)

    historia.append(Paragraph("Detalle de pagos recibidos en el período", estilos["Seccion"]))
    encabezados_pagos = ["Pago", "Crédito", "Cliente", "Usuario", "Fecha de pago", "Valor recibido", "Observación"]
    filas_pagos = [[Paragraph(f"<b>{h}</b>", estilos["Celda"]) for h in encabezados_pagos]]
    for pago in pagos_periodo:
        cliente = pago.prestamo.usuario
        nombre_cliente = f"{cliente.nombres} {cliente.apellidos}"
        filas_pagos.append([
            f"#{pago.id_pago}", f"#{pago.prestamo_id}",
            Paragraph(nombre_cliente, estilos["CeldaPequena"]),
            Paragraph(cliente.usuario or "", estilos["CeldaPequena"]),
            fecha_texto(pago.fecha_pago), moneda(pago.valor_pago),
            Paragraph((pago.observacion or "Sin observación"), estilos["CeldaPequena"])
        ])
    if not pagos_periodo:
        filas_pagos.append([Paragraph("No hay pagos registrados en este período.", estilos["Celda"])] + [""] * 6)
    tabla_pagos = Table(
        filas_pagos,
        colWidths=[18*mm, 20*mm, 48*mm, 27*mm, 28*mm, 30*mm, 78*mm],
        repeatRows=1, hAlign="LEFT"
    )
    tabla_pagos.setStyle(TableStyle([
        ("SPAN", (0, 1), (-1, 1)) if not pagos_periodo else ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1CA58D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    historia.append(tabla_pagos)

    def pie_pagina(canvas, doc):
        canvas.saveState()
        ancho, alto = landscape(letter)
        canvas.setStrokeColor(colors.HexColor("#D9E2F0"))
        canvas.setLineWidth(0.5)
        canvas.line(15 * mm, 12 * mm, ancho - 15 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#60758C"))
        canvas.drawString(15 * mm, 7 * mm, "DROP BY DROP | Informe financiero de uso administrativo")
        canvas.drawRightString(ancho - 15 * mm, 7 * mm, f"Página {doc.page}")
        canvas.restoreState()

    documento.build(historia, onFirstPage=pie_pagina, onLaterPages=pie_pagina)
    salida.seek(0)
    nombre_archivo = f"informe_financiero_drop_by_drop_{fecha_desde:%Y%m%d}_{fecha_hasta:%Y%m%d}.pdf"

    return send_file(
        salida,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype="application/pdf"
    )
