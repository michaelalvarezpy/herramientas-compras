import streamlit as st
from io import BytesIO
from datetime import date
from Inteligencia_Economica.Servicios.banco_central import consultar_ipc
from Inteligencia_Economica.Modulos.formatos import formato_pesos



def crear_excel_reajuste(modalidad, monto, monto_final, porcentaje,
                         diferencia, periodo_inicial=None, periodo_final=None,
                         indice_inicial=None, indice_final=None):
    """Genera un Excel de dos hojas con openpyxl, sin alterar el cálculo de Streamlit."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.workbook.properties import CalcProperties

    oficial = modalidad == "IPC oficial"
    libro = Workbook()
    resumen = libro.active
    resumen.title = "Resumen del reajuste"
    detalle = libro.create_sheet("Detalle del cálculo")
    libro.calculation = CalcProperties(calcMode="auto", fullCalcOnLoad=True)

    azul = "19334D"
    turquesa = "276078"
    claro = "E8F1F6"
    moneda = '#,##0.00 "CLP"'
    porcentaje_excel = '+0.0000%;-0.0000%;0.0000%'

    def preparar_hoja(hoja, titulo, ancho_b=47):
        hoja.merge_cells("A1:B1")
        celda = hoja["A1"]
        celda.value = titulo
        celda.font = Font(name="Aptos", size=15, bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=azul)
        celda.alignment = Alignment(vertical="center")
        hoja.row_dimensions[1].height = 34
        hoja.column_dimensions["A"].width = 33
        hoja.column_dimensions["B"].width = ancho_b
        hoja.sheet_view.showGridLines = False
        hoja.freeze_panes = "B4"

    def agregar_filas(hoja, fila_inicial, filas):
        for numero, (etiqueta, valor) in enumerate(filas, start=fila_inicial):
            c1, c2 = hoja.cell(numero, 1, etiqueta), hoja.cell(numero, 2, valor)
            c1.fill = PatternFill("solid", fgColor=claro)
            c1.font = Font(name="Aptos", bold=True, color=azul, size=10)
            c2.font = Font(name="Aptos", color="24364B", size=10)
            c1.alignment = Alignment(vertical="center")
            c2.alignment = Alignment(vertical="center", wrap_text=True)
            hoja.row_dimensions[numero].height = 24

    preparar_hoja(resumen, "INFORME DE REAJUSTE ECONÓMICO")
    filas_resumen = [
        ("Modalidad", modalidad),
        ("Moneda", "CLP"),
        ("Período inicial", periodo_inicial if oficial else "No aplica"),
        ("Período final", periodo_final if oficial else "No aplica"),
        ("Índice IPC inicial", float(indice_inicial) if oficial else "No aplica"),
        ("Índice IPC final", float(indice_final) if oficial else "No aplica"),
        ("Monto original (CLP)", float(monto)),
        ("Variación aplicada (%)", float(porcentaje) / 100),
        ("Monto reajustado (CLP)", float(monto_final)),
        ("Diferencia económica (CLP)", float(diferencia)),
        ("Fuente", "Banco Central de Chile" if oficial else "Porcentaje ingresado por el usuario"),
        ("Fecha de elaboración", date.today()),
    ]
    agregar_filas(resumen, 3, filas_resumen)
    for celda in ("B7", "B8"):
        if oficial:
            resumen[celda].number_format = "0.0000"
    for celda in ("B9", "B11", "B12"):
        resumen[celda].number_format = moneda
    resumen["B10"].number_format = porcentaje_excel
    resumen["B14"].number_format = "DD-MM-YYYY"
    resumen.merge_cells("A16:B16")
    resumen["A16"] = "Informe referencial; revisar las condiciones contractuales aplicables."
    resumen["A16"].font = Font(name="Aptos", italic=True, color="64748B", size=10)

    preparar_hoja(detalle, "DETALLE Y TRAZABILIDAD DEL CÁLCULO", 65)
    for celda, valor in (("A3", "Concepto"), ("B3", "Valor / explicación")):
        detalle[celda] = valor
        detalle[celda].fill = PatternFill("solid", fgColor=turquesa)
        detalle[celda].font = Font(name="Aptos", bold=True, color="FFFFFF")
    detalle.row_dimensions[3].height = 26

    if oficial:
        filas_detalle = [
            ("Período inicial", periodo_inicial),
            ("Período final", periodo_final),
            ("Índice IPC inicial", float(indice_inicial)),
            ("Índice IPC final", float(indice_final)),
            ("Variación IPC", "=IFERROR(B7/B6-1,0)"),
            ("Monto original (CLP)", float(monto)),
            ("Monto reajustado (CLP)", "=IFERROR(B9*B7/B6,0)"),
            ("Diferencia (CLP)", "=B10-B9"),
            ("Método", "Índice final / índice inicial; se usan valores completos"),
            ("Fuente", "Banco Central de Chile"),
        ]
        agregar_filas(detalle, 4, filas_detalle)
        for celda in ("B6", "B7"):
            detalle[celda].number_format = "0.0000"
        detalle["B8"].number_format = porcentaje_excel
        for celda in ("B9", "B10", "B11"):
            detalle[celda].number_format = moneda
    else:
        filas_detalle = [
            ("Tipo de cálculo", "Simulación manual; no equivale al IPC oficial"),
            ("Monto original (CLP)", float(monto)),
            ("Porcentaje ingresado", float(porcentaje) / 100),
            ("Monto reajustado (CLP)", "=B5*(1+B6)"),
            ("Diferencia (CLP)", "=B7-B5"),
            ("Método", "Monto original × (1 + porcentaje / 100)"),
            ("Fuente", "Porcentaje ingresado por el usuario"),
        ]
        agregar_filas(detalle, 4, filas_detalle)
        detalle["B5"].number_format = moneda
        detalle["B6"].number_format = porcentaje_excel
        for celda in ("B7", "B8"):
            detalle[celda].number_format = moneda

    # Exportación en memoria: no se crean archivos temporales en el equipo.
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()



def crear_excel_simulaciones_multiples(modalidad, escenarios):
    """Genera un informe de escenarios con importes numéricos y fórmulas auditables."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.workbook.properties import CalcProperties

    libro = Workbook()
    resumen = libro.active
    resumen.title = "Resumen de simulación"
    detalle = libro.create_sheet("Detalle de escenarios")
    libro.calculation = CalcProperties(calcMode="auto", fullCalcOnLoad=True)

    azul, turquesa, claro = "19334D", "276078", "E8F1F6"
    moneda = '#,##0.00 "CLP"'
    porcentaje_excel = '+0.00%;-0.00%;0.00%'
    con_totales = modalidad != "Un monto y varios porcentajes"
    primera_fila = 5
    ultima_fila = primera_fila + len(escenarios) - 1
    fila_total = ultima_fila + 1

    for hoja, titulo in ((resumen, "INFORME DE SIMULACIÓN ECONÓMICA"),
                          (detalle, "DETALLE Y TRAZABILIDAD DE ESCENARIOS")):
        hoja.sheet_view.showGridLines = False
        hoja.merge_cells("A1:E1")
        encabezado = hoja["A1"]
        encabezado.value = titulo
        encabezado.font = Font(name="Aptos", size=15, bold=True, color="FFFFFF")
        encabezado.fill = PatternFill("solid", fgColor=azul)
        encabezado.alignment = Alignment(vertical="center")
        hoja.row_dimensions[1].height = 35
        for columna, ancho in {"A": 24, "B": 26, "C": 20, "D": 28, "E": 28}.items():
            hoja.column_dimensions[columna].width = ancho
        hoja.freeze_panes = "B5"
        hoja.print_options.horizontalCentered = True
        hoja.sheet_properties.pageSetUpPr.fitToPage = True
        hoja.page_setup.fitToWidth = 1
        hoja.sheet_view.zoomScale = 90

    resumen["A2"] = "Tipo de simulación"
    resumen["B2"] = modalidad
    resumen["A3"] = "Fecha de elaboración"
    resumen["B3"] = date.today()
    resumen["B3"].number_format = "DD-MM-YYYY"
    for fila in (2, 3):
        resumen.cell(fila, 1).font = Font(name="Aptos", bold=True, color=azul)
        resumen.cell(fila, 1).fill = PatternFill("solid", fgColor=claro)
        resumen.cell(fila, 2).font = Font(name="Aptos", color=azul)
    resumen.merge_cells("B2:E2")

    encabezados = ["Escenario", "Monto original (CLP)", "Reajuste (%)",
                   "Monto reajustado (CLP)", "Diferencia (CLP)"]
    for hoja in (resumen, detalle):
        for columna, texto in enumerate(encabezados, 1):
            celda = hoja.cell(4, columna, texto)
            celda.fill = PatternFill("solid", fgColor=turquesa)
            celda.font = Font(name="Aptos", bold=True, color="FFFFFF")
            celda.alignment = Alignment(vertical="center", wrap_text=True)
        hoja.row_dimensions[4].height = 30

    for indice, (nombre, monto, porcentaje) in enumerate(escenarios, start=primera_fila):
        # En el detalle se guardan valores numéricos y fórmulas editables.
        detalle.cell(indice, 1, nombre)
        detalle.cell(indice, 2, float(monto))
        detalle.cell(indice, 3, float(porcentaje) / 100)
        detalle.cell(indice, 4, f"=B{indice}*(1+C{indice})")
        detalle.cell(indice, 5, f"=D{indice}-B{indice}")
        # El resumen referencia el detalle, evitando cifras duplicadas.
        for columna in range(1, 6):
            letra = get_column_letter(columna)
            resumen.cell(indice, columna, f"='Detalle de escenarios'!{letra}{indice}")

    if con_totales:
        for hoja in (resumen, detalle):
            hoja.cell(fila_total, 1, "TOTAL")
            for columna in (2, 4, 5):
                letra = get_column_letter(columna)
                hoja.cell(fila_total, columna,
                           f"=SUM({letra}{primera_fila}:{letra}{ultima_fila})")
            hoja.cell(fila_total, 3, "—")
            for celda in hoja[fila_total][:5]:
                celda.fill = PatternFill("solid", fgColor=claro)
                celda.font = Font(name="Aptos", bold=True, color=azul)

    for hoja in (resumen, detalle):
        for fila in range(primera_fila, fila_total + int(con_totales)):
            for columna in (2, 4, 5):
                hoja.cell(fila, columna).number_format = moneda
            if fila <= ultima_fila:
                hoja.cell(fila, 3).number_format = porcentaje_excel
            for celda in hoja[fila][:5]:
                celda.alignment = Alignment(vertical="center")
                if fila <= ultima_fila:
                    celda.font = Font(name="Aptos", color="24364B", size=10)
                    if (fila - primera_fila) % 2:
                        celda.fill = PatternFill("solid", fgColor="F2F7FA")
            hoja.row_dimensions[fila].height = 24
        nota_fila = fila_total + int(con_totales) + 2
        hoja.merge_cells(start_row=nota_fila, start_column=1,
                          end_row=nota_fila, end_column=5)
        nota = hoja.cell(nota_fila, 1)
        nota.value = (
            "Escenarios alternativos: se aplica cada porcentaje al mismo monto; no corresponde sumar resultados."
            if not con_totales else
            "Los totales suman montos distintos; cada porcentaje se aplica al monto de su propia fila."
        )
        nota.font = Font(name="Aptos", italic=True, color="64748B", size=10)
        hoja.row_dimensions[nota_fila].height = 28
        hoja.merge_cells(start_row=nota_fila + 1, start_column=1,
                          end_row=nota_fila + 1, end_column=5)
        aviso = hoja.cell(nota_fila + 1, 1)
        aviso.value = "Simulación referencial; los porcentajes ingresados no son proyecciones oficiales del IPC."
        aviso.font = Font(name="Aptos", italic=True, color="64748B", size=10)
        hoja.print_area = f"A1:E{nota_fila + 1}"

    detalle["A2"] = "Método: monto original × (1 + reajuste / 100)."
    detalle.merge_cells("A2:E2")
    detalle["A3"] = "Los importes y porcentajes son editables; las columnas D y E contienen fórmulas."
    detalle.merge_cells("A3:E3")
    for fila in (2, 3):
        detalle.cell(fila, 1).font = Font(name="Aptos", italic=True, color="64748B")

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()




