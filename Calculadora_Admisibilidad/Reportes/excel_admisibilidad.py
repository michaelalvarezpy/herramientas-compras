
from io import BytesIO
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ============================================================
# GENERADOR DE INFORME EXCEL - CALCULADORA DE ADMISIBILIDAD
# ============================================================
# Genera un archivo Excel con:
# 1. Evaluación económica de la oferta.
# 2. Tabla de porcentajes de admisibilidad.
#
# Los cálculos se realizan en app_admisibilidad.py.
# Este módulo solamente presenta los resultados.
# ============================================================


def generar_excel_admisibilidad(datos, tabla_admisibilidad):

    # --------------------------------------------------------
    # 1. CREAR LIBRO EXCEL
    # --------------------------------------------------------

    libro = Workbook()

    hoja_evaluacion = libro.active
    hoja_evaluacion.title = "Evaluación de Admisibilidad"

    hoja_tabla = libro.create_sheet("Tabla de Admisibilidad")

    # --------------------------------------------------------
    # 2. COLORES DEL INFORME
    # --------------------------------------------------------

    azul_oscuro = "173454"
    azul_claro = "DCEBFF"
    turquesa = "20BFAF"
    blanco = "FFFFFF"
    gris_claro = "F1F5F9"
    gris_texto = "475569"

    # --------------------------------------------------------
    # 3. CONFIGURACIÓN DE COLUMNAS
    # --------------------------------------------------------

    hoja_evaluacion.column_dimensions["A"].width = 5
    hoja_evaluacion.column_dimensions["B"].width = 38
    hoja_evaluacion.column_dimensions["C"].width = 27
    hoja_evaluacion.column_dimensions["D"].width = 22

    hoja_tabla.column_dimensions["A"].width = 8
    hoja_tabla.column_dimensions["B"].width = 43
    hoja_tabla.column_dimensions["C"].width = 22

    # --------------------------------------------------------
    # 4. ENCABEZADO PRINCIPAL
    # --------------------------------------------------------

    hoja_evaluacion.merge_cells("B2:D3")

    titulo = hoja_evaluacion["B2"]
    titulo.value = "INFORME DE ADMISIBILIDAD ECONÓMICA"
    titulo.font = Font(
        name="Aptos",
        size=16,
        bold=True,
        color=blanco
    )
    titulo.fill = PatternFill(
        "solid",
        fgColor=azul_oscuro
    )
    titulo.alignment = Alignment(
        horizontal="center",
        vertical="center"
    )

    hoja_evaluacion["B5"] = "Fecha de generación"
    hoja_evaluacion["C5"] = datetime.now()
    hoja_evaluacion["C5"].number_format = "dd-mm-yyyy hh:mm"

    # --------------------------------------------------------
    # 5. FUNCIÓN PARA CREAR SECCIONES
    # --------------------------------------------------------

    def crear_seccion(hoja, fila, titulo_seccion):

        hoja.merge_cells(
            start_row=fila,
            start_column=2,
            end_row=fila,
            end_column=4
        )

        celda = hoja.cell(
            row=fila,
            column=2,
            value=titulo_seccion
        )

        celda.fill = PatternFill(
            "solid",
            fgColor=azul_oscuro
        )

        celda.font = Font(
            name="Aptos",
            size=11,
            bold=True,
            color=blanco
        )

        celda.alignment = Alignment(
            vertical="center"
        )

        hoja.row_dimensions[fila].height = 25

    # --------------------------------------------------------
    # 6. FUNCIÓN PARA AGREGAR DATOS
    # --------------------------------------------------------

    def agregar_dato(hoja, fila, etiqueta, valor):

        celda_etiqueta = hoja.cell(
            row=fila,
            column=2,
            value=etiqueta
        )

        celda_valor = hoja.cell(
            row=fila,
            column=3,
            value=valor
        )

        celda_etiqueta.font = Font(
            name="Aptos",
            bold=True,
            color=gris_texto
        )

        celda_valor.font = Font(
            name="Aptos",
            color=azul_oscuro
        )
        
        # ----------------------------------------------------
        # FORMATO DE MONTOS, PORCENTAJES Y COTIZACIONES
        # ----------------------------------------------------
        # Mantiene los valores como números para que puedan
        # utilizarse posteriormente en fórmulas de Excel.
        # Los porcentajes se reciben como valores de 0 a 100.

        moneda_solicitud = datos.get("moneda_solicitud", "CLP")
        moneda_oferta = datos.get("moneda_oferta", "CLP")

        formato_monedas = {
            "CLP": '"CLP " #,##0;[Red]("CLP " #,##0)',
            "USD": '"USD " #,##0.00;[Red]("USD " #,##0.00)',
            "EUR": '"EUR " #,##0.00;[Red]("EUR " #,##0.00)',
            "UF": '"UF " #,##0.00;[Red]("UF " #,##0.00)',
        }

        formato_solicitud = formato_monedas[moneda_solicitud]
        formato_oferta = formato_monedas[moneda_oferta]

        etiquetas_monedas = {
            "Monto de la solicitud": formato_solicitud,
            "Monto de la oferta recibida": formato_oferta,
            "Oferta convertida a moneda de solicitud": formato_solicitud,
            "Solicitud equivalente en USD": formato_monedas["USD"],
            "Límite inferior": formato_solicitud,
            "Límite superior": formato_solicitud,
            "Diferencia económica": formato_solicitud,
            "Rebaja mínima requerida": formato_solicitud,
            "Monto bajo el límite admisible": formato_solicitud,
            "Oferta máxima admisible": formato_solicitud,
            "Rebaja en moneda del proveedor": formato_oferta,
            "Máximo en moneda del proveedor": formato_oferta,
        }

        etiquetas_porcentajes = {
            "Porcentaje de admisibilidad",
            "Desviación de la oferta (%)",
            "Descuento requerido (%)",
        }

        etiquetas_cotizaciones = {
            "Dólar observado (CLP/USD)": '#,##0.0000',
            "Euro (USD/EUR)": '#,##0.000000',
            "Valor UF (CLP/UF)": '#,##0.0000',
        }

        if isinstance(valor, (int, float)) and not isinstance(valor, bool):

            if etiqueta in etiquetas_monedas:
                celda_valor.number_format = etiquetas_monedas[etiqueta]

            elif etiqueta in etiquetas_porcentajes:
                celda_valor.number_format = '0.00"%"'

            elif etiqueta in etiquetas_cotizaciones:
                celda_valor.number_format = etiquetas_cotizaciones[etiqueta]

            celda_valor.alignment = Alignment(horizontal="right")

        if fila % 2 == 0:
            for columna in (2, 3, 4):
                hoja.cell(
                    row=fila,
                    column=columna
                ).fill = PatternFill(
                    "solid",
                    fgColor=gris_claro
                )

        hoja.row_dimensions[fila].height = 22

    # --------------------------------------------------------
    # 7. ANTECEDENTES DE LA EVALUACIÓN
    # --------------------------------------------------------

    crear_seccion(
        hoja_evaluacion,
        7,
        "01 / ANTECEDENTES DE LA EVALUACIÓN"
    )

    agregar_dato(
        hoja_evaluacion,
        9,
        "Monto de la solicitud",
        datos.get("monto_solicitud")
    )

    agregar_dato(
        hoja_evaluacion,
        10,
        "Moneda de la solicitud",
        datos.get("moneda_solicitud")
    )

    agregar_dato(
        hoja_evaluacion,
        11,
        "Monto de la oferta recibida",
        datos.get("monto_oferta")
    )

    agregar_dato(
        hoja_evaluacion,
        12,
        "Moneda de la oferta",
        datos.get("moneda_oferta")
    )

    agregar_dato(
        hoja_evaluacion,
        13,
        "Oferta convertida a moneda de solicitud",
        datos.get("oferta_convertida")
    )

    # --------------------------------------------------------
    # 8. TIPOS DE CAMBIO UTILIZADOS
    # --------------------------------------------------------

    crear_seccion(
        hoja_evaluacion,
        15,
        "02 / TIPOS DE CAMBIO UTILIZADOS"
    )

    agregar_dato(
        hoja_evaluacion,
        17,
        "Dólar observado (CLP/USD)",
        datos.get("dolar_clp")
    )

    agregar_dato(
        hoja_evaluacion,
        18,
        "Euro (USD/EUR)",
        datos.get("euro_usd")
    )

    agregar_dato(
        hoja_evaluacion,
        19,
        "Valor UF (CLP/UF)",
        datos.get("valor_uf")
    )

    agregar_dato(
        hoja_evaluacion,
        20,
        "Fecha de referencia",
        datos.get("fecha_cotizacion")
    )

    agregar_dato(
        hoja_evaluacion,
        21,
        "Origen de cotizaciones",
        datos.get("origen_cotizaciones")
    )
    
    # Formato de fecha de referencia
    hoja_evaluacion["C20"].number_format = "dd-mm-yyyy"

    # --------------------------------------------------------
    # 9. RESULTADOS DE ADMISIBILIDAD
    # --------------------------------------------------------

    crear_seccion(
        hoja_evaluacion,
        23,
        "03 / RESULTADOS DE ADMISIBILIDAD"
    )

    resultados = [
        ("Solicitud equivalente en USD", "monto_usd"),
        ("Porcentaje de admisibilidad", "porcentaje"),
        ("Límite inferior", "limite_inferior"),
        ("Límite superior", "limite_superior"),
        ("Desviación de la oferta (%)", "desviacion"),
        ("Diferencia económica", "diferencia_economica"),
        ("Resultado de evaluación", "resultado"),
    ]

    for fila, (etiqueta, clave) in enumerate(
        resultados,
        start=25
    ):
        agregar_dato(
            hoja_evaluacion,
            fila,
            etiqueta,
            datos.get(clave)
        )
        
    # --------------------------------------------------------
    # DESTACAR VISUALMENTE EL RESULTADO DE ADMISIBILIDAD
    # --------------------------------------------------------

    celda_resultado = hoja_evaluacion["C31"]

    resultado_evaluacion = str(
        datos.get("resultado") or ""
    ).upper()

    if resultado_evaluacion == "OFERTA ADMISIBLE":

        celda_resultado.fill = PatternFill(
            "solid",
            fgColor="DCFCE7"
        )

        celda_resultado.font = Font(
            name="Aptos",
            bold=True,
            color="166534"
        )

    elif "FUERA" in resultado_evaluacion:

        celda_resultado.fill = PatternFill(
            "solid",
            fgColor="FEE2E2"
        )

        celda_resultado.font = Font(
            name="Aptos",
            bold=True,
            color="991B1B"
        )

    else:

        celda_resultado.fill = PatternFill(
            "solid",
            fgColor="FEF3C7"
        )

        celda_resultado.font = Font(
            name="Aptos",
            bold=True,
            color="92400E"
        )

    hoja_evaluacion.merge_cells("C31:D31")

    celda_resultado.alignment = Alignment(
        horizontal="center",
        vertical="center",
        wrap_text=True
    )

    hoja_evaluacion.row_dimensions[31].height = 36

    # --------------------------------------------------------
    # 10. RECOMENDACIÓN DE NEGOCIACIÓN
    # --------------------------------------------------------

    crear_seccion(
        hoja_evaluacion,
        34,
        "04 / ANÁLISIS Y RECOMENDACIÓN"
    )
    
    # --------------------------------------------------------
    # OBSERVACIÓN SEGÚN EL RESULTADO DE LA EVALUACIÓN
    # --------------------------------------------------------
    # La recomendación depende de la posición de la oferta
    # respecto de los límites económicos permitidos.

    oferta_evaluada = datos.get("oferta_convertida")
    limite_minimo = datos.get("limite_inferior")
    limite_maximo = datos.get("limite_superior")

    observacion = datos.get("observacion")

    if all(
        isinstance(valor, (int, float))
        for valor in (oferta_evaluada, limite_minimo, limite_maximo)
    ):

        if limite_minimo <= oferta_evaluada <= limite_maximo:
            observacion = (
                "La oferta cumple con los límites económicos "
                "de admisibilidad establecidos."
            )

        elif oferta_evaluada > limite_maximo:
            observacion = (
                "La oferta supera el límite máximo de admisibilidad. "
                "Se recomienda negociar una reducción del precio "
                "hasta alcanzar un valor admisible."
            )

        else:
            observacion = (
                "La oferta se encuentra por debajo del límite mínimo "
                "de admisibilidad. Se recomienda revisar los antecedentes "
                "económicos y técnicos antes de continuar."
            )

    agregar_dato(
        hoja_evaluacion,
        36,
        "Observación",
        observacion
    )

    # --------------------------------------------------------
    # MOSTRAR NEGOCIACIÓN SOLO CUANDO CORRESPONDA
    # --------------------------------------------------------

    if (
        isinstance(oferta_evaluada, (int, float))
        and isinstance(limite_minimo, (int, float))
        and isinstance(limite_maximo, (int, float))
    ):

        if oferta_evaluada > limite_maximo:

            agregar_dato(
                hoja_evaluacion,
                37,
                "Rebaja mínima requerida",
                oferta_evaluada - limite_maximo
            )

            agregar_dato(
                hoja_evaluacion,
                38,
                "Descuento requerido (%)",
                (oferta_evaluada - limite_maximo)
                / oferta_evaluada * 100
            )

            agregar_dato(
                hoja_evaluacion,
                39,
                "Oferta máxima admisible",
                limite_maximo
            )

            if datos.get("moneda_oferta") != datos.get("moneda_solicitud"):

                agregar_dato(
                    hoja_evaluacion,
                    40,
                    "Rebaja en moneda del proveedor",
                    datos.get("rebaja_moneda_oferta")
                )

                agregar_dato(
                    hoja_evaluacion,
                    41,
                    "Máximo en moneda del proveedor",
                    datos.get("maximo_moneda_oferta")
                )

        elif oferta_evaluada < limite_minimo:

            agregar_dato(
                hoja_evaluacion,
                37,
                "Monto bajo el límite admisible",
                limite_minimo - oferta_evaluada
            )

    # Ajustar la presentación de la observación.
    hoja_evaluacion.merge_cells("C36:D36")

    hoja_evaluacion["C36"].alignment = Alignment(
        horizontal="left",
        vertical="center",
        wrap_text=True
    )

    hoja_evaluacion.row_dimensions[36].height = 60

    # --------------------------------------------------------
    # 11. TABLA DE PORCENTAJES DE ADMISIBILIDAD
    # --------------------------------------------------------

    hoja_tabla.merge_cells("B2:C3")

    titulo_tabla = hoja_tabla["B2"]
    titulo_tabla.value = "TABLA DE ADMISIBILIDAD"
    titulo_tabla.fill = PatternFill(
        "solid",
        fgColor=azul_oscuro
    )
    titulo_tabla.font = Font(
        name="Aptos",
        size=15,
        bold=True,
        color=blanco
    )
    titulo_tabla.alignment = Alignment(
        horizontal="center",
        vertical="center"
    )

    hoja_tabla["B5"] = "Monto de solicitud (USD)"
    hoja_tabla["C5"] = "Admisibilidad"

    for columna in ("B", "C"):
        celda = hoja_tabla[f"{columna}5"]
        celda.fill = PatternFill(
            "solid",
            fgColor=azul_oscuro
        )
        celda.font = Font(
            bold=True,
            color=blanco
        )
        celda.alignment = Alignment(
            horizontal="center"
        )

    for fila, tramo in enumerate(
        tabla_admisibilidad,
        start=6
    ):

        hoja_tabla.cell(
            row=fila,
            column=2,
            value=tramo["Monto de solicitud (USD)"]
        )

        hoja_tabla.cell(
            row=fila,
            column=3,
            value=tramo["Admisibilidad"]
        )

        hoja_tabla.row_dimensions[fila].height = 23

        if fila % 2 == 0:
            for columna in (2, 3):
                hoja_tabla.cell(
                    row=fila,
                    column=columna
                ).fill = PatternFill(
                    "solid",
                    fgColor=gris_claro
                )

    hoja_tabla["B17"] = (
        "El porcentaje aplicable se determina según "
        "el monto de la solicitud expresado en USD."
    )

    hoja_tabla.merge_cells("B17:C17")

    hoja_tabla["B17"].font = Font(
        italic=True,
        color=gris_texto
    )
    
    # Ajustar la nota explicativa de la tabla
    hoja_tabla["B17"].alignment = Alignment(
        horizontal="left",
        vertical="center",
        wrap_text=True
    )

    hoja_tabla.row_dimensions[17].height = 45

    # --------------------------------------------------------
    # 12. CONFIGURACIÓN FINAL Y EXPORTACIÓN
    # --------------------------------------------------------

    hoja_evaluacion.sheet_view.showGridLines = False
    hoja_tabla.sheet_view.showGridLines = False

    hoja_evaluacion.freeze_panes = "B7"
    hoja_tabla.freeze_panes = "B6"

    archivo = BytesIO()
    libro.save(archivo)
    archivo.seek(0)

    return archivo.getvalue()
