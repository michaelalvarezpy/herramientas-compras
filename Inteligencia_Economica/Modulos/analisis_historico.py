import streamlit as st
from datetime import date, timedelta
from calendar import monthrange
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

import pandas as pd
import plotly.graph_objects as go

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Font, PatternFill, Alignment

from Inteligencia_Economica.Servicios.banco_central import consultar_monedas, consultar_ipc
from Inteligencia_Economica.Servicios.cobre import consultar_cobre




def crear_informe_excel_historico(serie, moneda, nombre_periodo, fecha_inicio,
                                  fecha_fin, periodo_incompleto):
    """Genera en memoria un informe Excel con resumen, gráfico y datos."""
    libro = Workbook()
    resumen = libro.active
    resumen.title = "Resumen económico"
    grafico = libro.create_sheet("Gráfico histórico")
    datos = libro.create_sheet("Datos históricos")

    azul = "17324D"
    turquesa = "19A7A0"
    claro = "EAF3F7"
    formato_numero = '#,##0.00 "CLP"'
    formato_porcentaje = '+0.00%;-0.00%;0.00%'
    formato_fecha = "DD-MM-YYYY"

    def encabezado(hoja, titulo, columnas):
        hoja.merge_cells(start_row=1, start_column=1, end_row=1, end_column=columnas)
        celda = hoja.cell(1, 1, titulo)
        celda.font = Font(name="Aptos Display", size=17, bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=azul)
        celda.alignment = Alignment(vertical="center")
        hoja.row_dimensions[1].height = 34
        hoja.sheet_view.showGridLines = False

    def fila_etiqueta(hoja, fila, etiqueta, valor, formato=None):
        celda = hoja.cell(fila, 1, etiqueta)
        celda.font = Font(name="Aptos", bold=True, color=azul)
        celda.fill = PatternFill("solid", fgColor=claro)
        resultado = hoja.cell(fila, 2, valor)
        resultado.font = Font(name="Aptos", color="17324D")
        if formato:
            resultado.number_format = formato

    inicial = float(serie.iloc[0])
    final = float(serie.iloc[-1])
    variacion = final - inicial
    variacion_pct = variacion / inicial if inicial else 0.0
    if variacion_pct > 0.001:
        tendencia = "Alza"
    elif variacion_pct < -0.001:
        tendencia = "Baja"
    else:
        tendencia = "Relativamente estable"

    encabezado(resumen, "INFORME DE ANÁLISIS HISTÓRICO", 2)
    resumen.column_dimensions["A"].width = 33
    resumen.column_dimensions["B"].width = 49
    contenido = [
        (3, "Moneda", moneda, None),
        (4, "Período", nombre_periodo, None),
        (5, "Fecha inicial consultada", fecha_inicio, formato_fecha),
        (6, "Fecha final consultada", fecha_fin, formato_fecha),
        (7, "Primer registro disponible", serie.index[0].to_pydatetime(), formato_fecha),
        (8, "Último registro disponible", serie.index[-1].to_pydatetime(), formato_fecha),
        (9, "Cantidad de registros", len(serie), None),
        (11, "Valor inicial", inicial, formato_numero),
        (12, "Valor final", final, formato_numero),
        (13, "Valor máximo", float(serie.max()), formato_numero),
        (14, "Fecha del máximo", serie.idxmax().to_pydatetime(), formato_fecha),
        (15, "Valor mínimo", float(serie.min()), formato_numero),
        (16, "Fecha del mínimo", serie.idxmin().to_pydatetime(), formato_fecha),
        (17, "Valor promedio", float(serie.mean()), formato_numero),
        (18, "Variación absoluta", variacion, formato_numero),
        (19, "Variación porcentual", variacion_pct, formato_porcentaje),
        (20, "Tendencia observada", tendencia, None),
        (22, "Estado del período", "Resultados parciales" if periodo_incompleto else "Período consultado", None),
        (23, "Fuente", "Banco Central de Chile", None),
        (24, "Generado el", date.today(), formato_fecha),
    ]
    for fila, etiqueta, valor, formato in contenido:
        fila_etiqueta(resumen, fila, etiqueta, valor, formato)
    resumen.merge_cells("A26:B26")
    resumen["A26"] = "Variación calculada entre el primer y último registro disponible. No es una proyección."
    resumen["A26"].font = Font(name="Aptos", italic=True, color="657587", size=10)
    resumen.freeze_panes = "B3"
    resumen.print_options.horizontalCentered = True
    resumen.sheet_properties.pageSetUpPr.fitToPage = True
    resumen.page_setup.fitToWidth = 1

    encabezado(datos, f"DATOS HISTÓRICOS · {moneda}", 4)
    for columna, ancho in {"A": 19, "B": 24, "C": 27, "D": 27}.items():
        datos.column_dimensions[columna].width = ancho
    titulos = ["Fecha", f"Valor {moneda} (CLP)", "Variación vs. registro anterior (CLP)", "Variación vs. registro anterior (%)"]
    for col, titulo in enumerate(titulos, 1):
        celda = datos.cell(3, col, titulo)
        celda.fill = PatternFill("solid", fgColor=azul)
        celda.font = Font(name="Aptos", bold=True, color="FFFFFF")
        celda.alignment = Alignment(wrap_text=True, vertical="center")
    datos.row_dimensions[3].height = 34
    anterior = None
    for fila, (fecha, valor) in enumerate(serie.items(), 4):
        actual = float(valor)
        datos.cell(fila, 1, fecha.to_pydatetime()).number_format = formato_fecha
        datos.cell(fila, 2, actual).number_format = formato_numero
        if anterior is not None:
            datos.cell(fila, 3, actual - anterior).number_format = formato_numero
            if anterior:
                datos.cell(fila, 4, (actual - anterior) / anterior).number_format = formato_porcentaje
        if fila % 2 == 0:
            for col in range(1, 5):
                datos.cell(fila, col).fill = PatternFill("solid", fgColor="F3F8FA")
        anterior = actual
    ultima_fila = len(serie) + 3
    datos.auto_filter.ref = f"A3:D{ultima_fila}"
    datos.freeze_panes = "A4"

    encabezado(grafico, f"EVOLUCIÓN HISTÓRICA · {moneda}", 4)
    grafico.column_dimensions["A"].width = 19
    grafico.column_dimensions["B"].width = 25
    grafico["A3"] = "Moneda"
    grafico["B3"] = moneda
    grafico["A4"] = "Período"
    grafico["B4"] = nombre_periodo
    grafico["A5"] = "Fuente"
    grafico["B5"] = "Banco Central de Chile"
    grafico["A6"] = "Nota"
    grafico["B6"] = "Valores históricos, no proyecciones"
    grafico.column_dimensions["B"].width = 43
    # Gráfico compatible con Excel Online: eje de categorías simple.
    # Evitamos DateAxis, cuya configuración anterior provocó una reparación del libro.
    linea = LineChart()
    linea.title = f"Evolución de {moneda}"
    linea.y_axis.title = "Pesos chilenos (CLP)"
    linea.x_axis.title = "Fecha (registros disponibles)"
    linea.style = 13
    linea.width = 25
    linea.height = 13
    linea.add_data(Reference(datos, min_col=2, min_row=3, max_row=ultima_fila), titles_from_data=True)
    linea.set_categories(Reference(datos, min_col=1, min_row=4, max_row=ultima_fila))
    linea.legend = None
    grafico.add_chart(linea, "A9")

    salida = BytesIO()
    libro.save(salida)
    salida.seek(0)
    return salida.getvalue()



def crear_tarjeta_png_historico(serie, moneda, nombre_periodo, periodo_incompleto):
    """Crea una tarjeta PNG compartible con los datos históricos seleccionados."""
    imagen = Image.new("RGB", (1200, 800), "#0B1627")
    dibujo = ImageDraw.Draw(imagen)

    def fuente(tamano, negrita=False):
        # Fuentes del sistema; respaldo incluido para distintos equipos.
        candidatos = (
            ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
            if negrita else
            ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        )
        for ruta in candidatos:
            try:
                return ImageFont.truetype(ruta, tamano)
            except OSError:
                continue
        return ImageFont.load_default()

    def numero(valor):
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def dato(x, y, etiqueta, valor, color="#F4F8FF"):
        dibujo.text((x, y), etiqueta, font=fuente(20), fill="#A9BBD0")
        dibujo.text((x, y + 31), valor, font=fuente(35, True), fill=color)

    inicial = float(serie.iloc[0])
    final = float(serie.iloc[-1])
    cambio = final - inicial
    porcentaje = (cambio / inicial * 100) if inicial else 0.0
    tendencia = "Alza" if porcentaje > 0.1 else "Baja" if porcentaje < -0.1 else "Relativamente estable"
    color_tendencia = "#55DFC7" if porcentaje > 0.1 else "#FF9A90" if porcentaje < -0.1 else "#D9E6F5"

    dibujo.rounded_rectangle((24, 24, 1176, 776), radius=30, fill="#14273C", outline="#2D4760", width=2)
    dibujo.text((65, 58), "INTELIGENCIA ECONÓMICA  /  HERRAMIENTAS DE COMPRAS", font=fuente(19, True), fill="#55DFC7")
    dibujo.text((65, 103), f"Resumen histórico · {moneda}", font=fuente(43, True), fill="#FFFFFF")
    periodo = nombre_periodo + ("  ·  Resultados parciales" if periodo_incompleto else "")
    dibujo.text((67, 165), periodo, font=fuente(23), fill="#B8CADD")
    dibujo.line((65, 216, 1135, 216), fill="#38536C", width=2)

    dato(68, 248, "VALOR INICIAL", f"${numero(inicial)}")
    dato(645, 248, "VALOR FINAL", f"${numero(final)}")
    dato(68, 348, "VALOR MÁXIMO", f"${numero(float(serie.max()))}")
    dato(645, 348, "VALOR MÍNIMO", f"${numero(float(serie.min()))}")
    dato(68, 448, "VALOR PROMEDIO", f"${numero(float(serie.mean()))}")
    dato(645, 448, "VARIACIÓN DEL PERÍODO", f"{porcentaje:+.2f}%".replace(".", ","), color_tendencia)

    dibujo.rounded_rectangle((65, 562, 1135, 655), radius=16, fill="#203C53")
    dibujo.text((90, 576), f"Tendencia observada: {tendencia}", font=fuente(25, True), fill=color_tendencia)
    dibujo.text((90, 615), f"Variación absoluta: {numero(cambio)} CLP  |  {len(serie)} registros disponibles", font=fuente(19), fill="#E2EDF7")
    dibujo.text((68, 681), f"Primer registro: {serie.index[0]:%d-%m-%Y}   |   Último registro: {serie.index[-1]:%d-%m-%Y}", font=fuente(19), fill="#D5E3EF")
    dibujo.text((68, 718), "Fuente: Banco Central de Chile · Variación histórica, no es una proyección.", font=fuente(17), fill="#9EB3C9")

    salida = BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return salida.getvalue()