def crear_tarjeta_simulacion(modalidad, escenarios):
    """Tarjeta PNG legible en Windows y Linux, sin depender de fuentes por defecto."""
    from PIL import Image, ImageDraw, ImageFont
    from pathlib import Path

    # Resolución compacta: evita grandes espacios entre columnas.
    ancho = 1420
    margen = 32
    fila_alto = 78
    hay_total = modalidad != "Un monto y varios porcentajes"
    filas = len(escenarios) + int(hay_total)
    tabla_y = 208
    cabecera_alto = 67
    tabla_fin = tabla_y + cabecera_alto + filas * fila_alto
    alto = tabla_fin + 124

    imagen = Image.new("RGB", (ancho, alto), (11, 21, 37))
    dibujo = ImageDraw.Draw(imagen)

    def fuente(tamano, negrita=False):
        # En Windows Pillow no siempre encuentra 'DejaVuSans.ttf' por nombre.
        # La fuente básica de Pillow es diminuta: nunca usarla para esta tarjeta.
        nombres = (["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"] if negrita
                   else ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"])
        carpetas = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"),
                    Path("/usr/share/fonts/truetype/msttcorefonts"), Path("/usr/share/fonts/truetype/liberation2")]
        for carpeta in carpetas:
            for nombre in nombres:
                ruta = carpeta / nombre
                if ruta.is_file():
                    return ImageFont.truetype(str(ruta), tamano)
        for nombre in nombres:
            try:
                return ImageFont.truetype(nombre, tamano)
            except OSError:
                pass
        raise RuntimeError("No se encontró una fuente TrueType para generar la tarjeta PNG.")

    titulo = fuente(44, True)
    subtitulo = fuente(27)
    cabecera = fuente(22, True)
    normal = fuente(27)
    destacado = fuente(28, True)
    nota = fuente(21)

    def clp(valor):
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def pct(valor):
        return f"{valor:+.2f}%".replace(".", ",")

    # Columnas proporcionales a la longitud de los importes.
    columnas = [55, 247, 538, 717, 1055]
    limites = [233, 524, 701, 1041, ancho - 52]

    def texto_ajustado(texto, x, y, x_limite, fuente_base, color, negrita=False):
        tam = fuente_base.size
        actual = fuente_base
        while dibujo.textbbox((0, 0), texto, font=actual)[2] > x_limite - x and tam > 20:
            tam -= 1
            actual = fuente(tam, negrita)
        dibujo.text((x, y), texto, font=actual, fill=color, anchor="lm")

    dibujo.rounded_rectangle((12, 12, ancho - 12, alto - 12), radius=26, fill=(20, 35, 55))
    dibujo.rounded_rectangle((margen, 29, ancho - margen, 40), radius=5, fill=(45, 201, 185))
    dibujo.text((margen + 16, 61), "SIMULACIÓN DE REAJUSTES", font=titulo, fill="white")
    dibujo.text((margen + 16, 145), modalidad, font=subtitulo, fill=(191, 213, 229))
    dibujo.text((ancho - margen - 16, 151), date.today().strftime("%d-%m-%Y"),
                font=subtitulo, fill=(191, 213, 229), anchor="ra")

    dibujo.rounded_rectangle((margen, tabla_y, ancho - margen, tabla_y + cabecera_alto),
                              radius=9, fill=(37, 97, 119))
    nombres = ["ESCENARIO", "MONTO ORIGINAL", "REAJUSTE", "MONTO REAJUSTADO", "DIFERENCIA"]
    for x, limite, nombre in zip(columnas, limites, nombres):
        texto_ajustado(nombre, x, tabla_y + cabecera_alto / 2, limite, cabecera, "white", True)

    for i, (nombre, monto, porcentaje) in enumerate(escenarios):
        y = tabla_y + cabecera_alto + i * fila_alto
        dibujo.rounded_rectangle((margen, y + 3, ancho - margen, y + fila_alto - 3),
                                  radius=7, fill=(29, 49, 71) if i % 2 == 0 else (24, 43, 63))
        monto_final = monto * (1 + porcentaje / 100)
        diferencia = monto_final - monto
        valores = [nombre, "$" + clp(monto), pct(porcentaje),
                   "$" + clp(monto_final), "$" + clp(diferencia)]
        for j, (x, limite, valor) in enumerate(zip(columnas, limites, valores)):
            color = ((89, 225, 192) if j == 3 else
                     (255, 180, 153) if j == 4 and diferencia < 0 else (232, 240, 247))
            negrita = j == 3
            texto_ajustado(valor, x, y + fila_alto / 2, limite,
                           destacado if negrita else normal, color, negrita)

    if hay_total:
        y = tabla_y + cabecera_alto + len(escenarios) * fila_alto
        total = sum(monto for _, monto, _ in escenarios)
        total_final = sum(monto * (1 + porcentaje / 100) for _, monto, porcentaje in escenarios)
        dibujo.rounded_rectangle((margen, y + 3, ancho - margen, y + fila_alto - 3),
                                  radius=7, fill=(40, 81, 103))
        valores = ["TOTAL", "$" + clp(total), "—", "$" + clp(total_final),
                   "$" + clp(total_final - total)]
        for x, limite, valor in zip(columnas, limites, valores):
            texto_ajustado(valor, x, y + fila_alto / 2, limite, destacado, "white", True)

    aviso = ("Escenarios alternativos: los resultados no se suman." if not hay_total
             else "Cada reajuste se aplica al monto original de su fila.")
    dibujo.text((margen + 16, tabla_fin + 31), aviso, font=nota, fill=(191, 213, 229))
    dibujo.text((margen + 16, tabla_fin + 69),
                 "Simulación referencial; no representa una proyección oficial del IPC.",
                 font=nota, fill=(191, 213, 229))

    salida = BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return salida.getvalue()

