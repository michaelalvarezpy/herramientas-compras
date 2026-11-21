import streamlit as st
import plotly.graph_objects as go
from Inteligencia_Economica.Modulos.formatos import formato_moneda, formato_pesos
from io import BytesIO
from datetime import datetime
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.marker import DataPoint
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from PIL import Image, ImageDraw, ImageFont


def _formato_clp(valor):
    return f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _excel_simulacion(datos, escenarios):
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen ejecutivo"
    navy, teal, white = "14243A", "16B8AA", "FFFFFF"
    ws.merge_cells("A1:D2")
    ws["A1"] = "SIMULACIÓN ECONÓMICA"
    ws["A1"].font = Font(name="Aptos Display", size=17, bold=True, color=white)
    ws["A1"].fill = PatternFill("solid", fgColor=navy)
    ws["A1"].alignment = Alignment(vertical="center", horizontal="left", indent=1)
    ws.row_dimensions[1].height = 25
    ws.row_dimensions[2].height = 17
    ws["A3"] = "ANÁLISIS CAMBIARIO · RESUMEN EJECUTIVO"
    ws["A3"].font = Font(name="Aptos", bold=True, size=11, color=teal)
    ws.row_dimensions[3].height = 24
    ws["A4"] = "Fecha de elaboración"
    ws["B4"] = datetime.now().strftime("%d-%m-%Y %H:%M")
    filas = [
        (5, "Moneda de origen", datos["moneda"]),
        (6, "Monto original", datos["monto"]),
        (7, "Fecha del tipo de cambio de referencia", datos["fecha"]),
        (8, "Modalidad", datos["modalidad"]),
        (9, "Tipo de cambio de referencia (CLP)", datos["tasa_base"]),
        (10, "Tipo de cambio simulado (CLP)", datos["tasa_simulada"]),
        (11, "Variación equivalente", datos["variacion"] / 100),
        (13, "Costo base (CLP)", datos["costo_base"]),
        (14, "Costo simulado (CLP)", datos["costo_simulado"]),
        (15, "Diferencia económica (CLP)", datos["diferencia"]),
    ]
    for fila, etiqueta, valor in filas:
        ws.cell(fila, 1, etiqueta)
        ws.cell(fila, 2, valor)
        ws.cell(fila, 1).font = Font(name="Aptos", bold=True, color=navy)
        ws.cell(fila, 2).font = Font(name="Aptos", color=navy, bold=fila in (13,14,15))
    for fila in (6,9,10,13,14,15):
        ws.cell(fila,2).number_format = '#,##0.00;[Red]-#,##0.00'
    ws["B11"].number_format = '+0.00%;-0.00%;0.00%'
    for fila in (13,14,15):
        for celda in ws[fila][:2]:
            celda.fill = PatternFill("solid", fgColor="EAF5F4")
    ws["A17"] = "Interpretación"
    ws["A17"].font = Font(bold=True, color=teal, size=12)
    ws.merge_cells("A18:D19")
    ws["A18"] = datos["interpretacion"]
    ws["A18"].alignment = Alignment(wrap_text=True, vertical="center", indent=1)
    ws.row_dimensions[18].height = 29
    ws.row_dimensions[19].height = 23
    ws["A21"] = "Nota: Simulación referencial; no constituye una proyección del tipo de cambio futuro."
    ws.merge_cells("A21:D21")
    ws["A21"].font = Font(italic=True, color="667085", size=10)
    ws.column_dimensions["A"].width = 49
    ws.column_dimensions["B"].width = 31
    ws.column_dimensions["C"].width = 19
    ws.column_dimensions["D"].width = 19
    ws.freeze_panes = "B5"

    sh = wb.create_sheet("Comparación de escenarios")
    headers = ["Escenario", "Tipo de cambio (CLP)", "Costo total (CLP)", "Diferencia (CLP)"]
    sh.append(headers)
    for cell in sh[1]:
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.font = Font(bold=True, color=white)
        cell.alignment = Alignment(horizontal="center")
    for escenario in escenarios:
        sh.append([escenario[h] for h in headers])
        if "seleccionado" in escenario["Escenario"].lower() or "personalizado" in escenario["Escenario"].lower():
            for cell in sh[sh.max_row]:
                cell.fill = PatternFill("solid", fgColor="DDF5F1")
                cell.font = Font(bold=True, color=navy)
    for fila in sh.iter_rows(min_row=2, min_col=2, max_col=4):
        for cell in fila:
            cell.number_format = '#,##0.00;[Red]-#,##0.00'
    for i, ancho in enumerate((31, 27, 26, 26), 1):
        sh.column_dimensions[get_column_letter(i)].width = ancho
    sh.freeze_panes = "B2"
    sh.sheet_view.showGridLines = False
    ws.sheet_view.showGridLines = False
    sh.auto_filter.ref = f"A1:D{sh.max_row}"
    # Imagen de gráfico incrustada: Excel Online muestra de forma consistente
    # los ahorros, sobrecostos, categorías y etiquetas monetarias.
    from openpyxl.drawing.image import Image as ExcelImage
    grafico_png = _imagen_grafico_escenarios(escenarios)
    imagen_excel = ExcelImage(BytesIO(grafico_png))
    imagen_excel.width = 960
    imagen_excel.height = 510
    sh.add_image(imagen_excel, "F3")
    sh.column_dimensions["E"].width = 3
    output = BytesIO()
    wb.save(output)
    return output.getvalue()