def crear_informe_excel_ipc(visible, variacion_mensual, variacion_anual, nombre_periodo):
    """Genera un informe Excel del IPC para el período seleccionado."""
    libro = Workbook()
    resumen = libro.active
    resumen.title = "Resumen IPC"
    grafico = libro.create_sheet("Gráfico histórico")
    datos = libro.create_sheet("Datos históricos")

    azul = "17324D"
    claro = "EAF3F7"
    formato_indice = '#,##0.00'
    formato_porcentaje = '+0.00%;-0.00%;0.00%'

    # Hoja 1: resumen del período seleccionado.
    resumen.merge_cells("A1:B1")
    resumen["A1"] = "INFORME HISTÓRICO DEL IPC"
    resumen["A1"].font = Font(size=17, bold=True, color="FFFFFF")
    resumen["A1"].fill = PatternFill("solid", fgColor=azul)
    resumen.row_dimensions[1].height = 34
    resumen.column_dimensions["A"].width = 35
    resumen.column_dimensions["B"].width = 42

    inicial = float(visible.iloc[0])
    final = float(visible.iloc[-1])
    variacion_periodo = (final / inicial - 1) if inicial else None

    contenido = [
        ("Indicador", "IPC de Chile (base 2023 = 100)"),
        ("Período seleccionado", nombre_periodo),
        ("Primer mes mostrado", visible.index[0].strftime("%m-%Y")),
        ("Último mes mostrado", visible.index[-1].strftime("%m-%Y")),
        ("Meses mostrados", len(visible)),
        ("Índice inicial", inicial),
        ("Índice final", final),
        ("Variación del período", variacion_periodo),
        ("Fuente", "Banco Central de Chile"),
        ("Fecha de elaboración", date.today()),
    ]

    for fila, (etiqueta, valor) in enumerate(contenido, 3):
        resumen.cell(fila, 1, etiqueta)
        resumen.cell(fila, 2, valor)
        resumen.cell(fila, 1).font = Font(bold=True, color=azul)
        resumen.cell(fila, 1).fill = PatternFill("solid", fgColor=claro)

    for fila in (8, 9):
        resumen.cell(fila, 2).number_format = formato_indice
    if variacion_periodo is not None:
        resumen["B10"].number_format = formato_porcentaje
    resumen["B12"].number_format = "DD-MM-YYYY"
    resumen["A14"] = "La variación compara el primer y último índice mostrado."
    resumen["A15"] = "No equivale necesariamente a la inflación acumulada anual."
    resumen.sheet_view.showGridLines = False

    # Hoja 3: datos numéricos del período visible.
    encabezados = [
        "Mes", "Índice IPC", "Variación mensual (%)",
        "Variación a 12 meses (%)"
    ]
    for columna, titulo in enumerate(encabezados, 1):
        celda = datos.cell(1, columna, titulo)
        celda.fill = PatternFill("solid", fgColor=azul)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.alignment = Alignment(wrap_text=True)

    for fila, (mes, indice) in enumerate(visible.items(), 2):
        datos.cell(fila, 1, mes.to_timestamp())
        datos.cell(fila, 1).number_format = "MM-YYYY"
        datos.cell(fila, 2, float(indice))
        datos.cell(fila, 2).number_format = formato_indice
        mensual = variacion_mensual.loc[mes]
        anual = variacion_anual.loc[mes]
        if pd.notna(mensual):
            datos.cell(fila, 3, float(mensual) / 100)
            datos.cell(fila, 3).number_format = formato_porcentaje
        if pd.notna(anual):
            datos.cell(fila, 4, float(anual) / 100)
            datos.cell(fila, 4).number_format = formato_porcentaje

    for columna, ancho in {"A": 19, "B": 22, "C": 27, "D": 30}.items():
        datos.column_dimensions[columna].width = ancho
    datos.freeze_panes = "A2"
    datos.auto_filter.ref = f"A1:D{datos.max_row}"
    datos.sheet_view.showGridLines = False

    # Hoja 2: gráfico con datos auxiliares en la MISMA hoja.
    # Excel Online suele omitir las etiquetas cuando el gráfico apunta a
    # categorías de otra hoja o a una columna oculta.
    grafico["A1"] = "EVOLUCIÓN MENSUAL DEL IPC"
    grafico["A1"].font = Font(size=16, bold=True, color=azul)
    grafico["A3"] = "Período"
    grafico["B3"] = nombre_periodo
    grafico["A4"] = "Fuente"
    grafico["B4"] = "Banco Central de Chile"
    grafico["A5"] = "Lectura"
    grafico["B5"] = "Cada punto representa el índice publicado de un mes"
    grafico.column_dimensions["A"].width = 19
    grafico.column_dimensions["B"].width = 48

    # Tabla visible y legible debajo del gráfico, como respaldo para
    # Excel Online si el navegador no representa etiquetas del gráfico.
    fila_tabla = 38
    grafico.cell(fila_tabla, 1, "Mes")
    grafico.cell(fila_tabla, 2, "Índice IPC")
    grafico.cell(fila_tabla, 3, "Variación mensual")
    for col in range(1, 4):
        encabezado = grafico.cell(fila_tabla, col)
        encabezado.font = Font(bold=True, color="FFFFFF")
        encabezado.fill = PatternFill("solid", fgColor=azul)
    grafico.column_dimensions["C"].width = 23

    for i, (mes, indice) in enumerate(visible.items(), fila_tabla + 1):
        grafico.cell(i, 1, mes.strftime("%m-%Y"))  # Categoría de texto explícita
        grafico.cell(i, 2, float(indice))
        grafico.cell(i, 2).number_format = formato_indice
        mensual = variacion_mensual.loc[mes]
        if pd.notna(mensual):
            grafico.cell(i, 3, float(mensual) / 100)
            grafico.cell(i, 3).number_format = formato_porcentaje

    # Gráfico como imagen de alta resolución para asegurar una presentación
    # idéntica en Excel Online y Excel de escritorio. Los datos siguen siendo
    # numéricos y editables en la hoja "Datos históricos".
    from math import floor, ceil
    from pathlib import Path

    ancho_img, alto_img = 1600, 700
    imagen = Image.new("RGB", (ancho_img, alto_img), "#FFFFFF")
    dibujo = ImageDraw.Draw(imagen)

    def fuente(tamano, negrita=False):
        rutas = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if negrita else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if negrita else "C:/Windows/Fonts/arial.ttf",
        ]
        for ruta in rutas:
            if Path(ruta).exists():
                return ImageFont.truetype(ruta, tamano)
        return ImageFont.load_default()

    ft_titulo = fuente(32, True)
    ft_sub = fuente(20)
    ft_ejes = fuente(19)
    ft_valor = fuente(19, True)
    ft_pie = fuente(17)
    azul_linea = "#1677B8"
    azul_titulo = "#17324D"
    gris = "#66788A"
    dibujo.text((90, 35), "EVOLUCIÓN MENSUAL DEL IPC", fill=azul_titulo, font=ft_titulo)
    dibujo.text((90, 88), f"{nombre_periodo}  |  Índice base 2023 = 100", fill=gris, font=ft_sub)

    xs, ys = [], []
    valores = [float(v) for v in visible.values]
    n = len(valores)
    izq, der, sup, inf = 112, 1520, 175, 555
    minimo, maximo = min(valores), max(valores)
    margen = max((maximo - minimo) * 0.22, 0.45)
    y_min = floor((minimo - margen) * 2) / 2
    y_max = ceil((maximo + margen) * 2) / 2
    if y_max == y_min:
        y_max += 1
    for i in range(6):
        v = y_min + (y_max - y_min) * i / 5
        y = round(inf - (v - y_min) / (y_max - y_min) * (inf - sup))
        dibujo.line([(izq, y), (der, y)], fill="#E5EAF0", width=2)
        etiqueta = f"{v:.1f}".replace(".", ",")
        dibujo.text((izq - 18, y), etiqueta, fill=gris, font=ft_ejes, anchor="rm")

    for i, (mes, valor) in enumerate(visible.items()):
        x = round(izq + (der - izq) * (i / max(n - 1, 1)))
        y = round(inf - (float(valor) - y_min) / (y_max - y_min) * (inf - sup))
        xs.append(x)
        ys.append(y)
        if n <= 14 or i % 2 == 0 or i == n - 1:
            fecha = mes.strftime("%m-%Y")
            dibujo.text((x, inf + 23), fecha, fill=gris, font=ft_ejes, anchor="mt")

    if n > 1:
        dibujo.line(list(zip(xs, ys)), fill=azul_linea, width=5, joint="curve")
    for i, (x, y) in enumerate(zip(xs, ys)):
        dibujo.ellipse((x - 6, y - 6, x + 6, y + 6), fill=azul_linea)
        # Para 24 meses mostramos etiquetas alternadas y extremos; los 12 meses
        # muestran todos sus valores, con una sola cifra por punto.
        if n <= 14 or i % 2 == 0 or i == n - 1:
            etiqueta = f"{valores[i]:.2f}".replace(".", ",")
            # Alternar la posición reduce solapamientos en tramos casi planos.
            direccion = -1 if i % 2 == 0 else 1
            dy = -20 if direccion < 0 else 21
            if y + dy < sup + 5:
                dy = 22
            if y + dy > inf - 5:
                dy = -22
            dibujo.text((x, y + dy), etiqueta, fill=azul_titulo, font=ft_valor,
                        anchor="mm")

    dibujo.text((ancho_img // 2, 645), "Mes publicado", fill=azul_titulo,
                font=ft_ejes, anchor="mm")
    dibujo.text((90, 672), "Fuente: Banco Central de Chile  |  Valores mensuales publicados",
                fill=gris, font=ft_pie)
    imagen_bytes = BytesIO()
    imagen.save(imagen_bytes, format="PNG")
    imagen_bytes.seek(0)
    figura_excel = ExcelImage(imagen_bytes)
    figura_excel.width = 1120
    figura_excel.height = 490
    grafico.add_image(figura_excel, "A7")
    grafico["A36"] = "El gráfico es una imagen para garantizar su legibilidad en Excel Online."
    grafico["A37"] = "Los valores numéricos están disponibles en Datos históricos y en la tabla inferior."
    grafico.sheet_view.showGridLines = False

    # Guardar el archivo en memoria para descargarlo desde Streamlit.
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()



def crear_tarjeta_png_ipc(visible, nombre_periodo):
    """Genera una tarjeta PNG del IPC con los meses seleccionados en pantalla."""
    imagen = Image.new("RGB", (1200, 820), "#0B1627")
    dibujo = ImageDraw.Draw(imagen)

    def fuente(tamano, negrita=False):
        rutas = (
            ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
            if negrita else
            ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        )
        for ruta in rutas:
            try:
                return ImageFont.truetype(ruta, tamano)
            except OSError:
                continue
        return ImageFont.load_default()

    def numero(valor):
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    inicial = float(visible.iloc[0])
    final = float(visible.iloc[-1])
    variacion = (final / inicial - 1) * 100 if len(visible) > 1 and inicial else None
    color_variacion = (
        "#55DFC7" if variacion is not None and variacion > 0 else
        "#FF9A90" if variacion is not None and variacion < 0 else "#E2EDF7"
    )
    texto_variacion = f"{variacion:+.2f}%".replace(".", ",") if variacion is not None else "Sin datos"

    dibujo.rounded_rectangle((24, 24, 1176, 796), radius=30,
                             fill="#14273C", outline="#2D4760", width=2)
    dibujo.text((66, 58), "INTELIGENCIA ECONÓMICA  /  HERRAMIENTAS DE COMPRAS",
                 font=fuente(18, True), fill="#55DFC7")
    dibujo.text((66, 105), "Resumen histórico del IPC", font=fuente(42, True), fill="#FFFFFF")
    dibujo.text((68, 165), nombre_periodo, font=fuente(24), fill="#C0D2E3")
    dibujo.line((66, 213, 1134, 213), fill="#38536C", width=2)

    def indicador(x, y, titulo, valor, color="#FFFFFF"):
        dibujo.text((x, y), titulo, font=fuente(19), fill="#A9BBD0")
        dibujo.text((x, y + 33), valor, font=fuente(34, True), fill=color)

    indicador(70, 242, "ÍNDICE INICIAL", numero(inicial))
    indicador(640, 242, "ÍNDICE FINAL", numero(final))
    indicador(70, 347, "MESES PUBLICADOS", str(len(visible)))
    indicador(640, 347, "VARIACIÓN DEL PERÍODO", texto_variacion, color_variacion)

    # Minigráfico descriptivo: conserva los valores exactos y no proyecta datos.
    dibujo.rounded_rectangle((65, 462, 1135, 652), radius=18, fill="#203C53")
    dibujo.text((88, 477), "EVOLUCIÓN DEL ÍNDICE IPC", font=fuente(19, True), fill="#DDEBF5")
    valores = [float(v) for v in visible.values]
    minimo, maximo = min(valores), max(valores)
    margen = max((maximo - minimo) * 0.25, 0.25)
    y_min, y_max = minimo - margen, maximo + margen
    x_izq, x_der, y_sup, y_inf = 110, 1090, 535, 610
    puntos = []
    for i, valor in enumerate(valores):
        x = (x_izq + x_der) // 2 if len(valores) == 1 else round(
            x_izq + (x_der - x_izq) * (i / (len(valores) - 1))
        )
        y = round(y_inf - (valor - y_min) / (y_max - y_min) * (y_inf - y_sup))
        puntos.append((x, y))
    if len(puntos) > 1:
        dibujo.line(puntos, fill="#55DFC7", width=5, joint="curve")
    for x, y in puntos:
        dibujo.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#55DFC7")
    # Con un solo mes, mostrar una única fecha centrada bajo el punto.
    if len(visible) == 1:
        dibujo.text(((x_izq + x_der) // 2, 620), visible.index[0].strftime("%m-%Y"),
                     font=fuente(16), fill="#C0D2E3", anchor="mt")
    else:
        dibujo.text((110, 620), visible.index[0].strftime("%m-%Y"),
                     font=fuente(16), fill="#C0D2E3")
        dibujo.text((1090, 620), visible.index[-1].strftime("%m-%Y"),
                     font=fuente(16), fill="#C0D2E3", anchor="ra")

    dibujo.text((68, 683),
                 f"Desde {visible.index[0].strftime('%m-%Y')} hasta {visible.index[-1].strftime('%m-%Y')}  |  Base 2023 = 100",
                 font=fuente(19), fill="#D5E3EF")
    # Distribuir el texto en líneas completas, sin recortar palabras.
    dibujo.text((68, 714),
                 "Variación entre el primer y último índice mostrado; no equivale necesariamente",
                 font=fuente(15), fill="#A9BBD0")
    dibujo.text((68, 738), "a la inflación acumulada del trimestre o año.",
                 font=fuente(15), fill="#A9BBD0")
    dibujo.text((68, 766),
                 "Fuente: Banco Central de Chile  |  Análisis descriptivo, no es una proyección.",
                 font=fuente(15), fill="#A9BBD0")

    salida = BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return salida.getvalue()

def mostrar_ipc_historico():
    """Presenta la evolución mensual del IPC oficial sin modificar los reajustes."""
    st.subheader("📊 Evolución histórica del IPC")
    st.caption("Índice mensual del IPC de Chile. Se muestran únicamente los meses publicados.")

    hoy = date.today()
    opcion = st.selectbox(
        "Período de análisis",
        ["Últimos 3 meses", "Últimos 6 meses", "Últimos 12 meses", "Últimos 24 meses",
         "Trimestre calendario", "Semestre calendario", "Año calendario"],
        index=2,
        key="historico_ipc_periodo",
    )
    anio = None
    segmento_ipc = None
    if opcion in ("Trimestre calendario", "Semestre calendario", "Año calendario"):
        anio = st.selectbox(
            "Año", list(range(hoy.year, 2022, -1)),
            key="historico_ipc_anio",
        )
        if opcion == "Trimestre calendario":
            segmento_ipc = st.selectbox(
                "Trimestre", ["T1 (ene-mar)", "T2 (abr-jun)",
                              "T3 (jul-sep)", "T4 (oct-dic)"],
                index=(hoy.month - 1) // 3 if anio == hoy.year else 0,
                key="historico_ipc_trimestre",
            )
        elif opcion == "Semestre calendario":
            segmento_ipc = st.selectbox(
                "Semestre", ["S1 (ene-jun)", "S2 (jul-dic)"],
                index=(hoy.month - 1) // 6 if anio == hoy.year else 0,
                key="historico_ipc_semestre",
            )

    try:
        # Consultamos desde 2023 para calcular correctamente las variaciones
        # mensuales y a doce meses, incluso al comienzo del período visible.
        datos = consultar_ipc(date(2023, 1, 1), hoy)
        serie_completa = datos["INDICE"].dropna().sort_index().astype(float)
        if serie_completa.empty:
            st.warning("No se encontraron registros de IPC publicados.")
            return

        # Un índice por mes; no se rellenan meses sin publicación.
        serie_completa = serie_completa.groupby(
            serie_completa.index.to_period("M")
        ).last()
        variacion_mensual = serie_completa.pct_change(fill_method=None) * 100
        variacion_anual = serie_completa.pct_change(periods=12, fill_method=None) * 100
        ultimo_mes = serie_completa.index[-1]

        if opcion in ("Trimestre calendario", "Semestre calendario", "Año calendario"):
            # Los períodos calendario utilizan meses fijos del año elegido.
            if opcion == "Trimestre calendario":
                mes_inicio = (int(segmento_ipc[1]) - 1) * 3 + 1
                mes_fin = mes_inicio + 2
            elif opcion == "Semestre calendario":
                mes_inicio = 1 if segmento_ipc.startswith("S1") else 7
                mes_fin = mes_inicio + 5
            else:
                mes_inicio, mes_fin = 1, 12
            visible = serie_completa[
                (serie_completa.index.year == anio)
                & (serie_completa.index.month >= mes_inicio)
                & (serie_completa.index.month <= mes_fin)
            ]
            if pd.Period(f"{anio}-{mes_inicio:02d}", freq="M") > ultimo_mes:
                st.info("El período seleccionado todavía no tiene índices publicados.")
                return
        else:
            # Ventanas móviles de meses publicados, contadas desde el último IPC disponible.
            meses = {
                "Últimos 3 meses": 3,
                "Últimos 6 meses": 6,
                "Últimos 12 meses": 12,
                "Últimos 24 meses": 24,
            }[opcion]
            visible = serie_completa.iloc[-meses:]

        if visible.empty:
            st.warning("No existen índices publicados para el período seleccionado.")
            return

        def numero(valor, decimales=2):
            return f"{valor:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")

        # OPCIONES DEL GRÁFICO IPC: independientes de las opciones de monedas.
        col_valores, col_extremos = st.columns(2)
        with col_valores:
            mostrar_valores_ipc = st.toggle(
                "Mostrar valores sobre los puntos", value=False,
                key="ipc_mostrar_valores",
            )
        with col_extremos:
            destacar_extremos_ipc = st.toggle(
                "Destacar máximo y mínimo", value=True,
                key="ipc_destacar_extremos",
            )
        mostrar_media_ipc = st.toggle(
            "Mostrar media móvil (3 meses)", value=False,
            key="ipc_media_movil",
            help="Promedio de los últimos tres índices publicados; no es una proyección.",
        )

        fechas = visible.index.to_timestamp()
        etiquetas_ipc = [numero(float(v)) for v in visible.values]
        # El detalle del mouse usa variaciones calculadas con toda la serie.
        detalles_ipc = [
            f"Índice: {numero(float(valor))}<br>Variación mensual: "
            + (f"{float(variacion_mensual.loc[mes]):+.2f}%".replace(".", ",")
               if pd.notna(variacion_mensual.loc[mes]) else "Sin datos")
            for mes, valor in visible.items()
        ]
        grafico = go.Figure()
        grafico.add_trace(go.Scatter(
            x=fechas, y=visible.values,
            mode="lines+markers+text" if mostrar_valores_ipc else "lines+markers",
            name="Índice IPC", line=dict(color="#56B4E9", width=3),
            marker=dict(size=7),
            text=[("" if destacar_extremos_ipc and mes in (visible.idxmax(), visible.idxmin()) else etiqueta) for mes, etiqueta in zip(visible.index, etiquetas_ipc)] if mostrar_valores_ipc else None,
            textposition="top center",
            textfont=dict(size=15, color="#DDEBF5"),
            customdata=detalles_ipc,
            hovertemplate="Mes: %{x|%m-%Y}<br>%{customdata}<extra></extra>",
        ))

        if destacar_extremos_ipc and len(visible) > 1:
            # Con un solo registro no se dibujan máximo y mínimo superpuestos.
            # Para varios meses se mantiene el comportamiento anterior.
            for nombre, mes, color, posicion in [
                ("Máximo", visible.idxmax(), "#36D6B5", "bottom center"),
                ("Mínimo", visible.idxmin(), "#FFB454", "top center"),
            ]:
                valor = float(visible.loc[mes])
                grafico.add_trace(go.Scatter(
                    x=[mes.to_timestamp()], y=[valor],
                    mode="markers+text", name=nombre,
                    marker=dict(size=12, color=color,
                                line=dict(width=2, color="#101828")),
                    text=[f"{nombre}: {numero(valor)}"],
                    textposition=posicion,
                    textfont=dict(size=14, color=color),
                    hovertemplate=(f"{nombre} · {mes.strftime('%m-%Y')}"
                                   f"<br>Índice: {numero(valor)}<extra></extra>"),
                    showlegend=False,
                ))

        if mostrar_media_ipc:
            # La media se calcula solo con meses consecutivos publicados.
            # El gráfico presenta los valores dentro del período seleccionado.
            media_ipc = serie_completa.rolling(window=3, min_periods=3).mean()
            media_visible = media_ipc.reindex(visible.index)
            grafico.add_trace(go.Scatter(
                x=fechas, y=media_visible.values, mode="lines",
                name="Media móvil (3 meses)",
                line=dict(color="#FFB454", width=2, dash="dash"),
                hovertemplate="Mes: %{x|%m-%Y}<br>Media móvil: %{y:.2f}<extra></extra>",
            ))

        grafico.update_layout(
            title="Evolución mensual del índice IPC",
            template="plotly_dark", height=500 if mostrar_valores_ipc else 440,
            xaxis_title="Mes", yaxis_title="Índice IPC (base 2023 = 100)",
            margin=dict(l=20, r=20, t=65, b=35),
            # Etiquetas mensuales explícitas para evitar marcas semanales en 3 meses.
            xaxis=dict(
                tickmode="array",
                tickvals=list(fechas),
                ticktext=[mes.strftime("%m-%Y") for mes in visible.index],
                tickfont=dict(size=13),
                automargin=True,
            ),
            yaxis=dict(tickfont=dict(size=13)),
            hovermode="closest",
            showlegend=mostrar_media_ipc,
        )
        st.plotly_chart(grafico, use_container_width=True)
        if mostrar_media_ipc:
            st.caption(
                "La media móvil de 3 meses suaviza la evolución del índice IPC. "
                "No es una predicción de inflación futura."
            )

        st.subheader("📋 Resumen del IPC")
        ultimo = float(serie_completa.iloc[-1])
        mes_var = variacion_mensual.loc[ultimo_mes]
        anual_var = variacion_anual.loc[ultimo_mes]
        acumulada = float("nan")
        enero_anterior = pd.Period(f"{ultimo_mes.year - 1}-12", freq="M")
        if enero_anterior in serie_completa.index:
            base = float(serie_completa.loc[enero_anterior])
            if base:
                acumulada = (ultimo / base - 1) * 100

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Último índice publicado", numero(ultimo))
        c2.metric("Variación mensual", f"{mes_var:+.2f}%" if pd.notna(mes_var) else "Sin datos")
        c3.metric("Acumulado del año", f"{acumulada:+.2f}%" if pd.notna(acumulada) else "Sin datos")
        c4.metric("Variación a 12 meses", f"{anual_var:+.2f}%" if pd.notna(anual_var) else "Sin datos")

        # Variación exclusiva del rango visible: no altera los indicadores oficiales.
        # Se compara el primer índice mostrado con el último del mismo período.
        indice_inicial_periodo = float(visible.iloc[0])
        indice_final_periodo = float(visible.iloc[-1])
        variacion_periodo = (
            (indice_final_periodo / indice_inicial_periodo - 1) * 100
            if len(visible) >= 2 and indice_inicial_periodo != 0
            else None
        )
        st.metric(
            "Variación del período seleccionado",
            f"{variacion_periodo:+.2f}%" if variacion_periodo is not None else "Sin datos",
        )
        st.caption(
            f"Calculada entre {visible.index[0].strftime('%m-%Y')} y "
            f"{visible.index[-1].strftime('%m-%Y')}, según los índices mostrados "
            "en el gráfico. No equivale necesariamente a la inflación acumulada del año."
        )
        st.caption(
            f"Último IPC publicado: {ultimo_mes.month:02d}-{ultimo_mes.year}. "
            f"Meses mostrados: {len(visible)}. Fuente: Banco Central de Chile. "
            "Las variaciones corresponden al último mes publicado, no necesariamente al último mes del gráfico."
        )
        st.caption("Análisis histórico descriptivo; no representa una proyección.")


        # TABLA HISTÓRICA DEL IPC: utiliza el mismo período visible del gráfico.
        # Las variaciones se calculan con la serie completa para conservar
        # la comparación con meses anteriores al período seleccionado.
        st.subheader("📋 Tabla histórica mensual del IPC")
        tabla_ipc = pd.DataFrame({
            "Mes": [mes.strftime("%m-%Y") for mes in visible.index],
            "Índice IPC": [numero(float(valor)) for valor in visible.values],
            "Variación mensual": [
                f"{float(variacion_mensual.loc[mes]):+.2f}%".replace(".", ",")
                if pd.notna(variacion_mensual.loc[mes]) else "Sin datos"
                for mes in visible.index
            ],
            "Variación a 12 meses": [
                f"{float(variacion_anual.loc[mes]):+.2f}%".replace(".", ",")
                if pd.notna(variacion_anual.loc[mes]) else "Sin datos"
                for mes in visible.index
            ],
        })
        st.dataframe(tabla_ipc, hide_index=True, use_container_width=True)
        st.caption(
            "La tabla corresponde a los meses mostrados en el gráfico. "
            "Las variaciones se calculan respecto del mes anterior y del mismo "
            "mes del año anterior, cuando existen registros disponibles."
        )

        # DESCARGA EXCEL IPC: conserva el período elegido en pantalla.
        # Las variaciones mensuales y anuales se obtienen de la serie completa.
        if opcion == "Trimestre calendario":
            nombre_periodo_ipc = f"{segmento_ipc.split(' ')[0]} de {anio}"
        elif opcion == "Semestre calendario":
            nombre_periodo_ipc = f"{segmento_ipc.split(' ')[0]} de {anio}"
        elif opcion == "Año calendario":
            nombre_periodo_ipc = f"Año calendario {anio}"
        else:
            nombre_periodo_ipc = opcion
        archivo_excel_ipc = crear_informe_excel_ipc(
            visible, variacion_mensual, variacion_anual, nombre_periodo_ipc
        )
        st.download_button(
            label="📥 Descargar informe Excel del IPC",
            data=archivo_excel_ipc,
            file_name=(
                f"Informe_IPC_{visible.index[0].strftime('%Y%m')}_"
                f"{visible.index[-1].strftime('%Y%m')}.xlsx"
            ),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="descargar_excel_ipc_historico",
        )

        # TARJETA PNG IPC: utiliza exactamente el período visible del gráfico.
        archivo_png_ipc = crear_tarjeta_png_ipc(visible, nombre_periodo_ipc)
        st.download_button(
            label="🖼️ Descargar tarjeta PNG del IPC",
            data=archivo_png_ipc,
            file_name=(
                f"Tarjeta_IPC_{visible.index[0].strftime('%Y%m')}_"
                f"{visible.index[-1].strftime('%Y%m')}.png"
            ),
            mime="image/png",
            key="descargar_png_ipc_historico",
        )
    except Exception as error:
        st.error(f"No fue posible cargar el IPC histórico: {error}")