def crear_tarjeta_ipc_oficial(monto, monto_final, porcentaje, diferencia,
                              periodo_inicial, periodo_final, indice_inicial, indice_final):
    """Crea una tarjeta PNG compacta del reajuste IPC oficial, con índices y fuente."""
    from PIL import Image, ImageDraw, ImageFont
    from pathlib import Path

    ancho, alto = 1180, 620
    imagen = Image.new("RGB", (ancho, alto), (11, 21, 37))
    dibujo = ImageDraw.Draw(imagen)

    # Buscar fuentes TrueType reales: evita texto diminuto en Windows.
    def fuente(tamano, negrita=False):
        nombres = (["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"] if negrita
                   else ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"])
        carpetas = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"),
                    Path("/usr/share/fonts/truetype/msttcorefonts"),
                    Path("/usr/share/fonts/truetype/liberation2")]
        for carpeta in carpetas:
            for nombre in nombres:
                ruta = carpeta / nombre
                if ruta.is_file():
                    return ImageFont.truetype(str(ruta), tamano)
        for nombre in nombres:
            try:
                return ImageFont.truetype(nombre, tamano)
            except OSError:
                continue
        raise RuntimeError("No se encontró una fuente TrueType para generar la tarjeta IPC.")

    titulo = fuente(39, True)
    etiqueta = fuente(21)
    valor = fuente(31, True)
    pequeno = fuente(19)
    color_texto = (234, 242, 249)
    color_suave = (182, 204, 220)
    turquesa = (77, 221, 192)

    def pesos(numero):
        return "$" + f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def porcentaje_es(numero):
        return f"{numero:+.4f}%".replace(".", ",")

    def indice_es(numero):
        return f"{numero:.4f}".replace(".", ",")

    def escribir_ajustado(texto, x, y, limite, tamano=31, negrita=True, color=color_texto):
        actual = fuente(tamano, negrita)
        while dibujo.textbbox((0, 0), texto, font=actual)[2] > limite - x and tamano > 18:
            tamano -= 1
            actual = fuente(tamano, negrita)
        dibujo.text((x, y), texto, font=actual, fill=color)

    dibujo.rounded_rectangle((10, 10, ancho - 10, alto - 10), radius=24, fill=(20, 35, 55))
    dibujo.rounded_rectangle((28, 26, ancho - 28, 37), radius=5, fill=(45, 201, 185))
    dibujo.text((43, 55), "REAJUSTE SEGÚN IPC OFICIAL", font=titulo, fill="white")
    dibujo.text((45, 116), "Banco Central de Chile", font=etiqueta, fill=color_suave)
    dibujo.text((ancho - 44, 119), date.today().strftime("%d-%m-%Y"),
                font=etiqueta, fill=color_suave, anchor="ra")

    # Dos períodos e índices, con columnas proporcionadas y sin espacio sobrante.
    for x, periodo, indice, encabezado in (
        (42, periodo_inicial, indice_inicial, "PERÍODO INICIAL"),
        (601, periodo_final, indice_final, "PERÍODO FINAL"),
    ):
        dibujo.rounded_rectangle((x - 8, 170, x + 533, 283), radius=12, fill=(29, 49, 71))
        dibujo.text((x + 11, 183), encabezado, font=pequeno, fill=color_suave)
        escribir_ajustado(periodo, x + 11, 210, x + 515, 28)
        dibujo.text((x + 11, 251), "Índice IPC: " + indice_es(indice),
                    font=pequeno, fill=turquesa)

    # Tres indicadores principales; cada cifra ocupa una columna legible.
    tarjetas = [
        (42, "MONTO ORIGINAL", pesos(monto), color_texto),
        (422, "MONTO REAJUSTADO", pesos(monto_final), turquesa),
        (802, "DIFERENCIA", pesos(diferencia), (255, 180, 153) if diferencia < 0 else color_texto),
    ]
    for x, encabezado, cifra, color in tarjetas:
        dibujo.rounded_rectangle((x - 8, 307, x + 353, 413), radius=11, fill=(29, 49, 71))
        dibujo.text((x + 7, 322), encabezado, font=pequeno, fill=color_suave)
        escribir_ajustado(cifra, x + 7, 357, x + 340, 30, True, color)

    dibujo.rounded_rectangle((34, 435, ancho - 34, 523), radius=12, fill=(37, 97, 119))
    dibujo.text((54, 451), "VARIACIÓN DEL IPC ENTRE LOS PERÍODOS", font=pequeno, fill="white")
    escribir_ajustado(porcentaje_es(porcentaje), 54, 478, ancho - 65, 33, True, "white")

    dibujo.text((44, 543), "Cálculo: monto original × (IPC final / IPC inicial).",
                font=pequeno, fill=color_suave)
    dibujo.text((44, 575), "Informe referencial; revisar las condiciones contractuales aplicables.",
                font=pequeno, fill=color_suave)

    salida = BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return salida.getvalue()