def _imagen_grafico_escenarios(escenarios):
    """Gráfico PNG con etiquetas, robusto al abrir el XLSX en Excel Online."""
    from PIL import Image, ImageDraw
    import math

    W, H = 1440, 765
    im = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(im)
    f_titulo = _fuente(37, True)
    f_eje = _fuente(22, False)
    f_valor = _fuente(22, True)
    f_pie = _fuente(19, False)
    d.text((65, 34), "Impacto económico por escenario", font=f_titulo, fill="#14243A")
    d.text((65, 94), "Diferencia respecto del costo base (CLP)", font=f_eje, fill="#506579")

    valores = [float(e.get("Diferencia (CLP)", 0) or 0) for e in escenarios]
    etiquetas = [str(e.get("Escenario", "")) for e in escenarios]
    max_abs = max([abs(v) for v in valores] + [1.0])
    limite = max_abs * 1.22
    izq, der, arriba, abajo = 190, W - 48, 165, 625
    y0 = (arriba + abajo) // 2
    escala = (abajo - arriba) / (2 * limite)
    # Líneas de referencia y eje cero
    for factor in [-1, -0.5, 0, 0.5, 1]:
        y = round(y0 - factor * max_abs * escala)
        d.line((izq, y, der, y), fill="#D8E3E8" if factor else "#617789", width=2 if factor else 4)
        etiqueta = _formato_clp(factor * max_abs)
        d.text((izq - 12, y - 13), etiqueta, anchor="ra", font=f_pie, fill="#63788B")
    n = max(1, len(valores))
    ancho_grupo = (der - izq) / n
    ancho_barra = min(130, ancho_grupo * 0.53)
    for i, (valor, nombre) in enumerate(zip(valores, etiquetas)):
        cx = izq + ancho_grupo * (i + 0.5)
        yv = y0 - valor * escala
        color = "#20A99B" if valor < 0 else ("#E85D61" if valor > 0 else "#94A3B8")
        if valor:
            d.rounded_rectangle((round(cx-ancho_barra/2), round(min(y0,yv)), round(cx+ancho_barra/2), round(max(y0,yv))), radius=5, fill=color)
        else:
            d.ellipse((cx-5, y0-5, cx+5, y0+5), fill=color)
        etiqueta_valor = ("+" if valor > 0 else "") + _formato_clp(valor)
        # Ubicar etiqueta afuera de cada barra para legibilidad.
        y_texto = yv - 14 if valor > 0 else (yv + 14 if valor < 0 else y0 - 15)
        d.text((cx, y_texto), etiqueta_valor, anchor="mb" if valor >= 0 else "mt", font=f_valor, fill=color)
        # Etiquetas largas en dos líneas.
        nombre = nombre.replace(" (seleccionado)", "\n(seleccionado)").replace("Personalizado (", "Personalizado\n(")
        d.multiline_text((cx, abajo + 18), nombre, anchor="ma", align="center", spacing=3, font=f_pie, fill="#14243A")
    d.text((W/2, H-37), "Verde: ahorro     |     Rojo: sobrecosto     |     Valores expresados en pesos chilenos", anchor="mm", font=f_pie, fill="#51687A")
    buf = BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _fuente(tamano, negrita=False):
    candidatos = (["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
                  if negrita else ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for ruta in candidatos:
        try:
            return ImageFont.truetype(ruta, tamano)
        except OSError:
            pass
    return ImageFont.load_default()


def _imagen_simulacion(datos):
    ancho, alto = 1100, 680
    img = Image.new("RGB", (ancho, alto), "#0C1525")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((35, 35, 1065, 645), radius=28, fill="#14243A", outline="#29475A", width=2)
    d.text((75, 75), "SIMULACIÓN ECONÓMICA", font=_fuente(35, True), fill="#FFFFFF")
    d.text((75, 130), f"Compra: { _formato_clp(datos['monto']) } {datos['moneda']}", font=_fuente(24), fill="#B9D1DE")
    d.line((75, 182, 1025, 182), fill="#2C5664", width=2)
    etiquetas = [
        ("COSTO BASE", datos["costo_base"], 215),
        ("COSTO SIMULADO", datos["costo_simulado"], 325),
        ("DIFERENCIA ECONÓMICA", datos["diferencia"], 435),
    ]
    for etiqueta, valor, y in etiquetas:
        d.text((78, y), etiqueta, font=_fuente(18, True), fill="#8DAFBF")
        color = "#FF8585" if etiqueta.startswith("DIFERENCIA") and valor > 0 else ("#55D7C1" if etiqueta.startswith("DIFERENCIA") and valor < 0 else "#FFFFFF")
        d.text((78, y + 27), f"{_formato_clp(valor)} CLP", font=_fuente(34, True), fill=color)
    d.text((650, 235), "TIPO DE CAMBIO", font=_fuente(18, True), fill="#8DAFBF")
    d.text((650, 274), f"Base: {_formato_clp(datos['tasa_base'])}", font=_fuente(22), fill="#FFFFFF")
    d.text((650, 315), f"Simulado: {_formato_clp(datos['tasa_simulada'])}", font=_fuente(22), fill="#FFFFFF")
    d.text((650, 376), "VARIACIÓN", font=_fuente(18, True), fill="#8DAFBF")
    d.text((650, 412), f"{datos['variacion']:+.2f}%", font=_fuente(35, True), fill="#55D7C1" if datos['variacion'] < 0 else "#FF8585" if datos['variacion'] > 0 else "#FFFFFF")
    if datos["diferencia"] > 0:
        mensaje = f"Sobrecosto de {_formato_clp(datos['diferencia'])} CLP con una variación de {datos['variacion']:+.2f}%."
    elif datos["diferencia"] < 0:
        mensaje = f"Ahorro de {_formato_clp(abs(datos['diferencia']))} CLP con una variación de {datos['variacion']:+.2f}%."
    else:
        mensaje = "Sin diferencia económica respecto del tipo de cambio base."
    d.text((78, 513), mensaje, font=_fuente(18, True), fill="#B9D1DE")
    d.line((75, 555, 1025, 555), fill="#2C5664", width=2)
    d.text((75, 576), f"Referencia: {datos['fecha']}  |  Elaborado: {datetime.now():%d-%m-%Y}", font=_fuente(16), fill="#B9D1DE")
    d.text((75, 607), "Simulación referencial. No es una proyección del tipo de cambio.", font=_fuente(15), fill="#8DAFBF")
    output = BytesIO()
    img.save(output, format="PNG", optimize=True)
    return output.getvalue()



def mostrar_simulador(indicadores):
    # SIMULADOR ECONÓMICO

    st.subheader("🔮 Simulador Económico")

    st.caption(
        "Evalúa cómo las variaciones del tipo de cambio "
        "afectan el costo de una compra en pesos chilenos."
    )

    col_monto_sim, col_moneda_sim = st.columns(2)

    with col_monto_sim:
        monto_simulacion = st.number_input(
            "Monto de la compra",
            min_value=0.0,
            value=0.0,
            step=1000.0,
            format="%.2f",
            key="simulador_monto"
        )

    with col_moneda_sim:
        moneda_simulacion = st.selectbox(
            "Moneda de la compra",
            ["USD", "EUR", "UF"],
            key="simulador_moneda"
        )

    informacion_sim = indicadores.get(moneda_simulacion)

    if informacion_sim:

        tasa_base = float(informacion_sim["valor"])

        st.caption(
            f"Tipo de cambio de referencia: "
            f"${formato_moneda(tasa_base)} CLP "
            f"({informacion_sim['fecha']:%d-%m-%Y})"
        )

        # Dos modalidades: porcentaje o tipo de cambio definido por el usuario.
        modalidad = st.radio(
            "Modalidad de simulación",
            ["Variación porcentual (%)", "Tipo de cambio personalizado (CLP)"],
            horizontal=True,
            key="simulador_modalidad"
        )

        if modalidad == "Variación porcentual (%)":
            # El rango habitual se mantiene en +/-20%; otros rangos son opcionales.
            rango_simulacion = st.selectbox(
                "Rango de variación",
                ["Normal (±20%)", "Ampliado (±50%)", "Extraordinario (-99% a +100%)"],
                key="simulador_rango"
            )
            limites_rango = {
                "Normal (±20%)": (-20, 20),
                "Ampliado (±50%)": (-50, 50),
                "Extraordinario (-99% a +100%)": (-99, 100),
            }
            minimo, maximo = limites_rango[rango_simulacion]
            # Claves independientes evitan conflictos al cambiar los límites.
            variacion_simulacion = st.slider(
                "Variación del tipo de cambio (%)",
                min_value=minimo,
                max_value=maximo,
                value=5,
                step=1,
                key=f"simulador_variacion_{maximo}"
            )
            tasa_simulada = tasa_base * (1 + variacion_simulacion / 100)
        else:
            # La clave incluye la moneda para conservar valores independientes.
            tasa_simulada = st.number_input(
                f"Tipo de cambio hipotético ({moneda_simulacion} a CLP)",
                min_value=0.01,
                value=float(round(tasa_base, 2)),
                step=1.0,
                format="%.2f",
                key=f"simulador_tasa_manual_{moneda_simulacion}"
            )
            st.caption(
                "Ingresa el valor que quieras evaluar; no modifica "
                "el tipo de cambio oficial ni los demás módulos."
            )

        # Variación real respecto del valor oficial, también en modo manual.
        variacion_equivalente = (tasa_simulada / tasa_base - 1) * 100

        if monto_simulacion == 0:
            st.info(
                "Ingresa un monto de compra para visualizar "
                "los resultados y comparar escenarios."
            )

        else:

            costo_base = monto_simulacion * tasa_base
            costo_simulado = monto_simulacion * tasa_simulada

            diferencia = costo_simulado - costo_base

            col_base, col_simulado, col_diferencia = st.columns(3)

            with col_base:
                st.metric(
                    "Costo base",
                    f"${formato_moneda(costo_base)} CLP"
                )

            with col_simulado:
                st.metric(
                    "Costo simulado",
                    f"${formato_moneda(costo_simulado)} CLP"
                )

            with col_diferencia:
                st.metric(
                    "Diferencia económica",
                    f"{formato_pesos(diferencia)} CLP",
                    delta=f"{variacion_equivalente:+.2f}%",
                    delta_color="inverse"
                )

            # La compra mantiene su importe en la moneda de origen;
            # lo que cambia es su equivalencia en pesos chilenos.
            with st.expander("Detalle en moneda de origen"):
                st.write(
                    f"**Monto de la compra:** "
                    f"{formato_moneda(monto_simulacion)} {moneda_simulacion}"
                )
                st.write(
                    f"**Tipo de cambio de referencia:** "
                    f"{formato_moneda(tasa_base)} CLP por {moneda_simulacion}"
                )
                st.write(
                    f"**Tipo de cambio simulado:** "
                    f"{formato_moneda(tasa_simulada)} CLP por {moneda_simulacion}"
                )
                st.caption(
                    "El monto en moneda de origen no cambia por la variación "
                    "del tipo de cambio; cambia su costo equivalente en CLP."
                )

            st.caption(
                f"Tipo de cambio simulado: "
                f"${formato_moneda(tasa_simulada)} CLP | "
                f"Variación equivalente respecto de la referencia: "
                f"{variacion_equivalente:+.2f}%"
            )

            # Aclaraciones para interpretar los indicadores en reuniones.
            with st.expander("¿Qué significan estos resultados?"):
                st.markdown(
                    "**Costo base:** monto de la compra convertido con el "
                    "tipo de cambio de referencia.\n\n"
                    "**Costo simulado:** monto de la misma compra convertido "
                    "con el tipo de cambio hipotético.\n\n"
                    "**Diferencia económica:** costo simulado menos costo base; "
                    "un valor positivo indica sobrecosto y uno negativo, ahorro."
                )

            # Rojo para sobrecostos, verde para ahorros y neutro si no varía.
            if diferencia > 0:
                st.error(
                    f"Con un tipo de cambio de ${formato_moneda(tasa_simulada)} "
                    f"CLP, la compra costaría {formato_pesos(diferencia)} "
                    "CLP adicionales."
                )
            elif diferencia < 0:
                st.success(
                    f"Con un tipo de cambio de ${formato_moneda(tasa_simulada)} "
                    f"CLP, la compra tendría un ahorro referencial de "
                    f"${formato_moneda(abs(diferencia))} CLP."
                )
            else:
                st.caption(
                    "Sin variación económica: el costo simulado coincide "
                    "con el costo base."
                )

            st.info(
                "Esta simulación es referencial y no constituye "
                "una proyección del tipo de cambio futuro."
            )

            st.markdown("### 📊 Comparación de escenarios")

            st.caption(
                "Compara el impacto económico de diferentes "
                "variaciones del tipo de cambio."
            )

            escenarios = [-10, -5, 0, 5, 10]
            tabla_escenarios = []

            for variacion in escenarios:
                tasa_escenario = tasa_base * (1 + variacion / 100)
                costo_escenario = monto_simulacion * tasa_escenario
                diferencia_escenario = costo_escenario - costo_base

                tabla_escenarios.append({
                    "Escenario": f"{variacion:+d}%",
                    "Tipo de cambio (CLP)": tasa_escenario,
                    "Costo total (CLP)": costo_escenario,
                    "Diferencia (CLP)": diferencia_escenario
                })

            # Incluir la simulación seleccionada en ambas modalidades.
            # Evitar duplicados si coincide con un escenario estándar.
            escenario_coincidente = next(
                (
                    escenario for escenario in tabla_escenarios
                    if abs(escenario["Tipo de cambio (CLP)"] - tasa_simulada) < 0.000001
                ),
                None,
            )

            if escenario_coincidente is not None:
                # Identificar el escenario existente sin repetirlo.
                escenario_coincidente["Escenario"] += " (seleccionado)"
            else:
                if modalidad == "Variación porcentual (%)":
                    etiqueta_seleccionada = f"{variacion_simulacion:+d}% (seleccionado)"
                else:
                    etiqueta_seleccionada = (
                        f"Personalizado ({variacion_equivalente:+.2f}%)"
                    )

                tabla_escenarios.append({
                    "Escenario": etiqueta_seleccionada,
                    "Tipo de cambio (CLP)": tasa_simulada,
                    "Costo total (CLP)": costo_simulado,
                    "Diferencia (CLP)": diferencia,
                })

            # Mantener la lectura de escenarios de menor a mayor variación.
            tabla_escenarios.sort(key=lambda escenario: escenario["Tipo de cambio (CLP)"])

            tabla_formateada = []

            for escenario in tabla_escenarios:
                tabla_formateada.append({
                    "Escenario": escenario["Escenario"],
                    "Tipo de cambio (CLP)": (
                        "$" + formato_moneda(escenario["Tipo de cambio (CLP)"])
                    ),
                    "Costo total (CLP)": (
                        "$" + formato_moneda(escenario["Costo total (CLP)"])
                    ),
                    "Diferencia (CLP)": (
                        formato_pesos(escenario["Diferencia (CLP)"])
                    )

                })

            st.dataframe(
                tabla_formateada,
                hide_index=True,
                width="stretch"
            )

            st.markdown("### 📈 Impacto económico por escenario")

            variaciones_grafico = []
            diferencias_grafico = []
            colores_grafico = []

            for escenario in tabla_escenarios:
                variaciones_grafico.append(escenario["Escenario"])
                diferencia_valor = escenario["Diferencia (CLP)"]
                diferencias_grafico.append(diferencia_valor)

                if diferencia_valor > 0:
                    colores_grafico.append("#EF5350")
                elif diferencia_valor < 0:
                    colores_grafico.append("#26A69A")
                else:
                    colores_grafico.append("#90A4AE")

            fig_escenarios = go.Figure()

            fig_escenarios.add_trace(
                go.Bar(
                    x=variaciones_grafico,
                    y=diferencias_grafico,
                    marker_color=colores_grafico,
                    hovertemplate=(
                        "Escenario: %{x}<br>"
                        "Diferencia: $%{y:,.2f} CLP"
                        "<extra></extra>"
                    )
                )
            )

            fig_escenarios.update_layout(
                title="Variación del costo de la compra",
                template="plotly_dark",
                height=400,
                xaxis_title="Variación del tipo de cambio",
                yaxis_title="Diferencia económica (CLP)",
                showlegend=False,
                margin=dict(l=20, r=20, t=55, b=30)
            )

            st.plotly_chart(
                fig_escenarios,
                width="stretch"
            )

            # Exportaciones calculadas a partir de los mismos datos visibles.
            st.markdown("### 📤 Exportar y compartir análisis")
            st.caption("Descarga un informe Excel para presentar o una tarjeta PNG para WhatsApp.")
            if diferencia > 0:
                interpretacion = f"Con una variación de {variacion_equivalente:+.2f}% del tipo de cambio, la compra tendría un sobrecosto referencial de {_formato_clp(diferencia)} CLP."
            elif diferencia < 0:
                interpretacion = f"Con una variación de {variacion_equivalente:+.2f}% del tipo de cambio, la compra tendría un ahorro referencial de {_formato_clp(abs(diferencia))} CLP."
            else:
                interpretacion = "No existe diferencia económica frente al tipo de cambio de referencia."
            datos_exportacion = {
                "moneda": moneda_simulacion,
                "monto": monto_simulacion,
                "fecha": informacion_sim["fecha"].strftime("%d-%m-%Y"),
                "modalidad": modalidad,
                "tasa_base": tasa_base,
                "tasa_simulada": tasa_simulada,
                "variacion": variacion_equivalente,
                "costo_base": costo_base,
                "costo_simulado": costo_simulado,
                "diferencia": diferencia,
                "interpretacion": interpretacion,
            }
            col_excel, col_whatsapp = st.columns(2)
            with col_excel:
                st.download_button(
                    "📊 Descargar informe Excel",
                    data=_excel_simulacion(datos_exportacion, tabla_escenarios),
                    file_name=f"Simulacion_Economica_{moneda_simulacion}_{datetime.now():%Y%m%d}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="simulador_descargar_excel",
                    use_container_width=True,
                )
            with col_whatsapp:
                st.download_button(
                    "🖼️ Descargar tarjeta para WhatsApp",
                    data=_imagen_simulacion(datos_exportacion),
                    file_name=f"Resumen_Simulacion_{moneda_simulacion}_{datetime.now():%Y%m%d}.png",
                    mime="image/png",
                    key="simulador_descargar_png",
                    use_container_width=True,
                )

    else:
        st.warning(
            "No hay un tipo de cambio disponible "
            "para realizar la simulación."
        )