def crear_informe_excel_cobre(serie, nombre_periodo, fecha_inicio, fecha_fin, periodo_incompleto):
    """Crea el informe Excel del cobre con resumen, gráfico y cotizaciones editables."""
    libro = Workbook()
    resumen = libro.active
    resumen.title = "Resumen económico"
    grafico = libro.create_sheet("Gráfico histórico")
    datos = libro.create_sheet("Datos históricos")

    azul, claro = "17324D", "EAF3F7"
    formato_precio = '#,##0.0000 "USD/lb"'
    formato_variacion = '+0.00%;-0.00%;0.00%'
    formato_fecha = "DD-MM-YYYY"

    def titulo(hoja, texto, columnas=2):
        hoja.merge_cells(start_row=1, start_column=1, end_row=1, end_column=columnas)
        celda = hoja.cell(1, 1, texto)
        celda.font = Font(name="Aptos Display", size=16, bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=azul)
        celda.alignment = Alignment(vertical="center")
        hoja.row_dimensions[1].height = 34
        hoja.sheet_view.showGridLines = False

    inicial, final = float(serie.iloc[0]), float(serie.iloc[-1])
    variacion = final - inicial
    porcentaje = variacion / inicial if inicial else None
    tendencia = ("Alza" if porcentaje is not None and porcentaje > 0.001
                 else "Baja" if porcentaje is not None and porcentaje < -0.001
                 else "Relativamente estable")

    titulo(resumen, "INFORME HISTÓRICO DEL COBRE")
    resumen.column_dimensions["A"].width = 35
    resumen.column_dimensions["B"].width = 48
    contenido = [
        (3, "Indicador", "Precio de referencia del cobre"),
        (4, "Unidad", "USD por libra (USD/lb)"),
        (5, "Período seleccionado", nombre_periodo),
        (6, "Fecha inicial consultada", fecha_inicio),
        (7, "Fecha final consultada", fecha_fin),
        (8, "Primer registro publicado", serie.index[0].to_pydatetime()),
        (9, "Último registro publicado", serie.index[-1].to_pydatetime()),
        (10, "Cantidad de registros", len(serie)),
        (12, "Precio inicial", inicial),
        (13, "Precio final", final),
        (14, "Precio mínimo", float(serie.min())),
        (15, "Fecha del mínimo", serie.idxmin().to_pydatetime()),
        (16, "Precio máximo", float(serie.max())),
        (17, "Fecha del máximo", serie.idxmax().to_pydatetime()),
        (18, "Precio promedio", float(serie.mean())),
        (19, "Variación absoluta", variacion),
        (20, "Variación porcentual", porcentaje),
        (21, "Tendencia observada", tendencia),
        (23, "Estado del período", "Resultados parciales" if periodo_incompleto else "Período consultado"),
        (24, "Fuente", "Banco Central de Chile"),
        (25, "Fecha de elaboración", date.today()),
    ]
    filas_precio = {12, 13, 14, 16, 18, 19}
    filas_fecha = {6, 7, 8, 9, 15, 17, 25}
    for fila, etiqueta, valor in contenido:
        celda = resumen.cell(fila, 1, etiqueta)
        celda.font = Font(name="Aptos", bold=True, color=azul)
        celda.fill = PatternFill("solid", fgColor=claro)
        resultado = resumen.cell(fila, 2, valor)
        resultado.font = Font(name="Aptos", color=azul)
        if fila in filas_precio:
            resultado.number_format = formato_precio
        elif fila in filas_fecha:
            resultado.number_format = formato_fecha
        elif fila == 20:
            resultado.number_format = formato_variacion
    resumen.merge_cells("A27:B27")
    resumen["A27"] = "Variación entre el primer y último registro disponible; no es una proyección."
    resumen["A27"].font = Font(name="Aptos", italic=True, color="657587", size=10)
    resumen.freeze_panes = "B3"
    resumen.sheet_properties.pageSetUpPr.fitToPage = True
    resumen.page_setup.fitToWidth = 1

    titulo(datos, "COTIZACIONES HISTÓRICAS DEL COBRE", 4)
    for columna, ancho in {"A": 20, "B": 25, "C": 30, "D": 25}.items():
        datos.column_dimensions[columna].width = ancho
    encabezados = ["Fecha", "Precio (USD/lb)", "Variación (USD/lb)", "Variación (%)"]
    for columna, texto in enumerate(encabezados, 1):
        celda = datos.cell(3, columna, texto)
        celda.font = Font(name="Aptos", bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=azul)
        celda.alignment = Alignment(wrap_text=True, vertical="center")
    datos.row_dimensions[3].height = 30
    anterior = None
    for fila, (fecha, valor) in enumerate(serie.items(), 4):
        actual = float(valor)
        datos.cell(fila, 1, fecha.to_pydatetime()).number_format = formato_fecha
        datos.cell(fila, 2, actual).number_format = formato_precio
        if anterior is not None:
            datos.cell(fila, 3, actual - anterior).number_format = formato_precio
            if anterior:
                datos.cell(fila, 4, (actual / anterior) - 1).number_format = formato_variacion
        if fila % 2 == 0:
            for columna in range(1, 5):
                datos.cell(fila, columna).fill = PatternFill("solid", fgColor="F3F8FA")
        anterior = actual
    ultima_fila = len(serie) + 3
    datos.auto_filter.ref = f"A3:D{ultima_fila}"
    datos.freeze_panes = "A4"

    titulo(grafico, "EVOLUCIÓN HISTÓRICA DEL COBRE", 4)
    grafico.column_dimensions["A"].width = 23
    grafico.column_dimensions["B"].width = 48
    grafico["A3"], grafico["B3"] = "Período", nombre_periodo
    grafico["A4"], grafico["B4"] = "Unidad", "USD por libra"
    grafico["A5"], grafico["B5"] = "Fuente", "Banco Central de Chile"
    grafico["A6"], grafico["B6"] = "Nota", "Valores publicados; no representan proyecciones"
    # Gráfico como imagen: las etiquetas de ambos ejes permanecen visibles
    # en Excel Online y Excel de escritorio. Los datos numéricos siguen
    # editables en la hoja "Datos históricos".
    from math import floor, ceil

    ancho_img, alto_img = 1600, 760
    imagen = Image.new("RGB", (ancho_img, alto_img), "#FFFFFF")
    dibujo = ImageDraw.Draw(imagen)

    def fuente_grafico(tamano, negrita=False):
        rutas = (
            ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
            if negrita else
            ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        )
        for ruta in rutas:
            try:
                return ImageFont.truetype(ruta, tamano)
            except OSError:
                continue
        return ImageFont.load_default()

    ft_titulo = fuente_grafico(33, True)
    ft_texto = fuente_grafico(21)
    ft_eje = fuente_grafico(20)
    ft_pie = fuente_grafico(18)
    azul = "#17324D"
    gris = "#66788A"
    dibujo.text((115, 38), "PRECIO HISTÓRICO DEL COBRE", font=ft_titulo, fill=azul)
    dibujo.text((115, 92), f"{nombre_periodo}  |  USD por libra", font=ft_texto, fill=gris)

    valores = [float(v) for v in serie.values]
    fechas = list(serie.index)
    cantidad = len(valores)
    izq, der, sup, inf = 130, 1510, 165, 605
    minimo, maximo = min(valores), max(valores)
    margen = max((maximo - minimo) * 0.12, 0.08)
    y_min = floor((minimo - margen) * 4) / 4
    y_max = ceil((maximo + margen) * 4) / 4
    if y_min == y_max:
        y_max = y_min + 0.5

    # Seis marcas de precio, dibujadas como texto real dentro de la imagen.
    for i in range(6):
        valor_eje = y_min + (y_max - y_min) * i / 5
        y = round(inf - (valor_eje - y_min) / (y_max - y_min) * (inf - sup))
        dibujo.line([(izq, y), (der, y)], fill="#E3E9EF", width=2)
        etiqueta = f"{valor_eje:.2f}".replace(".", ",")
        dibujo.text((izq - 17, y), etiqueta, font=ft_eje, fill=gris, anchor="rm")

    # Conservar TODOS los registros y distribuirlos según sus fechas reales.
    # Así, los días sin publicación no alteran la escala temporal del gráfico.
    fecha_primera = pd.Timestamp(fechas[0])
    fecha_ultima = pd.Timestamp(fechas[-1])
    dias_totales = (fecha_ultima - fecha_primera).total_seconds() / 86400

    def coordenada_fecha(fecha):
        if dias_totales == 0:
            return round((izq + der) / 2)
        dias = (pd.Timestamp(fecha) - fecha_primera).total_seconds() / 86400
        return round(izq + (der - izq) * dias / dias_totales)

    puntos = []
    for fecha, valor in zip(fechas, valores):
        x = coordenada_fecha(fecha)
        y = round(inf - (valor - y_min) / (y_max - y_min) * (inf - sup))
        puntos.append((x, y))
    if len(puntos) > 1:
        dibujo.line(puntos, fill="#668C36", width=5, joint="curve")
    else:
        x, y = puntos[0]
        dibujo.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#668C36")

    # Eje X con meses calendario uniformes, no con fechas elegidas por
    # posición de registro. En períodos breves usamos marcas semanales/diarias.
    nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                     "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    if dias_totales >= 55:
        meses_periodo = pd.period_range(fecha_primera.to_period("M"),
                                        fecha_ultima.to_period("M"), freq="M")
        # Máximo siete etiquetas: 12 meses -> cada dos meses; 3 años -> cada seis.
        paso_meses = max(1, (len(meses_periodo) + 6) // 7)
        marcas = [mes.to_timestamp() for mes in meses_periodo[::paso_meses]
                  if fecha_primera <= mes.to_timestamp() <= fecha_ultima]
        for marca in marcas:
            x = coordenada_fecha(marca)
            dibujo.line([(x, inf), (x, inf + 8)], fill="#AAB7C3", width=2)
            etiqueta = f"{nombres_meses[marca.month - 1]} {marca.year}"
            dibujo.text((x, inf + 19), etiqueta, font=ft_eje, fill=gris,
                        anchor="mt")
    else:
        cantidad_fechas = min(cantidad, 7)
        posiciones = sorted(set(
            round(i * (cantidad - 1) / (cantidad_fechas - 1))
            for i in range(cantidad_fechas)
        )) if cantidad_fechas > 1 else [0]
        for posicion in posiciones:
            x, _ = puntos[posicion]
            dibujo.line([(x, inf), (x, inf + 8)], fill="#AAB7C3", width=2)
            dibujo.text((x, inf + 19), fechas[posicion].strftime("%d-%m-%Y"),
                        font=ft_eje, fill=gris, anchor="mt")

    dibujo.text(((izq + der) // 2, 682), "Fecha (registros publicados)",
                font=ft_texto, fill=azul, anchor="mm")
    dibujo.text((115, 725), "Fuente: Banco Central de Chile  |  Valores históricos publicados",
                font=ft_pie, fill=gris)

    imagen_bytes = BytesIO()
    imagen.save(imagen_bytes, format="PNG")
    imagen_bytes.seek(0)
    figura_excel = ExcelImage(imagen_bytes)
    figura_excel.width = 1120
    figura_excel.height = 532
    grafico.add_image(figura_excel, "A9")
    grafico["A44"] = "Gráfico de imagen para mantener visibles las fechas y los precios en Excel Online."
    grafico["A45"] = "Los precios originales permanecen editables en la hoja Datos históricos."

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def crear_tarjeta_png_cobre(serie, nombre_periodo, periodo_incompleto):
    """Genera una tarjeta PNG del cobre con un gráfico de tendencia del período."""
    imagen = Image.new("RGB", (1200, 850), "#0B1627")
    dibujo = ImageDraw.Draw(imagen)

    def fuente(tamano, negrita=False):
        rutas = (["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
                 if negrita else ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
        for ruta in rutas:
            try:
                return ImageFont.truetype(ruta, tamano)
            except OSError:
                pass
        return ImageFont.load_default()

    def numero(valor):
        return f"{valor:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def dato(x, y, etiqueta, valor, color="#F4F8FF"):
        dibujo.text((x, y), etiqueta, font=fuente(19), fill="#A9BBD0")
        dibujo.text((x, y + 30), valor, font=fuente(31, True), fill=color)

    inicial, final = float(serie.iloc[0]), float(serie.iloc[-1])
    variacion = (final / inicial - 1) * 100 if inicial else 0.0
    color = "#55DFC7" if variacion > 0 else "#FF9A90" if variacion < 0 else "#D9E6F5"
    tendencia = "Alza" if variacion > 0 else "Baja" if variacion < 0 else "Estable"

    dibujo.rounded_rectangle((24, 24, 1176, 826), radius=30, fill="#14273C", outline="#2D4760", width=2)
    dibujo.text((65, 56), "INTELIGENCIA ECONÓMICA  /  HERRAMIENTAS DE COMPRAS", font=fuente(18, True), fill="#55DFC7")
    dibujo.text((65, 100), "Resumen histórico del cobre", font=fuente(42, True), fill="#FFFFFF")
    periodo = nombre_periodo + ("  ·  Resultados parciales" if periodo_incompleto else "")
    # Evita cortar nombres de períodos largos en la tarjeta.
    tamano_periodo = 20 if len(periodo) > 65 else 23
    dibujo.text((67, 161), periodo, font=fuente(tamano_periodo), fill="#B8CADD")
    dibujo.line((65, 209, 1135, 209), fill="#38536C", width=2)

    dato(68, 231, "PRECIO INICIAL", f"{numero(inicial)} USD/lb")
    dato(645, 231, "PRECIO FINAL", f"{numero(final)} USD/lb")
    dato(68, 320, "PRECIO MÍNIMO", f"{numero(float(serie.min()))} USD/lb")
    dato(645, 320, "PRECIO MÁXIMO", f"{numero(float(serie.max()))} USD/lb")
    dato(68, 409, "PRECIO PROMEDIO", f"{numero(float(serie.mean()))} USD/lb")
    dato(645, 409, "VARIACIÓN DEL PERÍODO", f"{variacion:+.2f}%".replace(".", ","), color)

    # Gráfico de línea compacto, calculado con los registros efectivamente publicados.
    izquierda, arriba, derecha, abajo = 92, 545, 1100, 696
    dibujo.rounded_rectangle((65, 512, 1135, 726), radius=16, fill="#203C53")
    dibujo.text((91, 521), f"EVOLUCIÓN DEL PRECIO  ·  {tendencia}", font=fuente(17, True), fill=color)
    valores = [float(v) for v in serie.values]
    minimo, maximo = min(valores), max(valores)
    amplitud = max(maximo - minimo, 0.0001)
    puntos = [
        (izquierda + i * (derecha - izquierda) / max(len(valores) - 1, 1),
         abajo - (v - minimo) / amplitud * (abajo - arriba))
        for i, v in enumerate(valores)
    ]
    for fraccion in (0, 0.5, 1):
        y = arriba + (abajo - arriba) * fraccion
        dibujo.line((izquierda, y, derecha, y), fill="#35546B", width=1)
    if len(puntos) > 1:
        dibujo.line(puntos, fill="#76D4AD", width=4, joint="curve")
    else:
        x, y = puntos[0]
        dibujo.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#76D4AD")
    dibujo.text((92, 698), f"{serie.index[0]:%d-%m-%Y}", font=fuente(15), fill="#B8CADD")
    texto_fin = f"{serie.index[-1]:%d-%m-%Y}"
    caja_fin = dibujo.textbbox((0, 0), texto_fin, font=fuente(15))
    dibujo.text((1100 - (caja_fin[2] - caja_fin[0]), 698), texto_fin, font=fuente(15), fill="#B8CADD")

    dibujo.text((68, 751), f"{len(serie)} registros publicados  |  Unidad: USD por libra", font=fuente(18), fill="#D5E3EF")
    dibujo.text((68, 785), "Fuente: Banco Central de Chile · Datos históricos, no son proyecciones.", font=fuente(16), fill="#9EB3C9")
    salida = BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return salida.getvalue()


def mostrar_cobre_historico():
    """Primera etapa: consulta y gráfico del cobre en USD por libra."""
    st.subheader("📈 Evolución histórica del precio del cobre")
    st.caption(
        "Precio de referencia del cobre publicado por el Banco Central de Chile, "
        "expresado en USD por libra. No corresponde al precio contractual de venta "
        "de una empresa minera ni a una cotización mayorista de combustible."
    )

    hoy = date.today()
    tipo = st.radio(
        "Tipo de período", ["Período móvil", "Período calendario", "Período personalizado"],
        horizontal=True, key="cobre_tipo_periodo"
    )
    if tipo == "Período móvil":
        opcion = st.selectbox(
            "Período de análisis",
            ["7 días", "30 días", "90 días", "6 meses", "1 año", "3 años"],
            index=1, key="cobre_periodo_movil"
        )
        dias = {"7 días": 7, "30 días": 30, "90 días": 90,
                "6 meses": 183, "1 año": 365, "3 años": 1095}[opcion]
        inicio, fin = hoy - timedelta(days=dias), hoy
        nombre_periodo_cobre = f"Últimos {opcion.lower()}"
        periodo_incompleto_cobre = False
    elif tipo == "Período calendario":
        # Períodos fijos: el año, semestre o trimestre se eligen por separado.
        agrupacion = st.selectbox(
            "Agrupación calendario", ["Trimestre", "Semestre", "Año"],
            key="cobre_agrupacion_calendario"
        )
        col_anio, col_segmento = st.columns(2)
        with col_anio:
            anio = st.selectbox(
                "Año", list(range(hoy.year, 1999, -1)),
                key="cobre_anio_calendario"
            )
        with col_segmento:
            if agrupacion == "Trimestre":
                segmento = st.selectbox(
                    "Trimestre", ["T1 (ene-mar)", "T2 (abr-jun)",
                                  "T3 (jul-sep)", "T4 (oct-dic)"],
                    index=(hoy.month - 1) // 3 if anio == hoy.year else 0,
                    key="cobre_trimestre_calendario"
                )
                mes_inicio = (int(segmento[1]) - 1) * 3 + 1
                mes_fin = mes_inicio + 2
                nombre_periodo_cobre = f"{segmento.split(' ')[0]} de {anio}"
            elif agrupacion == "Semestre":
                segmento = st.selectbox(
                    "Semestre", ["S1 (ene-jun)", "S2 (jul-dic)"],
                    index=(hoy.month - 1) // 6 if anio == hoy.year else 0,
                    key="cobre_semestre_calendario"
                )
                mes_inicio = 1 if segmento.startswith("S1") else 7
                mes_fin = mes_inicio + 5
                nombre_periodo_cobre = f"{segmento.split(' ')[0]} de {anio}"
            else:
                st.caption("Se analizará el año calendario completo, o hasta hoy si está en curso.")
                mes_inicio, mes_fin = 1, 12
                nombre_periodo_cobre = f"Año calendario {anio}"
        inicio = date(anio, mes_inicio, 1)
        fin_programado = date(anio, mes_fin, monthrange(anio, mes_fin)[1])
        fin = min(fin_programado, hoy)
        periodo_incompleto_cobre = fin_programado > hoy
    else:
        col1, col2 = st.columns(2)
        with col1:
            inicio = st.date_input(
                "Fecha inicial", value=hoy - timedelta(days=30),
                key="cobre_fecha_inicio"
            )
        with col2:
            fin = st.date_input("Fecha final", value=hoy, key="cobre_fecha_fin")
        nombre_periodo_cobre = f"Del {inicio:%d-%m-%Y} al {fin:%d-%m-%Y}"
        periodo_incompleto_cobre = False

    if inicio > fin:
        st.warning("La fecha inicial no puede ser posterior a la fecha final.")
        return
    if inicio > hoy:
        st.info("El período seleccionado todavía no comienza.")
        return

    st.caption(f"**Período seleccionado:** {nombre_periodo_cobre}")
    if periodo_incompleto_cobre:
        st.warning(
            "**Período calendario en curso.** Los resultados son parciales y "
            f"se consultan hasta el {fin:%d-%m-%Y}. No representan el cierre definitivo."
        )

    try:
        datos = consultar_cobre(inicio, min(fin, hoy))
        if "COBRE_USD_LIBRA" not in datos.columns:
            st.error("La consulta no devolvió la columna COBRE_USD_LIBRA esperada.")
            return
        serie = pd.to_numeric(datos["COBRE_USD_LIBRA"], errors="coerce").dropna()
        serie.index = pd.to_datetime(serie.index)
        serie = serie.sort_index()
        if serie.empty:
            st.warning("No existen precios publicados para el período seleccionado.")
            return

        def numero(valor, decimales=4):
            return (f"{float(valor):,.{decimales}f}"
                    .replace(",", "X").replace(".", ",").replace("X", "."))

        # Controles independientes para las etiquetas y los extremos del cobre.
        col_etiquetas, col_extremos = st.columns(2)
        with col_etiquetas:
            mostrar_valores = st.toggle(
                "Mostrar precios sobre los puntos", value=False,
                key="cobre_mostrar_valores",
                help="Las fechas aparecen en el eje inferior. En períodos extensos se muestran "
                     "menos precios para evitar superposiciones; el mouse muestra todos."
            )
        with col_extremos:
            destacar_extremos = st.toggle(
                "Destacar máximo y mínimo", value=True,
                key="cobre_destacar_extremos"
            )

        fecha_maximo = serie.idxmax()
        fecha_minimo = serie.idxmin()
        valor_maximo = float(serie.max())
        valor_minimo = float(serie.min())

        # Sobre los puntos se muestran SOLO precios; las fechas van en el eje inferior.
        # En rangos densos se alternan las etiquetas para evitar solapamientos.
        cantidad_registros = len(serie)
        paso_etiquetas = (1 if cantidad_registros <= 14 else
                          2 if cantidad_registros <= 30 else
                          max(3, (cantidad_registros + 19) // 20))
        etiquetas = [
            numero(valor) if (i % paso_etiquetas == 0 or i == cantidad_registros - 1)
            and not (destacar_extremos and fecha in (fecha_maximo, fecha_minimo)) else ""
            for i, (fecha, valor) in enumerate(serie.items())
        ]
        # Marcas del eje X: fechas calendario, no posiciones arbitrarias de puntos.
        dias_grafico = (serie.index[-1] - serie.index[0]).days
        meses_abrev = ["ene", "feb", "mar", "abr", "may", "jun",
                       "jul", "ago", "sep", "oct", "nov", "dic"]
        if dias_grafico <= 10:
            frecuencia_eje = "2D"
        elif dias_grafico <= 45:
            frecuencia_eje = "7D"
        elif dias_grafico <= 100:
            frecuencia_eje = "14D"
        elif dias_grafico <= 220:
            frecuencia_eje = "MS"
        elif dias_grafico <= 450:
            frecuencia_eje = "2MS"
        else:
            frecuencia_eje = "6MS"
        fechas_eje = list(pd.date_range(serie.index[0], serie.index[-1], freq=frecuencia_eje))
        if not fechas_eje or fechas_eje[0] != serie.index[0]:
            fechas_eje.insert(0, serie.index[0])
        if fechas_eje[-1] != serie.index[-1]:
            fechas_eje.append(serie.index[-1])
        textos_eje = [
            f"{fecha.day} {meses_abrev[fecha.month - 1]}"
            if dias_grafico <= 100 else f"{meses_abrev[fecha.month - 1]} {fecha.year}"
            for fecha in fechas_eje
        ]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=serie.index, y=serie.values,
            mode="lines+markers+text" if mostrar_valores else "lines+markers",
            line=dict(color="#56B4E9", width=3), marker=dict(size=6),
            text=etiquetas if mostrar_valores else None,
            textposition="top center", textfont=dict(size=11, color="#DDEBF5"),
            name="Cobre (USD/libra)",
            customdata=[numero(v) for v in serie.values],
            hovertemplate="Fecha: %{x|%d-%m-%Y}<br>USD/libra: %{customdata}<extra></extra>"
        ))

        if destacar_extremos:
            # Si máximo y mínimo coinciden, evitar marcadores duplicados.
            extremos = [
                ("Máximo", fecha_maximo, valor_maximo, "#36D6B5", "top center"),
                ("Mínimo", fecha_minimo, valor_minimo, "#FFB454", "bottom center"),
            ]
            if fecha_maximo == fecha_minimo:
                extremos = extremos[:1]
            for nombre, fecha, valor, color, posicion in extremos:
                fig.add_trace(go.Scatter(
                    x=[fecha], y=[valor], mode="markers+text",
                    marker=dict(size=13, color=color, line=dict(width=2, color="#101828")),
                    text=[f"{nombre}: {numero(valor)}"],
                    textposition=posicion, textfont=dict(size=12, color=color),
                    name=nombre, showlegend=False,
                    hovertemplate=(f"{nombre} · {fecha:%d-%m-%Y}<br>"
                                   f"Precio: {numero(valor)} USD/lb<extra></extra>")
                ))

        # Margen vertical para que las etiquetas de extremos no queden cortadas.
        margen = max((valor_maximo - valor_minimo) * 0.18, valor_maximo * 0.025)
        fig.update_layout(
            title="Precio histórico del cobre", template="plotly_dark",
            height=540 if mostrar_valores else 470,
            xaxis_title="Fecha", yaxis_title="USD por libra",
            xaxis=dict(tickmode="array", tickvals=fechas_eje,
                       ticktext=textos_eje, tickfont=dict(size=12),
                       automargin=True),
            yaxis=dict(range=[valor_minimo - margen, valor_maximo + margen]),
            margin=dict(l=20, r=20, t=60, b=35), showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        if mostrar_valores and len(serie) > 14:
            st.caption(
                "Para mantener la legibilidad, se muestran precios alternados. "
                "Pasa el mouse sobre cualquier punto para consultar su precio y fecha exactos."
            )

        primero, ultimo = float(serie.iloc[0]), float(serie.iloc[-1])
        cambio = ((ultimo / primero) - 1) * 100 if primero else None
        st.subheader("📋 Resumen del cobre")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Último valor del período", f"{numero(ultimo)} USD/lb")
        c2.metric("Valor mínimo", f"{numero(valor_minimo)} USD/lb")
        c3.metric("Valor máximo", f"{numero(valor_maximo)} USD/lb")
        st.caption(
            f"**Fecha del mínimo:** {fecha_minimo:%d-%m-%Y}  |  "
            f"**Fecha del máximo:** {fecha_maximo:%d-%m-%Y}"
        )
        c4.metric("Valor promedio", f"{numero(serie.mean())} USD/lb")
        st.metric(
            "Variación del período",
            f"{cambio:+.2f}%" if cambio is not None else "Sin datos"
        )
        # TABLA HISTÓRICA DEL COBRE: utiliza los mismos registros del gráfico.
        # La variación se calcula respecto del registro publicado anterior
        # dentro del período seleccionado, sin inventar datos en días sin cotización.
        st.subheader("📋 Tabla histórica de precios del cobre")
        variacion_absoluta = serie.diff()
        variacion_porcentual = serie.pct_change(fill_method=None) * 100
        tabla_cobre = pd.DataFrame({
            "Fecha": [fecha.strftime("%d-%m-%Y") for fecha in serie.index],
            "Precio (USD/lb)": [numero(valor) for valor in serie.values],
            "Variación (USD/lb)": [
                f"{numero(valor) if valor < 0 else '+' + numero(valor)}"
                if pd.notna(valor) else "Sin registro anterior"
                for valor in variacion_absoluta.values
            ],
            "Variación (%)": [
                f"{valor:+.2f}%".replace(".", ",")
                if pd.notna(valor) else "Sin registro anterior"
                for valor in variacion_porcentual.values
            ],
        })
        st.dataframe(tabla_cobre, hide_index=True, use_container_width=True)
        st.caption(
            "La tabla muestra los mismos registros publicados que el gráfico. "
            "Las variaciones comparan cada precio con el registro anterior "
            "dentro del período seleccionado; el primero no tiene comparación. "
            "Los días sin cotización publicada no se completan artificialmente."
        )

        st.caption(
            f"Registros publicados: {len(serie)}. "
            f"Primer registro: {serie.index[0]:%d-%m-%Y}. "
            f"Último registro: {serie.index[-1]:%d-%m-%Y}. "
            "Fuente: Banco Central de Chile. Análisis descriptivo, no es una proyección."
        )
        # EXPORTACIÓN DEL COBRE: utiliza los mismos registros y fechas del gráfico.
        st.subheader("📥 Exportar análisis del cobre")
        try:
            archivo_excel_cobre = crear_informe_excel_cobre(
                serie, nombre_periodo_cobre, inicio, fin, periodo_incompleto_cobre
            )
            st.download_button(
                "📊 Descargar informe Excel del cobre",
                data=archivo_excel_cobre,
                file_name=(
                    f"Informe_Historico_Cobre_{inicio:%Y%m%d}_{fin:%Y%m%d}.xlsx"
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="cobre_descargar_excel",
                use_container_width=True,
            )
        except Exception as error_excel:
            st.warning(f"No fue posible preparar el informe Excel del cobre: {error_excel}")

        # TARJETA PNG DEL COBRE: conserva el mismo período y los mismos datos.
        try:
            tarjeta_png_cobre = crear_tarjeta_png_cobre(
                serie, nombre_periodo_cobre, periodo_incompleto_cobre
            )
            st.download_button(
                "🖼️ Descargar tarjeta PNG del cobre",
                data=tarjeta_png_cobre,
                file_name=f"Tarjeta_Historica_Cobre_{inicio:%Y%m%d}_{fin:%Y%m%d}.png",
                mime="image/png",
                key="cobre_descargar_png",
                use_container_width=True,
            )
        except Exception as error_png:
            st.warning(f"No fue posible preparar la tarjeta PNG del cobre: {error_png}")

    except Exception as error:
        st.error(f"No fue posible cargar el precio histórico del cobre: {error}")


def mostrar_analisis_historico():
    # Selector principal: conserva intacto el análisis de monedas existente.
    categoria = st.radio(
        "Indicador a analizar",
        ["Monedas (USD, EUR, UF)", "IPC histórico", "Precio del cobre"],
        horizontal=True,
        key="historico_categoria",
    )
    if categoria == "IPC histórico":
        mostrar_ipc_historico()
        return

    if categoria == "Precio del cobre":
        mostrar_cobre_historico()
        return

    # ÁREA DE ANÁLISIS HISTÓRICO
    st.subheader("📈 Evolución de las monedas")

    # Selección entre ventanas móviles y períodos contables cerrados.
    tipo_periodo = st.radio(
        "Tipo de período",
        ["Período móvil", "Período calendario", "Personalizado"],
        horizontal=True,
        key="historico_tipo_periodo"
    )
    hoy = date.today()
    col_moneda, col_periodo = st.columns(2)
    with col_moneda:
        moneda = st.selectbox(
            "Selecciona la moneda", ["USD", "EUR", "UF"], key="historico_moneda"
        )

    with col_periodo:
        if tipo_periodo == "Período móvil":
            periodo = st.selectbox(
                "Período de análisis",
                ["7 días", "30 días", "90 días", "6 meses", "1 año", "3 años", "5 años"],
                index=1, key="historico_periodo_movil"
            )
        elif tipo_periodo == "Período calendario":
            periodo = st.selectbox(
                "Agrupación calendario", ["Trimestre", "Semestre", "Año"],
                key="historico_agrupacion_calendario"
            )
        else:
            periodo = "Personalizado"

    if tipo_periodo == "Período móvil":
        dias_periodo = {
            "7 días": 7, "30 días": 30, "90 días": 90,
            "6 meses": 183, "1 año": 365, "3 años": 1095, "5 años": 1826
        }
        fecha_fin = hoy
        fecha_inicio = hoy - timedelta(days=dias_periodo[periodo])

    elif tipo_periodo == "Período calendario":
        col_anio, col_segmento = st.columns(2)
        with col_anio:
            anio = st.selectbox(
                "Año", list(range(hoy.year, 1999, -1)),
                key="historico_anio_calendario"
            )
        with col_segmento:
            if periodo == "Trimestre":
                segmento = st.selectbox(
                    "Trimestre", ["T1 (ene-mar)", "T2 (abr-jun)",
                                  "T3 (jul-sep)", "T4 (oct-dic)"],
                    index=(hoy.month - 1) // 3 if anio == hoy.year else 0,
                    key="historico_trimestre"
                )
                mes_inicio = (int(segmento[1]) - 1) * 3 + 1
                mes_fin = mes_inicio + 2
            elif periodo == "Semestre":
                segmento = st.selectbox(
                    "Semestre", ["S1 (ene-jun)", "S2 (jul-dic)"],
                    index=(hoy.month - 1) // 6 if anio == hoy.year else 0,
                    key="historico_semestre"
                )
                mes_inicio = 1 if segmento.startswith("S1") else 7
                mes_fin = mes_inicio + 5
            else:
                st.caption("Se analizará el año calendario completo, o hasta hoy si está en curso.")
                mes_inicio, mes_fin = 1, 12
        fecha_inicio = date(anio, mes_inicio, 1)
        fecha_fin = min(date(anio, mes_fin, monthrange(anio, mes_fin)[1]), hoy)
        if fecha_inicio > hoy:
            st.info("Este período todavía no comienza. Selecciona uno anterior.")
            return

    else:
        col_inicio, col_fin = st.columns(2)
        with col_inicio:
            fecha_inicio = st.date_input(
                "Fecha inicial", value=hoy - timedelta(days=30),
                key="fecha_inicio_historico"
            )
        with col_fin:
            fecha_fin = st.date_input(
                "Fecha final", value=hoy, key="fecha_fin_historico"
            )

    # Nombre descriptivo para identificar claramente el alcance del análisis.
    if tipo_periodo == "Período calendario":
        if periodo == "Trimestre":
            numero = (mes_inicio - 1) // 3 + 1
            nombres = ["Primer", "Segundo", "Tercer", "Cuarto"]
            nombre_periodo = f"{nombres[numero - 1]} trimestre de {anio}"
        elif periodo == "Semestre":
            nombre_periodo = f"{'Primer' if mes_inicio == 1 else 'Segundo'} semestre de {anio}"
        else:
            nombre_periodo = f"Año calendario {anio}"
        fin_programado = date(anio, mes_fin, monthrange(anio, mes_fin)[1])
        periodo_incompleto = fin_programado > hoy
    elif tipo_periodo == "Período móvil":
        nombre_periodo = f"Últimos {periodo.lower()}"
        periodo_incompleto = False
    else:
        nombre_periodo = f"Período personalizado: {fecha_inicio:%d-%m-%Y} al {fecha_fin:%d-%m-%Y}"
        periodo_incompleto = False

    if fecha_inicio > fecha_fin:
        st.warning("La fecha inicial no puede ser posterior a la fecha final.")
        return

    try:
        datos_historicos = consultar_monedas(
            fecha_inicio,
            fecha_fin
        )

        serie = datos_historicos[moneda].dropna().sort_index()

        st.caption(f"**Período seleccionado:** {nombre_periodo} · Registros disponibles para {moneda}: {len(serie)}")
        if periodo_incompleto:
            st.warning(
                "**Período calendario en curso.** Los resultados son parciales: "
                f"se consultan datos hasta el {fecha_fin:%d-%m-%Y}. "
                "No representan el cierre definitivo del período."
            )

        if serie.empty:
            st.warning(
                "No existen registros disponibles "
                "para el período seleccionado."
            )

        else:
            # OPCIONES DE VISUALIZACIÓN DEL GRÁFICO
            col_etiquetas, col_extremos = st.columns(2)
            with col_etiquetas:
                mostrar_valores = st.toggle(
                    "Mostrar valores sobre los puntos",
                    value=False,
                    key="historico_mostrar_valores",
                    help="Recomendado para períodos cortos. En períodos largos puede saturar el gráfico."
                )
            with col_extremos:
                destacar_extremos = st.toggle(
                    "Destacar máximo y mínimo",
                    value=True,
                    key="historico_destacar_extremos"
                )

            # La media móvil se calcula con registros publicados, no días sin cotización.
            mostrar_media = st.toggle(
                "Mostrar media móvil (5 registros)", value=False,
                key="historico_media_movil",
                help=("Calcula el promedio de las últimas cinco cotizaciones publicadas "
                      "(incluyendo la actual). No son necesariamente cinco días calendario. "
                      "Suaviza las fluctuaciones y no predice precios.")
            )

            # Evitamos el símbolo $ en Markdown: Streamlit puede interpretarlo como fórmula.
            with st.expander("¿Qué significa la media móvil de 5 registros?"):
                st.markdown(
                    "La **media móvil de 5 registros** es el promedio de las últimas "
                    "cinco cotizaciones disponibles. Se recalcula cuando se publica "
                    "una nueva cotización."
                )
                st.markdown(
                    "**Ejemplo:** si los valores son 900, 910, 920, 930 y 940 CLP, "
                    "el promedio es **920 CLP**. Cuando aparece una nueva cotización "
                    "de 950 CLP, se elimina el registro más antiguo (900 CLP) y "
                    "el nuevo promedio es **930 CLP**."
                )
                st.markdown(
                    "La línea suavizada permite observar la tendencia, **no es una "
                    "proyección**. Los fines de semana y feriados sin publicación "
                    "no se cuentan como registros."
                )

            # Formato de números chileno para las etiquetas del gráfico.
            def etiqueta_clp(valor):
                return (f"{float(valor):,.2f}"
                        .replace(",", "X").replace(".", ",").replace("X", "."))

            fig = go.Figure()
            cambios = serie.diff()
            detalles_hover = [
                f"{etiqueta_clp(float(v))} CLP | Cambio: "
                + (f"{etiqueta_clp(float(c))} CLP" if c == c else "sin registro previo")
                for v, c in zip(serie.values, cambios.values)
            ]
            etiquetas = [etiqueta_clp(valor) for valor in serie.values]
            fig.add_trace(
                go.Scatter(
                    x=serie.index,
                    y=serie.values,
                    mode="lines+markers+text" if mostrar_valores else "lines+markers",
                    name=moneda,
                    line=dict(color="#56B4E9", width=3),
                    marker=dict(size=5),
                    text=etiquetas if mostrar_valores else None,
                    textposition="top center",
                    textfont=dict(size=12, color="#DDEBF5"),
                    customdata=detalles_hover,
                    hovertemplate=(
                        "Fecha: %{x|%d-%m-%Y}"
                        "<br>%{customdata}"
                        "<extra></extra>"
                    )
                )
            )

            if mostrar_media and len(serie) >= 5:
                media = serie.rolling(window=5, min_periods=5).mean()
                fig.add_trace(go.Scatter(
                    x=media.index, y=media.values, mode="lines",
                    name="Media móvil (5 registros)",
                    line=dict(color="#FFB454", width=2, dash="dash"),
                    hovertemplate="Media móvil: %{y:,.2f} CLP<extra></extra>"
                ))
            elif mostrar_media:
                st.info("La media móvil requiere al menos 5 registros disponibles.")

            valor_minimo = float(serie.min())
            valor_maximo = float(serie.max())
            margen = max(
                (valor_maximo - valor_minimo) * (0.30 if mostrar_valores else 0.15),
                valor_maximo * 0.002
            )

            if destacar_extremos:
                # Se señala la primera fecha en caso de máximos/mínimos repetidos.
                for titulo, indice, color, posicion in [
                    ("Máximo", serie.idxmax(), "#36D6B5", "bottom center"),
                    ("Mínimo", serie.idxmin(), "#FFB454", "top center"),
                ]:
                    valor = float(serie.loc[indice])
                    fig.add_trace(go.Scatter(
                        x=[indice], y=[valor],
                        mode="markers+text",
                        marker=dict(size=12, color=color, line=dict(width=2, color="#101828")),
                        text=[titulo] if not mostrar_valores else [""],
                        textposition=posicion,
                        textfont=dict(color=color, size=11),
                        name=titulo,
                        customdata=[etiqueta_clp(valor)],
                        hovertemplate=(
                            titulo + ": %{x|%d-%m-%Y}"
                            "<br>$%{customdata} CLP<extra></extra>"
                        )
                    ))

            # Fechas legibles en el eje horizontal, sin superponerlas a los valores.
            # Los intervalos se ajustan a la cantidad de días consultados.
            dias_consultados = (fecha_fin - fecha_inicio).days
            if dias_consultados <= 7:
                max_fechas_eje = 8
            elif dias_consultados <= 30:
                max_fechas_eje = 10
            elif dias_consultados <= 90:
                max_fechas_eje = 9
            elif dias_consultados <= 183:
                max_fechas_eje = 7
            else:
                max_fechas_eje = 8

            # Distribuimos las fechas según los registros realmente disponibles.
            cantidad = len(serie)
            posiciones = sorted(set(
                round(i * (cantidad - 1) / (min(cantidad, max_fechas_eje) - 1))
                for i in range(min(cantidad, max_fechas_eje))
            )) if cantidad > 1 else [0]
            fechas_eje = [serie.index[i] for i in posiciones]
            textos_eje = [fecha.strftime("%d/%m") for fecha in fechas_eje]

            # Eje Y con etiquetas explícitas en formato chileno (punto para miles,
            # coma para decimales). Plotly no respeta siempre la configuración regional.
            limite_inferior = valor_minimo - margen
            limite_superior = valor_maximo + margen
            cantidad_marcas_y = 6
            marcas_y = [
                limite_inferior + i * (limite_superior - limite_inferior)
                / (cantidad_marcas_y - 1)
                for i in range(cantidad_marcas_y)
            ]

            fig.update_layout(
                title=f"Evolución histórica de {moneda}",
                template="plotly_dark",
                height=480 if mostrar_valores else 430,
                margin=dict(l=20, r=20, t=55, b=30),
                xaxis_title="Fecha",
                xaxis=dict(
                    tickmode="array",
                    tickvals=fechas_eje,
                    ticktext=textos_eje,
                    tickfont=dict(size=12, color="#DDEBF5"),
                    automargin=True
                ),
                yaxis_title="Pesos chilenos (CLP)",
                yaxis=dict(
                    range=[limite_inferior, limite_superior],
                    tickmode="array",
                    tickvals=marcas_y,
                    ticktext=[etiqueta_clp(valor) for valor in marcas_y]
                ),
                hovermode="x unified",
                showlegend=mostrar_media and len(serie) >= 5
            )

            st.plotly_chart(fig, width="stretch")
            if mostrar_valores and len(serie) > 30:
                st.caption(
                    "Hay más de 30 registros: las etiquetas pueden superponerse. "
                    "Desactiva 'Mostrar valores' para una lectura más clara."
                )

            st.caption(
                "Nota: el eje vertical utiliza una escala "
                "ajustada para visualizar las fluctuaciones."
            )

            st.caption(
                f"Fuente: Banco Central de Chile. "
                f"Período consultado: "
                f"{fecha_inicio:%d-%m-%Y} al "
                f"{fecha_fin:%d-%m-%Y}."
            )

            st.subheader("📋 Resumen económico")
            st.caption(f"**{nombre_periodo}**" + (" · Resultados parciales" if periodo_incompleto else ""))

            valor_inicial = float(serie.iloc[0])
            valor_final = float(serie.iloc[-1])

            variacion_clp = valor_final - valor_inicial

            variacion_pct = (
                variacion_clp / valor_inicial * 100
                if valor_inicial != 0 else 0
            )

            def formato_clp(valor):
                return (
                    f"${valor:,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Valor máximo",
                formato_clp(serie.max())
            )

            col2.metric(
                "Valor mínimo",
                formato_clp(serie.min())
            )

            col3.metric(
                "Valor promedio",
                formato_clp(serie.mean())
            )

            col4.metric(
                "Variación del período",
                f"{variacion_pct:+.2f}%",
                delta=(
                    f"{variacion_clp:+,.2f} CLP"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
            )

            if variacion_pct > 0.1:
                tendencia = "Alza"
            elif variacion_pct < -0.1:
                tendencia = "Baja"
            else:
                tendencia = "Relativamente estable"
            # Presentación sobria, sin un bloque de alerta azul.
            st.markdown(
                f"**Tendencia observada: {tendencia}.** "
                f"El {moneda} pasó de {formato_clp(valor_inicial)} a "
                f"{formato_clp(valor_final)} CLP "
                f"({variacion_pct:+.2f}%)."
            )
            st.caption(
                "Variación entre el primer y último registro disponible; "
                "no representa una proyección."
                + (" El período calendario aún no ha finalizado." if periodo_incompleto else "")
            )

            st.caption(
                f"Primer registro: "
                f"{serie.index[0]:%d-%m-%Y} | "
                f"Último registro: "
                f"{serie.index[-1]:%d-%m-%Y}"
            )

            # EXPORTACIÓN A EXCEL: reutiliza exactamente la serie del gráfico.
            st.subheader("📥 Exportar análisis")
            try:
                archivo_excel = crear_informe_excel_historico(
                    serie, moneda, nombre_periodo, fecha_inicio,
                    fecha_fin, periodo_incompleto
                )
                st.download_button(
                    "📊 Descargar informe Excel",
                    data=archivo_excel,
                    file_name=(
                        f"Informe_Historico_{moneda}_"
                        f"{fecha_inicio:%Y%m%d}_{fecha_fin:%Y%m%d}.xlsx"
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="historico_descargar_excel",
                    use_container_width=True,
                )
            except Exception as error_excel:
                st.warning(f"No fue posible preparar el informe Excel: {error_excel}")

            # TARJETA PNG: comparte el mismo período, moneda y serie del informe.
            try:
                tarjeta_png = crear_tarjeta_png_historico(
                    serie, moneda, nombre_periodo, periodo_incompleto
                )
                st.download_button(
                    "🖼️ Descargar tarjeta PNG",
                    data=tarjeta_png,
                    file_name=(
                        f"Tarjeta_Historica_{moneda}_"
                        f"{fecha_inicio:%Y%m%d}_{fecha_fin:%Y%m%d}.png"
                    ),
                    mime="image/png",
                    key="historico_descargar_png",
                    use_container_width=True,
                )
            except Exception as error_png:
                st.warning(f"No fue posible preparar la tarjeta PNG: {error_png}")

    except Exception as error:
        st.error(
            "No fue posible cargar el análisis histórico: "
            f"{error}"
        )