def campo_monto_clp(etiqueta, clave):
    """Entrada CLP con puntos de miles y coma decimal, sin alterar los cálculos."""
    import re

    def formatear(valor):
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def normalizar():
        texto = str(st.session_state[clave]).strip().replace(" ", "")
        # Formato chileno: 1.234.567,89. También admite 1234567,89.
        if not re.fullmatch(r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{0,2})?", texto):
            st.session_state[clave + "_error"] = "Ingresa un monto válido, por ejemplo 1.500.000,00."
            return
        monto = float(texto.replace(".", "").replace(",", "."))
        st.session_state[clave] = formatear(monto)
        st.session_state[clave + "_error"] = ""

    if clave not in st.session_state:
        st.session_state[clave] = "0,00"
    st.text_input(etiqueta, key=clave, on_change=normalizar,
                  help="Formato chileno: puntos para miles y coma para decimales.")
    texto = str(st.session_state[clave]).strip().replace(" ", "")
    valido = bool(re.fullmatch(r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{0,2})?", texto))
    if not valido:
        st.error("Ingresa un monto válido, por ejemplo 1.500.000,00.")
        st.stop()
    return float(texto.replace(".", "").replace(",", "."))



def campo_porcentaje_manual(etiqueta, clave):
    """Porcentaje opcional al inicio: vacío hasta que el usuario lo ingrese."""
    import re

    # Conservar el valor durante las actualizaciones de Streamlit.
    # Si existía un valor numérico de una versión anterior, convertirlo a texto.
    if clave in st.session_state and not isinstance(st.session_state[clave], str):
        st.session_state[clave] = str(st.session_state[clave]).replace(".", ",")

    texto = st.text_input(
        etiqueta,
        value="",
        key=clave,
        placeholder="Ej.: 4,00",
        help="Ingresa un porcentaje entre -100 y 1000. Se admite coma decimal.",
    ).strip()

    # None significa que todavía no se ha ingresado un porcentaje.
    if not texto:
        return None

    # Se aceptan tanto 4,5 como 4.5, pero no separadores de miles.
    if not re.fullmatch(r"[+-]?(?:\d+(?:[.,]\d{1,4})?|[.,]\d{1,4})", texto):
        st.error(f"{etiqueta}: ingresa un porcentaje válido, por ejemplo 4,50.")
        return None

    porcentaje = float(texto.replace(",", "."))
    if not -100.0 <= porcentaje <= 1000.0:
        st.error(f"{etiqueta}: el porcentaje debe estar entre -100 y 1000.")
        return None

    return porcentaje


def mostrar_ipc_reajustes():
    # ============================================================
    # MÓDULO 4 - IPC Y REAJUSTES
    # ============================================================
    # Permite actualizar montos en pesos chilenos mediante
    # el IPC oficial o un porcentaje ingresado manualmente.
    #
    # Modalidades:
    # 1. IPC oficial: utiliza índices del Banco Central.
    # 2. IPC manual: permite simular reajustes porcentuales.
    # ============================================================

    st.subheader("📊 IPC y Reajustes")

    st.caption(
        "Calcula reajustes de precios, contratos y compras "
        "utilizando el IPC oficial de Chile o un porcentaje "
        "de variación definido manualmente."
    )

    modo_ipc = st.radio(
        "Modalidad de reajuste",
        [
            "IPC oficial",
            "IPC manual"
        ],
        horizontal=True,
        key="modo_reajuste_ipc"
    )



    # ============================================================
    # MODALIDAD 1 - REAJUSTE CON IPC OFICIAL
    # ============================================================
    # El usuario selecciona el monto original y los meses
    # de referencia para calcular el reajuste acumulado.
    # Los índices serán consultados al Banco Central.

    if modo_ipc == "IPC oficial":

        st.markdown("### Reajuste según IPC oficial")

        monto_ipc = campo_monto_clp("Monto original (CLP)", "ipc_monto_original_formateado")


        # ========================================================
        # SELECCIÓN DE PERÍODOS DEL IPC
        # ========================================================
        # Permite seleccionar directamente el mes y el año.
        # Las fechas se construyen con el día 1 porque el
        # índice IPC corresponde a períodos mensuales.

        meses_ipc = [
            "Enero", "Febrero", "Marzo", "Abril",
            "Mayo", "Junio", "Julio", "Agosto",
            "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]

        anios_ipc = list(range(2023, date.today().year + 1))



        # ========================================================
        # CONSULTAR PERÍODOS OFICIALES DISPONIBLES
        # ========================================================
        # Obtiene los índices publicados desde enero de 2023.
        # Se utilizarán para limitar los meses seleccionables.

        indices_disponibles = []

        try:
            datos_periodos_ipc = consultar_ipc(
                date(2023, 1, 1),
                date.today()
            )

            indices_disponibles = (
                datos_periodos_ipc["INDICE"]
                .dropna()
                .sort_index()
            )

            if not indices_disponibles.empty:

                ultimo_mes_disponible = (
                    indices_disponibles.index[-1]
                )

                st.caption(
                    "Último período IPC disponible: "
                    f"{meses_ipc[ultimo_mes_disponible.month - 1]} "
                    f"{ultimo_mes_disponible.year}"
                )

            else:
                st.warning(
                    "No se encontraron períodos IPC publicados."
                )

        except Exception as error:
            st.warning(
                f"No fue posible consultar los períodos IPC: {error}"
            )


        # ========================================================
        # MESES DISPONIBLES SEGÚN EL AÑO SELECCIONADO
        # ========================================================
        # Devuelve únicamente los meses que tienen un índice
        # IPC oficial publicado para el año indicado.

        def obtener_meses_disponibles(anio):

            # Si no hay datos oficiales disponibles,
            # conserva la lista completa de meses.
            if len(indices_disponibles) == 0:
                return meses_ipc

            # Identificar los meses con IPC publicado
            # correspondientes al año seleccionado.
            meses_publicados = [
                meses_ipc[fecha.month - 1]
                for fecha in indices_disponibles.index
                if fecha.year == anio
            ]

            # Evitar meses duplicados.
            return list(dict.fromkeys(meses_publicados))

        col_inicio_ipc, col_fin_ipc = st.columns(2)

        with col_inicio_ipc:

            st.markdown("**Período inicial**")

            # Identificar el año seleccionado para obtener
            # únicamente los meses con IPC publicado.
            anio_inicio_seleccionado = st.session_state.get(
                "ipc_anio_inicial",
                anios_ipc[-1]
            )

            # Detectar si el usuario cambió el año inicial.
            anio_inicio_anterior = st.session_state.get(
                "ipc_anio_inicio_anterior"
            )

            if anio_inicio_anterior != anio_inicio_seleccionado:

                # Obtener los meses publicados del nuevo año.
                meses_nuevo_anio_inicio = obtener_meses_disponibles(
                    anio_inicio_seleccionado
                )

                # Seleccionar automáticamente el primer mes disponible.
                if meses_nuevo_anio_inicio:
                    st.session_state["ipc_mes_inicial"] = (
                        meses_nuevo_anio_inicio[0]
                    )

                # Guardar el año para detectar futuros cambios.
                st.session_state["ipc_anio_inicio_anterior"] = (
                    anio_inicio_seleccionado
                )

            meses_inicio_disponibles = obtener_meses_disponibles(
                anio_inicio_seleccionado
            )

            mes_inicial_ipc = st.selectbox(
                "Mes inicial",
                meses_inicio_disponibles,
                index=0,
                key="ipc_mes_inicial"
            )

            anio_inicial_ipc = st.selectbox(
                "Año inicial",
                anios_ipc,
                index=len(anios_ipc) - 1,
                key="ipc_anio_inicial"
            )

        with col_fin_ipc:

            st.markdown("**Período final**")

            # Identificar el año final seleccionado para
            # mostrar únicamente los meses con IPC publicado.
            # Identificar el año final seleccionado.
            anio_fin_seleccionado = st.session_state.get(
                "ipc_anio_final",
                anios_ipc[-1]
            )

            # Detectar si el usuario cambió el año final.
            anio_fin_anterior = st.session_state.get(
                "ipc_anio_fin_anterior"
            )

            if anio_fin_anterior != anio_fin_seleccionado:

                # Obtener los meses publicados del nuevo año.
                meses_nuevo_anio = obtener_meses_disponibles(
                    anio_fin_seleccionado
                )

                # Seleccionar automáticamente el último mes.
                if meses_nuevo_anio:
                    st.session_state["ipc_mes_final"] = (
                        meses_nuevo_anio[-1]
                    )

                # Guardar el año para detectar futuros cambios.
                st.session_state["ipc_anio_fin_anterior"] = (
                    anio_fin_seleccionado
                )


            meses_fin_disponibles = obtener_meses_disponibles(
                anio_fin_seleccionado
            )

            # Seleccionar por defecto el último mes publicado.
            mes_final_ipc = st.selectbox(
                "Mes final",
                meses_fin_disponibles,
                index=len(meses_fin_disponibles) - 1,
                key="ipc_mes_final"
            )

            anio_final_ipc = st.selectbox(
                "Año final",
                anios_ipc,
                index=len(anios_ipc) - 1,
                key="ipc_anio_final"
            )

        # Convertir los períodos seleccionados a fechas.
        # Se conserva la compatibilidad con el cálculo actual.

        fecha_inicio_reajuste = date(
            anio_inicial_ipc,
            meses_ipc.index(mes_inicial_ipc) + 1,
            1
        )

        fecha_fin_reajuste = date(
            anio_final_ipc,
            meses_ipc.index(mes_final_ipc) + 1,
            1
        )

        st.caption(
            "El reajuste se calculará utilizando el índice "
            "IPC del mes inicial y del mes final seleccionado."
        )



        # ========================================================
        # CÁLCULO DEL REAJUSTE CON IPC OFICIAL
        # ========================================================
        # Se comparan los índices del mes inicial y final.
        # Fórmula: (IPC final / IPC inicial - 1) * 100.
        # El cálculo requiere índices publicados para ambos meses.

        mes_inicio = fecha_inicio_reajuste.replace(day=1)
        mes_fin = fecha_fin_reajuste.replace(day=1)

        if mes_inicio > mes_fin:
            st.warning(
                "El mes final no puede ser anterior al mes inicial."
            )

        elif monto_ipc <= 0:
            st.info(
                "Ingresa un monto original mayor que cero "
                "para calcular el reajuste."
            )

        else:
            try:
                # Consultar los índices oficiales del período.
                datos_reajuste = consultar_ipc(
                    mes_inicio,
                    mes_fin
                )

                indices = datos_reajuste["INDICE"].dropna()

                # Buscar exactamente los meses seleccionados.
                indice_inicial = indices[
                    (indices.index.year == mes_inicio.year) &
                    (indices.index.month == mes_inicio.month)
                ]

                indice_final = indices[
                    (indices.index.year == mes_fin.year) &
                    (indices.index.month == mes_fin.month)
                ]

                if indice_inicial.empty or indice_final.empty:
                    st.warning(
                        "No existen índices IPC publicados para "
                        "uno o ambos meses seleccionados."
                    )

                elif indice_inicial.iloc[0] <= 0:
                    st.error("El índice IPC inicial no es válido.")

                else:
                    # Calcular la variación acumulada.
                    ipc_inicial = float(indice_inicial.iloc[0])
                    ipc_final = float(indice_final.iloc[0])

                    reajuste_pct = (
                        (ipc_final / ipc_inicial) - 1
                    ) * 100

                    monto_reajustado = monto_ipc * (
                        ipc_final / ipc_inicial
                    )

                    diferencia_ipc = monto_reajustado - monto_ipc

                    # Mostrar los resultados económicos.
                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Monto original",
                        formato_pesos(monto_ipc)
                    )

                    col2.metric(
                        "Monto reajustado",
                        formato_pesos(monto_reajustado)
                    )

                    col3.metric(
                        "Reajuste acumulado",
                        f"{reajuste_pct:+.2f}%"
                    )

                    st.caption(
                        f"IPC inicial: {ipc_inicial:.2f} | "
                        f"IPC final: {ipc_final:.2f} | "
                        f"Diferencia: {formato_pesos(diferencia_ipc)}"
                    )

                    # Exportación del cálculo oficial con respaldo de índices.
                    try:
                        excel_oficial = crear_excel_reajuste(
                            "IPC oficial", monto_ipc, monto_reajustado,
                            reajuste_pct, diferencia_ipc,
                            f"{mes_inicial_ipc} {anio_inicial_ipc}",
                            f"{mes_final_ipc} {anio_final_ipc}",
                            ipc_inicial, ipc_final,
                        )
                        st.download_button(
                            "📊 Descargar informe Excel del reajuste",
                            data=excel_oficial,
                            file_name=f"Reajuste_IPC_{anio_inicial_ipc}_{anio_final_ipc}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="descarga_excel_ipc_oficial",
                            use_container_width=True,
                        )
                    except Exception as error_excel:
                        st.warning(f"No fue posible preparar el Excel: {error_excel}")

                    # Tarjeta PNG oficial: conserva los índices y períodos usados.
                    try:
                        tarjeta_oficial = crear_tarjeta_ipc_oficial(
                            monto_ipc, monto_reajustado, reajuste_pct, diferencia_ipc,
                            f"{mes_inicial_ipc} {anio_inicial_ipc}",
                            f"{mes_final_ipc} {anio_final_ipc}",
                            ipc_inicial, ipc_final,
                        )
                        st.download_button(
                            "🖼️ Descargar tarjeta PNG del reajuste IPC oficial",
                            data=tarjeta_oficial,
                            file_name=f"Tarjeta_IPC_{anio_inicial_ipc}_{anio_final_ipc}.png",
                            mime="image/png",
                            key="descarga_png_ipc_oficial",
                            use_container_width=True,
                        )
                    except Exception as error_png:
                        st.warning(f"No fue posible preparar la tarjeta PNG oficial: {error_png}")

                    # ====================================================
                    # DESGLOSE DEL CÁLCULO DE REAJUSTE OFICIAL
                    # ====================================================
                    # Se utiliza la precisión original de los índices
                    # obtenidos del Banco Central para evitar diferencias
                    # por redondeos en el cálculo económico.
                    with st.expander("🧮 Ver desglose del cálculo", expanded=True):
                        st.markdown("**Períodos e índices utilizados**")
                        st.write(
                            f"Período inicial: **{mes_inicial_ipc} {anio_inicial_ipc}** "
                            f"— índice IPC: **{ipc_inicial:.4f}**"
                        )
                        st.write(
                            f"Período final: **{mes_final_ipc} {anio_final_ipc}** "
                            f"— índice IPC: **{ipc_final:.4f}**"
                        )

                        st.markdown("**Fórmulas aplicadas**")
                        st.latex(r"\text{Variación (\%)} = \left(\frac{IPC_{final}}{IPC_{inicial}}-1\right)\times 100")
                        st.latex(r"\text{Monto reajustado} = \text{Monto original}\times\frac{IPC_{final}}{IPC_{inicial}}")

                        st.markdown("**Resultados del cálculo**")
                        st.write(
                            f"Variación del IPC: **{reajuste_pct:+.4f}%**"
                        )
                        st.write(
                            f"Monto original: **{formato_pesos(monto_ipc)}**"
                        )
                        st.write(
                            f"Monto reajustado: **{formato_pesos(monto_reajustado)}**"
                        )
                        st.write(
                            f"Diferencia económica: **{formato_pesos(diferencia_ipc)}**"
                        )
                        st.caption(
                            "Los índices se presentan con cuatro decimales; "
                            "los cálculos utilizan el valor completo recibido "
                            "de la fuente. El reajuste compara los dos meses "
                            "seleccionados y no sustituye las condiciones "
                            "establecidas en un contrato."
                        )

            except Exception as error:
                st.error(
                    f"No fue posible calcular el reajuste: {error}"
                )



    # ============================================================
    # MODALIDAD 2 - REAJUSTE MANUAL
    # ============================================================
    # Permite simular aumentos o disminuciones de precios
    # mediante un porcentaje ingresado por el usuario.
    # No utiliza índices oficiales del Banco Central.

    elif modo_ipc == "IPC manual":

        st.markdown("### Simulación de reajuste manual")
        st.caption(
            "Compara reajustes hipotéticos en CLP. Los porcentajes son "
            "ingresados por el usuario y no representan proyecciones oficiales del IPC."
        )

        # Se mantiene el cálculo individual original, con su Excel existente.
        modalidad_simulacion = st.selectbox(
            "Tipo de simulación",
            [
                "Un monto y varios porcentajes",
                "Varios montos y un porcentaje",
                "Varios montos y porcentajes diferentes",
                "Cálculo individual (original)",
            ],
            key="ipc_tipo_simulacion_manual",
        )

        if modalidad_simulacion == "Cálculo individual (original)":

            st.markdown("### Simulación de reajuste manual")

            st.caption(
                "Ingresa el monto original y el porcentaje "
                "de reajuste que deseas aplicar."
            )

            monto_manual = campo_monto_clp("Monto original (CLP)", "ipc_monto_manual_formateado")

            porcentaje_manual = st.number_input(
                "Porcentaje de reajuste (%)",
                min_value=-100.0,
                max_value=1000.0,
                value=0.0,
                step=0.5,
                format="%.2f",
                key="ipc_porcentaje_manual"
            )

            # ========================================================
            # CÁLCULO DEL REAJUSTE MANUAL
            # ========================================================
            # Fórmula:
            # Monto reajustado = Monto original * (1 + % / 100).
            # Un porcentaje negativo representa una disminución.

            if monto_manual <= 0:

                st.info(
                    "Ingresa un monto original mayor que cero "
                    "para calcular el reajuste."
                )

            else:

                monto_reajustado_manual = monto_manual * (
                    1 + porcentaje_manual / 100
                )

                diferencia_manual = (
                    monto_reajustado_manual - monto_manual
                )

                # Mostrar los resultados económicos.
                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Monto original",
                    formato_pesos(monto_manual)
                )

                col2.metric(
                    "Monto reajustado",
                    formato_pesos(monto_reajustado_manual)
                )

                col3.metric(
                    "Reajuste aplicado",
                    f"{porcentaje_manual:+.2f}%"
                )

                st.caption(
                    f"Diferencia económica: "
                    f"{formato_pesos(diferencia_manual)}"
                )

                # Exportación de la simulación manual, diferenciada del IPC oficial.
                try:
                    excel_manual = crear_excel_reajuste(
                        "IPC manual", monto_manual, monto_reajustado_manual,
                        porcentaje_manual, diferencia_manual,
                    )
                    st.download_button(
                        "📊 Descargar informe Excel del reajuste",
                        data=excel_manual,
                        file_name="Simulacion_Reajuste_Manual.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="descarga_excel_ipc_manual",
                        use_container_width=True,
                    )
                except Exception as error_excel:
                    st.warning(f"No fue posible preparar el Excel: {error_excel}")

                # Tarjeta PNG del cálculo individual para compartir.
                try:
                    tarjeta_individual = crear_tarjeta_simulacion(
                        "Cálculo individual (original)",
                        [("Reajuste", monto_manual, porcentaje_manual)],
                    )
                    st.download_button(
                        "🖼️ Descargar tarjeta PNG del reajuste",
                        data=tarjeta_individual,
                        file_name="Tarjeta_Reajuste_Individual.png",
                        mime="image/png",
                        key="descarga_png_ipc_manual",
                        use_container_width=True,
                    )
                except Exception as error_png:
                    st.warning(f"No fue posible preparar la tarjeta PNG: {error_png}")

                st.info(
                    "Simulación referencial. El porcentaje "
                    "ingresado manualmente no corresponde "
                    "necesariamente al IPC oficial."
                )

        else:
            # Cada escenario se calcula por separado: no se aplican
            # reajustes sucesivos ni se acumulan porcentajes entre filas.
            cantidad = st.number_input(
                "Cantidad de escenarios",
                min_value=2, max_value=10, value=3, step=1,
                key="ipc_cantidad_escenarios",
            )
            escenarios = []

            if modalidad_simulacion == "Un monto y varios porcentajes":
                monto_comun = campo_monto_clp(
                    "Monto original común (CLP)", "ipc_manual_monto_comun"
                )
                for i in range(int(cantidad)):
                    porcentaje = campo_porcentaje_manual(
                        f"Escenario {i + 1} · Reajuste (%)",
                        f"ipc_manual_pct_esc_{i}",
                    )
                    escenarios.append((f"Escenario {i + 1}", monto_comun, porcentaje))

            elif modalidad_simulacion == "Varios montos y un porcentaje":
                porcentaje_comun = campo_porcentaje_manual(
                    "Porcentaje común de reajuste (%)",
                    "ipc_manual_pct_comun",
                )
                for i in range(int(cantidad)):
                    monto = campo_monto_clp(
                        f"Monto {i + 1} (CLP)", f"ipc_manual_monto_{i}"
                    )
                    escenarios.append((f"Monto {i + 1}", monto, porcentaje_comun))

            else:
                for i in range(int(cantidad)):
                    col_monto, col_porcentaje = st.columns(2)
                    with col_monto:
                        monto = campo_monto_clp(
                            f"Monto {i + 1} (CLP)", f"ipc_manual_monto_dif_{i}"
                        )
                    with col_porcentaje:
                        porcentaje = campo_porcentaje_manual(
                            f"Reajuste {i + 1} (%)",
                            f"ipc_manual_pct_dif_{i}",
                        )
                    escenarios.append((f"Escenario {i + 1}", monto, porcentaje))

            if any(monto <= 0 for _, monto, _ in escenarios):
                st.info("Ingresa un monto mayor que cero en todos los escenarios para comparar.")
            elif any(porcentaje is None for _, _, porcentaje in escenarios):
                st.info(
                    "Ingresa un porcentaje válido en todos los escenarios "
                    "para mostrar la comparación."
                )
            else:
                # Resultados en CLP; los montos y porcentajes se conservan
                # como números hasta completar los cálculos.
                resultados = []
                for nombre, monto, porcentaje in escenarios:
                    reajustado = monto * (1 + porcentaje / 100)
                    resultados.append({
                        "Escenario": nombre,
                        "Monto original": formato_pesos(monto),
                        "Reajuste (%)": f"{porcentaje:+.2f}%".replace(".", ","),
                        "Monto reajustado": formato_pesos(reajustado),
                        "Diferencia": formato_pesos(reajustado - monto),
                    })

                # Mostrar totales únicamente cuando los escenarios representan
                # montos distintos. Con un monto común son alternativas excluyentes:
                # sumarlas duplicaría artificialmente el mismo presupuesto.
                if modalidad_simulacion != "Un monto y varios porcentajes":
                    total_original = sum(monto for _, monto, _ in escenarios)
                    total_reajustado = sum(
                        monto * (1 + porcentaje / 100)
                        for _, monto, porcentaje in escenarios
                    )
                    resultados.append({
                        "Escenario": "TOTAL",
                        "Monto original": formato_pesos(total_original),
                        "Reajuste (%)": "—",
                        "Monto reajustado": formato_pesos(total_reajustado),
                        "Diferencia": formato_pesos(total_reajustado - total_original),
                    })

                st.markdown("#### Comparación de escenarios")
                st.dataframe(resultados, hide_index=True, use_container_width=True)
                # Exportar la misma comparación a Excel, con desglose y fórmulas.
                try:
                    excel_escenarios = crear_excel_simulaciones_multiples(
                        modalidad_simulacion, escenarios
                    )
                    st.download_button(
                        "📊 Descargar informe Excel de escenarios",
                        data=excel_escenarios,
                        file_name="Simulacion_Reajustes_Multiples.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="descarga_excel_ipc_escenarios",
                        use_container_width=True,
                    )
                except Exception as error_excel:
                    st.warning(f"No fue posible preparar el Excel: {error_excel}")

                # Tarjeta PNG para las tres modalidades de escenarios múltiples.
                try:
                    tarjeta_escenarios = crear_tarjeta_simulacion(
                        modalidad_simulacion, escenarios
                    )
                    st.download_button(
                        "🖼️ Descargar tarjeta PNG de escenarios",
                        data=tarjeta_escenarios,
                        file_name="Tarjeta_Simulacion_Reajustes.png",
                        mime="image/png",
                        key="descarga_png_ipc_escenarios",
                        use_container_width=True,
                    )
                except Exception as error_png:
                    st.warning(f"No fue posible preparar la tarjeta PNG: {error_png}")

                st.caption(
                    "Cada fila aplica su porcentaje directamente al monto original. "
                    "Las diferencias negativas representan disminuciones."
                )
                st.info(
                    "Simulación referencial. Estos porcentajes no corresponden "
                    "necesariamente al IPC oficial."
                )
