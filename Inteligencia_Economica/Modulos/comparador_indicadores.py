"""Módulo del Comparador de Indicadores Económicos."""

from datetime import date, datetime, timedelta
from io import BytesIO

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from Inteligencia_Economica.Servicios.banco_central import consultar_monedas, consultar_ipc
from Inteligencia_Economica.Servicios.cobre import consultar_cobre


# Resta meses de calendario sin depender de librerías adicionales.
def restar_meses(fecha, cantidad):
    anio = fecha.year
    mes = fecha.month - cantidad
    while mes <= 0:
        mes += 12
        anio -= 1
    # Evita fechas inexistentes, como el 31 de febrero.
    if mes == 12:
        primer_dia_siguiente = date(anio + 1, 1, 1)
    else:
        primer_dia_siguiente = date(anio, mes + 1, 1)
    ultimo_dia_mes = (primer_dia_siguiente - timedelta(days=1)).day
    return date(anio, mes, min(fecha.day, ultimo_dia_mes))


def formato_fecha_resumen(fecha, mensual):
    """Presenta meses en español y conserva las fechas diarias completas."""
    if not mensual:
        return fecha.strftime("%d-%m-%Y")
    nombres_meses = (
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    )
    return f"{nombres_meses[fecha.month - 1]} {fecha.year}"



def generar_excel_comparativo(comparacion, variaciones, indicadores, columnas, unidades, decimales, mensual):
    """Genera un Excel profesional de tres hojas usando openpyxl."""
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as ExcelImage
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    libro = Workbook()
    resumen = libro.active
    resumen.title = "Resumen comparativo"
    historico = libro.create_sheet("Evolución histórica")
    grafico = libro.create_sheet("Gráfico comparativo")

    titulo = "COMPARADOR DE INDICADORES ECONÓMICOS"
    inicio = formato_fecha_resumen(comparacion.index[0], mensual)
    fin = formato_fecha_resumen(comparacion.index[-1], mensual)
    azul = "14243B"
    turquesa = "176A7A"
    blanco = "FFFFFF"
    formato_pct = '+0.00%;-0.00%;0.00%'

    # Preparar títulos y notas de origen en las tres hojas.
    for hoja in (resumen, historico, grafico):
        hoja.merge_cells("A1:I1")
        hoja["A1"] = titulo
        hoja["A1"].font = Font(bold=True, color=blanco, size=15)
        hoja["A1"].fill = PatternFill("solid", fgColor=azul)
        hoja["A1"].alignment = Alignment(vertical="center")
        hoja.row_dimensions[1].height = 32
        # Combinar las notas para que no queden cortadas por el ancho de A.
        hoja.merge_cells("A2:I2")
        hoja.merge_cells("A3:I3")
        hoja["A2"] = f"Período efectivo: {inicio} al {fin}"
        hoja["A3"] = "Fuente: Banco Central de Chile / serie de cobre configurada en la aplicación"
        hoja["A2"].alignment = Alignment(vertical="center")
        hoja["A3"].alignment = Alignment(vertical="center")
        hoja.freeze_panes = "B6"
        hoja.sheet_view.showGridLines = False
        hoja.column_dimensions["A"].width = 23
        for numero in range(2, 15):
            hoja.column_dimensions[get_column_letter(numero)].width = 23

    def agregar_encabezados(hoja, encabezados):
        for columna, texto in enumerate(encabezados, start=1):
            celda = hoja.cell(row=5, column=columna, value=texto)
            celda.fill = PatternFill("solid", fgColor=turquesa)
            celda.font = Font(bold=True, color=blanco)
            celda.alignment = Alignment(wrap_text=True, vertical="center")
        hoja.row_dimensions[5].height = 34

    # Hoja 1: valores originales y variación porcentual real de cada indicador.
    agregar_encabezados(resumen, [
        "Indicador", "Unidad", "Inicial", "Final", "Variación (%)",
        "Mínimo", "Fecha mínimo", "Máximo", "Fecha máximo",
    ])
    for indicador in indicadores:
        serie = comparacion[columnas[indicador]]
        minimo = serie.idxmin()
        maximo = serie.idxmax()
        resumen.append([
            indicador, unidades[indicador], float(serie.iloc[0]), float(serie.iloc[-1]),
            float(variaciones[indicador].iloc[-1]) / 100,
            float(serie.loc[minimo]), formato_fecha_resumen(minimo, mensual),
            float(serie.loc[maximo]), formato_fecha_resumen(maximo, mensual),
        ])
        fila = resumen.max_row
        for columna in (3, 4, 6, 8):
            resumen.cell(fila, columna).number_format = (
                '#,##0.0000' if decimales[indicador] == 4 else '#,##0.00'
            )
        resumen.cell(fila, 5).number_format = formato_pct
    # Nota combinada para que Excel Online muestre el texto completo.
    fila_nota = resumen.max_row + 3
    resumen.merge_cells(start_row=fila_nota, start_column=1, end_row=fila_nota, end_column=9)
    celda_nota = resumen.cell(fila_nota, 1,
        "Los extremos corresponden a fechas comunes; la variación usa el primer registro común como base.")
    celda_nota.alignment = Alignment(wrap_text=True, vertical="center")
    resumen.row_dimensions[fila_nota].height = 30
    resumen.auto_filter.ref = f"A5:I{5 + len(indicadores)}"

    # Hoja 2: valores originales y variaciones como números (no textos).
    encabezados = ["Fecha / mes"] + [f"{i} ({unidades[i]})" for i in indicadores]
    encabezados += [f"Variación {i} (%)" for i in indicadores]
    agregar_encabezados(historico, encabezados)
    for indice in comparacion.index:
        historico.append(
            [formato_fecha_resumen(indice, mensual)]
            + [float(comparacion.loc[indice, columnas[i]]) for i in indicadores]
            + [float(variaciones.loc[indice, i]) / 100 for i in indicadores]
        )
        fila = historico.max_row
        for posicion, indicador in enumerate(indicadores, start=2):
            historico.cell(fila, posicion).number_format = (
                '#,##0.0000' if decimales[indicador] == 4 else '#,##0.00'
            )
        for posicion in range(2 + len(indicadores), 2 + 2 * len(indicadores)):
            historico.cell(fila, posicion).number_format = formato_pct
    historico.auto_filter.ref = f"A5:{get_column_letter(len(encabezados))}{historico.max_row}"

    # Hoja 3: datos en puntos porcentuales y gráfico de líneas editable.
    agregar_encabezados(grafico, ["Fecha / mes"] + list(indicadores))
    for indice in comparacion.index:
        # Excel Online interpreta mejor las fechas reales que las etiquetas
        # de texto con caché: conservar fechas como valores de Excel.
        fecha_excel = indice.to_timestamp().to_pydatetime() if mensual else pd.Timestamp(indice).to_pydatetime()
        grafico.append(
            [fecha_excel]
            + [float(variaciones.loc[indice, i]) for i in indicadores]
        )
        grafico.cell(grafico.max_row, 1).number_format = "mmm yyyy" if mensual else "dd-mm-yyyy"
        for columna in range(2, 2 + len(indicadores)):
            grafico.cell(grafico.max_row, columna).number_format = '+0.00"%";-0.00"%";0.00"%"'

    # Crear el gráfico como PNG para garantizar que los meses se vean en Excel Online.
    # Los datos de las tres hojas siguen siendo editables; la imagen no es dinámica.
    colores = {
        "USD": "#35A7FF", "EUR": "#F4A261", "UF": "#D977E8",
        "IPC": "#28B487", "Cobre": "#E9B44C",
    }
    figura_excel, eje = plt.subplots(figsize=(13.5, 6.3), dpi=150)
    fechas = [
        indice.to_timestamp().to_pydatetime() if mensual
        else pd.Timestamp(indice).to_pydatetime()
        for indice in comparacion.index
    ]
    for indicador in indicadores:
        eje.plot(
            fechas, variaciones[indicador].astype(float).to_numpy(),
            label=indicador, color=colores[indicador], linewidth=2.3,
            marker="o", markersize=3.5,
        )
    eje.axhline(0, color="#7D8795", linestyle="--", linewidth=1)
    eje.set_title("Evolución porcentual de los indicadores", fontsize=15, weight="bold", pad=18)
    eje.set_ylabel("Variación desde el inicio (%)")
    eje.set_xlabel("Mes" if mensual else "Fecha")
    eje.grid(axis="y", alpha=0.22)
    eje.spines[["top", "right"]].set_visible(False)
    if mensual:
        nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        # Etiquetas explícitas: no dependen del motor de gráficos de Excel.
        eje.set_xticks(fechas)
        eje.set_xticklabels(
            [f"{nombres_meses[fecha.month - 1]} {fecha.year}" for fecha in fechas],
            rotation=40, ha="right",
        )
    else:
        eje.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=12))
        eje.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%Y"))
        figura_excel.autofmt_xdate(rotation=35)
    eje.legend(loc="upper center", bbox_to_anchor=(0.5, -0.19),
               ncol=min(len(indicadores), 5), frameon=False)
    figura_excel.subplots_adjust(bottom=0.26, top=0.88, left=0.09, right=0.98)
    imagen_png = BytesIO()
    figura_excel.savefig(imagen_png, format="png", dpi=150, facecolor="white")
    plt.close(figura_excel)
    imagen_png.seek(0)
    imagen_excel = ExcelImage(imagen_png)
    imagen_excel.width = 1050
    imagen_excel.height = 490
    grafico.add_image(imagen_excel, f"A{grafico.max_row + 5}")
    # La nota se coloca debajo de la imagen y ocupa varias columnas.
    fila_nota_grafico = grafico.max_row + 37
    grafico.merge_cells(start_row=fila_nota_grafico, start_column=1,
                        end_row=fila_nota_grafico, end_column=9)
    celda_nota_grafico = grafico.cell(fila_nota_grafico, 1,
        "Gráfico incorporado como imagen para compatibilidad con Excel Online; "
        "los datos se mantienen editables en las tablas.")
    celda_nota_grafico.alignment = Alignment(wrap_text=True, vertical="center")
    grafico.row_dimensions[fila_nota_grafico].height = 30

    # Crear el archivo en memoria, sin archivos temporales en el computador.
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()



def generar_ficha_png_comparativa(comparacion, variaciones, indicadores, columnas, unidades, decimales, mensual):
    """Genera una ficha ejecutiva PNG independiente del informe Excel."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.gridspec import GridSpec

    colores = {"USD": "#35A7FF", "EUR": "#F4A261", "UF": "#B58AE6",
               "IPC": "#28B487", "Cobre": "#E9B44C"}
    fondo = "#0B1526"
    blanco = "#F4F7FC"
    gris = "#A9B8CE"
    fig = plt.figure(figsize=(13, 8), dpi=160, facecolor=fondo)
    rejilla = GridSpec(3, 1, figure=fig, height_ratios=[0.8, 1.1, 3.1],
                      hspace=0.17, top=0.95, bottom=0.23, left=0.08, right=0.95)
    titulo_ax = fig.add_subplot(rejilla[0]); titulo_ax.axis("off")
    titulo_ax.text(0, 0.78, "COMPARADOR DE INDICADORES ECONÓMICOS",
                   color=blanco, fontsize=19, weight="bold", transform=titulo_ax.transAxes)
    inicio = formato_fecha_resumen(comparacion.index[0], mensual)
    fin = formato_fecha_resumen(comparacion.index[-1], mensual)
    titulo_ax.text(0, 0.29, f"Período efectivo: {inicio} al {fin}  |  Fuente: Banco Central de Chile / cobre",
                   color=gris, fontsize=10.5, transform=titulo_ax.transAxes)

    tarjetas = fig.add_subplot(rejilla[1]); tarjetas.axis("off")
    cantidad = len(indicadores)
    for posicion, indicador in enumerate(indicadores):
        x = (posicion + 0.5) / cantidad
        serie = comparacion[columnas[indicador]]
        variacion = float(variaciones[indicador].iloc[-1])
        formato = f"{{:,.{decimales[indicador]}f}}"
        # Formato numérico chileno para la ficha compartible.
        inicial = formato.format(float(serie.iloc[0])).replace(",", "§").replace(".", ",").replace("§", ".")
        final = formato.format(float(serie.iloc[-1])).replace(",", "§").replace(".", ",").replace("§", ".")
        tarjetas.text(x, 0.82, indicador, ha="center", color=colores[indicador],
                      fontsize=14, weight="bold", transform=tarjetas.transAxes)
        tarjetas.text(x, 0.45, f"{variacion:+.2f}%".replace(".", ","), ha="center", color=blanco,
                      fontsize=21 if cantidad <= 3 else 17, weight="bold", transform=tarjetas.transAxes)
        tarjetas.text(x, 0.15, f"{inicial} → {final}", ha="center", color=gris,
                      fontsize=9 if cantidad <= 3 else 7.5, transform=tarjetas.transAxes)

    eje = fig.add_subplot(rejilla[2]); eje.set_facecolor(fondo)
    fechas = [i.to_timestamp().to_pydatetime() if mensual else pd.Timestamp(i).to_pydatetime()
              for i in comparacion.index]
    for indicador in indicadores:
        eje.plot(fechas, variaciones[indicador].astype(float).to_numpy(),
                 color=colores[indicador], label=indicador, linewidth=2.4)
    eje.axhline(0, color="#8B97A9", linestyle="--", linewidth=1)
    eje.grid(axis="y", color="#41516A", alpha=0.4)
    eje.tick_params(colors=gris, labelsize=9)
    for borde in eje.spines.values():
        borde.set_visible(False)
    eje.set_ylabel("Variación desde el inicio (%)", color=gris, fontsize=10)
    if mensual and len(fechas) <= 18:
        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        eje.set_xticks(fechas)
        eje.set_xticklabels([f"{meses[f.month - 1]} {f.year}" for f in fechas], rotation=35, ha="right")
    else:
        eje.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=9))
        eje.xaxis.set_major_formatter(mdates.DateFormatter("%m-%Y" if mensual else "%d-%m-%Y"))
        fig.autofmt_xdate(rotation=30)
    # Leyenda a nivel de figura, dentro de un espacio reservado debajo del gráfico.
    # Así no se corta al exportar la ficha PNG de 2080 x 1280 píxeles.
    elementos, etiquetas = eje.get_legend_handles_labels()
    leyenda = fig.legend(elementos, etiquetas, loc="center", bbox_to_anchor=(0.5, 0.105),
                         ncol=min(cantidad, 5), frameon=False, fontsize=10)
    for texto in leyenda.get_texts():
        texto.set_color(blanco)
    fig.text(0.08, 0.035,
             "Variaciones relativas al primer registro común. Comparación descriptiva; no implica causalidad.",
             color=gris, fontsize=9)
    salida = BytesIO()
    fig.savefig(salida, format="png", dpi=160, facecolor=fondo)
    plt.close(fig)
    return salida.getvalue()


def mostrar_comparador_indicadores():
    """Muestra los indicadores y permite elegir un período de comparación."""
    st.subheader("📉 Comparador de Indicadores Económicos")
    st.caption(
        "Compara el comportamiento del USD, EUR, UF, IPC y cobre "
        "durante un mismo período."
    )

    # Selección de indicadores; la comparación requiere al menos dos.
    indicadores_seleccionados = st.multiselect(
        "Indicadores que deseas comparar",
        options=["USD", "EUR", "UF", "IPC", "Cobre"],
        default=["USD", "Cobre"],
        help="Selecciona entre 2 y 5 indicadores. Si incluyes IPC, la comparación será mensual para todos.",
        key="comparador_indicadores_seleccionados",
    )

    if len(indicadores_seleccionados) < 2:
        st.warning("Selecciona al menos dos indicadores para compararlos.")
    else:
        st.success(
            "Indicadores seleccionados: "
            + ", ".join(indicadores_seleccionados)
        )

    # Selector de período compartido por todos los indicadores.
    st.markdown("#### Período de comparación")
    opciones = [
        "Últimos 30 días",
        "Últimos 90 días",
        "Últimos 6 meses",
        "Últimos 12 meses",
        "Año calendario",
        "Período personalizado",
    ]
    # Al incorporar IPC, proponer un período mensual suficientemente amplio.
    # No sobrescribir períodos que el usuario haya elegido expresamente.
    ipc_actual = "IPC" in indicadores_seleccionados
    ipc_anterior = st.session_state.get("comparador_ipc_anterior", False)
    clave_periodo = "comparador_periodo_historico"
    if clave_periodo not in st.session_state:
        st.session_state[clave_periodo] = (
            "Últimos 12 meses" if ipc_actual else "Últimos 30 días"
        )
    elif ipc_actual and not ipc_anterior and st.session_state[clave_periodo] == "Últimos 30 días":
        st.session_state[clave_periodo] = "Últimos 12 meses"
    st.session_state["comparador_ipc_anterior"] = ipc_actual

    periodo = st.selectbox(
        "Selecciona el período histórico",
        options=opciones,
        key=clave_periodo,
    )

    hoy = date.today()
    fecha_fin = hoy
    if periodo == "Últimos 30 días":
        fecha_inicio = hoy - timedelta(days=30)
    elif periodo == "Últimos 90 días":
        fecha_inicio = hoy - timedelta(days=90)
    elif periodo == "Últimos 6 meses":
        fecha_inicio = restar_meses(hoy, 6)
    elif periodo == "Últimos 12 meses":
        fecha_inicio = restar_meses(hoy, 12)
    elif periodo == "Año calendario":
        anio = st.selectbox(
            "Año que deseas analizar",
            options=list(range(hoy.year, hoy.year - 11, -1)),
            key="comparador_anio_calendario",
        )
        fecha_inicio = date(anio, 1, 1)
        fecha_fin = min(date(anio, 12, 31), hoy)
    else:
        col_inicio, col_fin = st.columns(2)
        with col_inicio:
            fecha_inicio = st.date_input(
                "Fecha inicial",
                value=hoy - timedelta(days=90),
                max_value=hoy,
                format="DD/MM/YYYY",
                key="comparador_fecha_inicio",
            )
        with col_fin:
            fecha_fin = st.date_input(
                "Fecha final",
                value=hoy,
                max_value=hoy,
                format="DD/MM/YYYY",
                key="comparador_fecha_fin",
            )

    if fecha_inicio > fecha_fin:
        st.error("La fecha inicial no puede ser posterior a la fecha final.")
    else:
        st.info(
            f"Período seleccionado: {fecha_inicio:%d-%m-%Y} "
            f"al {fecha_fin:%d-%m-%Y}."
        )
        # Los indicadores diarios se mantienen sin cambios; con IPC se usa escala mensual.
        if len(indicadores_seleccionados) >= 2:
            incluir_ipc = "IPC" in indicadores_seleccionados
            if incluir_ipc:
                st.caption(
                    "El IPC se publica mensualmente. Para compararlo sin inventar datos "
                    "diarios, todos los indicadores se representarán por mes: "
                    "último valor disponible del mes para USD, EUR, UF y cobre; "
                    "índice mensual oficial para IPC."
                )
                try:
                    columnas = {"USD": "USD", "EUR": "EUR", "UF": "UF", "IPC": "INDICE", "Cobre": "COBRE_USD_LIBRA"}
                    unidades = {"USD": "CLP/USD", "EUR": "CLP/EUR", "UF": "CLP/UF", "IPC": "puntos (base 2023=100)", "Cobre": "USD/libra"}
                    decimales = {"USD": 2, "EUR": 2, "UF": 2, "IPC": 2, "Cobre": 4}

                    with st.spinner("Consultando series históricas del Banco Central..."):
                        series = []
                        seleccion_monedas = [i for i in indicadores_seleccionados if i in ("USD", "EUR", "UF")]
                        if seleccion_monedas:
                            monedas = consultar_monedas(fecha_inicio, fecha_fin)
                            faltantes = [i for i in seleccion_monedas if i not in monedas.columns]
                            if faltantes:
                                raise ValueError("La consulta de monedas no contiene: " + ", ".join(faltantes))
                            series.append(monedas[seleccion_monedas].copy())
                        if "Cobre" in indicadores_seleccionados:
                            cobre = consultar_cobre(fecha_inicio, fecha_fin)
                            if "COBRE_USD_LIBRA" not in cobre.columns:
                                raise ValueError("La consulta de cobre no contiene COBRE_USD_LIBRA.")
                            series.append(cobre[["COBRE_USD_LIBRA"]].copy())

                    # Primero alinear las cotizaciones diarias por fechas reales comunes.
                    if series:
                        for serie in series:
                            serie.index = pd.to_datetime(serie.index).normalize()
                        diarios = pd.concat(series, axis=1, join="inner").sort_index()
                        diarios = diarios.loc[~diarios.index.duplicated(keep="last")]
                        diarios = diarios.apply(pd.to_numeric, errors="coerce")
                        diarios = diarios.replace([float("inf"), float("-inf")], float("nan"))
                        diarios = diarios.dropna()
                        diarios = diarios[(diarios > 0).all(axis=1)]
                    else:
                        diarios = pd.DataFrame()

                    if incluir_ipc:
                        # Agrupar las cotizaciones por mes; cada mes usa su último
                        # día con cotizaciones comunes dentro del período solicitado.
                        if not diarios.empty:
                            diarios_mensuales = diarios.groupby(diarios.index.to_period("M")).last()
                        else:
                            diarios_mensuales = pd.DataFrame()

                        # El Banco Central entrega el IPC con frecuencia mensual.
                        # Consultamos desde el primer día del mes inicial para no
                        # excluir su observación por la fecha exacta del índice.
                        inicio_ipc = fecha_inicio.replace(day=1)
                        ipc = consultar_ipc(inicio_ipc, fecha_fin)
                        if "INDICE" not in ipc.columns:
                            raise ValueError("La consulta de IPC no contiene INDICE.")
                        ipc = ipc[["INDICE"]].copy()
                        ipc.index = pd.to_datetime(ipc.index).to_period("M")
                        ipc = ipc.loc[~ipc.index.duplicated(keep="last")].sort_index()
                        ipc["INDICE"] = pd.to_numeric(ipc["INDICE"], errors="coerce")
                        ipc = ipc.replace([float("inf"), float("-inf")], float("nan"))
                        ipc = ipc.dropna()
                        ipc = ipc[ipc["INDICE"] > 0]

                        # Solo meses con observaciones de TODOS los indicadores.
                        comparacion = pd.concat([diarios_mensuales, ipc], axis=1, join="inner")
                        comparacion = comparacion.sort_index()
                        comparacion = comparacion.loc[
                            (comparacion.index >= pd.Period(fecha_inicio, freq="M"))
                            & (comparacion.index <= pd.Period(fecha_fin, freq="M"))
                        ]
                    else:
                        comparacion = diarios

                    columnas_elegidas = [columnas[i] for i in indicadores_seleccionados]
                    comparacion = comparacion.reindex(columns=columnas_elegidas)
                    comparacion = comparacion.apply(pd.to_numeric, errors="coerce")
                    comparacion = comparacion.replace([float("inf"), float("-inf")], float("nan"))
                    comparacion = comparacion.dropna(subset=columnas_elegidas)
                    comparacion = comparacion[(comparacion[columnas_elegidas] > 0).all(axis=1)]

                    # Fechas de visualización: mes de referencia para IPC,
                    # fecha diaria real cuando IPC no está seleccionado.
                    if incluir_ipc:
                        fechas_grafico = comparacion.index.to_timestamp(how="end").normalize()
                    else:
                        fechas_grafico = comparacion.index

                    if len(comparacion) < 2:
                        if incluir_ipc:
                            st.warning(
                                "La comparación con IPC necesita al menos dos meses con datos "
                                "disponibles para todos los indicadores. "
                                "Prueba con «Últimos 12 meses», «Año calendario» o un período "
                                "personalizado más amplio. El IPC se publica mensualmente."
                            )
                        else:
                            st.warning(
                                "No hay suficientes fechas comunes con datos válidos para "
                                "los indicadores seleccionados en este período. "
                                "Prueba con un período más amplio."
                            )
                    else:
                        # Normalizar cada indicador a 0 % en la primera fecha común.
                        variaciones = pd.DataFrame(index=comparacion.index)
                        for indicador in indicadores_seleccionados:
                            columna = columnas[indicador]
                            variaciones[indicador] = (
                                comparacion[columna] / comparacion[columna].iloc[0] - 1
                            ) * 100

                        st.markdown("#### Evolución comparativa: " + " vs. ".join(indicadores_seleccionados))
                        st.caption(
                            ("Variación acumulada desde el primer mes común. " if incluir_ipc
                             else "Variación acumulada respecto al primer día con datos comunes. ")
                            + "Todos los indicadores parten de 0 % para comparar su evolución "
                            "porcentual desde una misma fecha. Esto no significa que sus valores "
                            "originales sean cero. Los precios y valores reales se presentan "
                            "en la tabla inferior."
                        )
                        columnas_metricas = st.columns(len(indicadores_seleccionados))
                        for columna_ui, indicador in zip(columnas_metricas, indicadores_seleccionados):
                            columna_ui.metric(
                                f"Variación {indicador}",
                                f"{variaciones[indicador].iloc[-1]:+.2f}%",
                            )

                        figura = go.Figure()
                        for indicador in indicadores_seleccionados:
                            figura.add_trace(
                                go.Scatter(
                                    x=fechas_grafico,
                                    y=variaciones[indicador],
                                    mode="lines",
                                    name=indicador,
                                    hovertemplate=(
                                        "%{x|%d-%m-%Y}<br>" + indicador + ": %{y:+.2f}%<extra></extra>"
                                    ),
                                )
                            )
                        figura.add_hline(y=0, line_dash="dash", line_color="gray")
                        figura.update_layout(
                            xaxis_title="Fecha",
                            yaxis_title="Variación desde el inicio (%)",
                            hovermode="x unified",
                            legend_title_text="Indicador",
                            margin=dict(l=20, r=20, t=20, b=20),
                        )
                        # En comparaciones mensuales de hasta 12 meses, mostrar
                        # explícitamente cada mes en el eje horizontal.
                        # Las comparaciones diarias conservan el eje automático.
                        if incluir_ipc and len(comparacion) <= 12:
                            nombres_meses = [
                                "Ene", "Feb", "Mar", "Abr", "May", "Jun",
                                "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
                            ]
                            figura.update_xaxes(
                                tickmode="array",
                                tickvals=list(fechas_grafico),
                                ticktext=[
                                    f"{nombres_meses[mes.month - 1]} {mes.year}"
                                    for mes in comparacion.index
                                ],
                                tickangle=-35,
                            )
                        st.plotly_chart(figura, use_container_width=True)
                        st.caption(
                            (f"Meses comunes: {comparacion.index[0]} a "
                             f"{comparacion.index[-1]} ({len(comparacion)} meses). "
                             if incluir_ipc else
                             f"Período efectivo con datos comunes: "
                             f"{comparacion.index[0]:%d-%m-%Y} al "
                             f"{comparacion.index[-1]:%d-%m-%Y} "
                             f"({len(comparacion)} registros). ")
                            + "USD, EUR y UF en CLP por unidad; cobre en USD/libra. "
                            + ("IPC: índice mensual base 2023=100. Los valores de mercado "
                               "son el último registro diario común de cada mes dentro del período. "
                               if incluir_ipc else "")
                            + "Las variaciones no implican causalidad."
                        )

                        # Mostrar precios originales, extremos y variaciones para cada serie.
                        st.markdown("#### Resumen de valores del período")
                        filas_resumen = []
                        for indicador in indicadores_seleccionados:
                            serie = comparacion[columnas[indicador]]
                            fecha_min = serie.idxmin()
                            fecha_max = serie.idxmax()
                            precision = decimales[indicador]
                            unidad = unidades[indicador]

                            def formato_valor(numero):
                                return (
                                    f"{numero:,.{precision}f}"
                                    .replace(",", "§")
                                    .replace(".", ",")
                                    .replace("§", ".")
                                )

                            inicial = serie.iloc[0]
                            final = serie.iloc[-1]
                            variacion = (final / inicial - 1) * 100
                            filas_resumen.append({
                                "Indicador": indicador,
                                "Inicial": f"{formato_valor(inicial)} {unidad}",
                                "Final": f"{formato_valor(final)} {unidad}",
                                "Variación": f"{variacion:+.2f}%".replace(".", ","),
                                "Mínimo": f"{formato_valor(serie.loc[fecha_min])} {unidad}",
                                "Fecha mínimo": formato_fecha_resumen(fecha_min, incluir_ipc),
                                "Máximo": f"{formato_valor(serie.loc[fecha_max])} {unidad}",
                                "Fecha máximo": formato_fecha_resumen(fecha_max, incluir_ipc),
                            })

                        st.dataframe(pd.DataFrame(filas_resumen), use_container_width=True, hide_index=True)
                        st.caption(
                            "Los valores iniciales y finales corresponden al primer y último "
                            + ("mes común del gráfico; los mínimos y máximos corresponden "
                               "a los meses observados. " if incluir_ipc else
                               "registro común del gráfico; los mínimos y máximos son los valores "
                               "extremos observados entre esas fechas. ")
                            + "Todas las cifras usan los valores originales, no la escala porcentual del gráfico."
                        )

                        # Exportación profesional del mismo conjunto de datos del gráfico.
                        try:
                            archivo_excel = generar_excel_comparativo(
                                comparacion, variaciones, indicadores_seleccionados,
                                columnas, unidades, decimales, incluir_ipc,
                            )
                            st.download_button(
                                "📥 Descargar informe Excel",
                                data=archivo_excel,
                                file_name=f"Comparador_Indicadores_{fecha_inicio:%Y%m%d}_{fecha_fin:%Y%m%d}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="descargar_excel_comparador",
                            )
                        except ImportError:
                            st.warning("No se encontró openpyxl. Instálalo con: py -m pip install openpyxl")
                        except Exception as error_excel:
                            st.warning(f"No fue posible preparar el informe Excel: {error_excel}")

                        # Ficha PNG para compartir por correo o WhatsApp.
                        try:
                            ficha_png = generar_ficha_png_comparativa(
                                comparacion, variaciones, indicadores_seleccionados,
                                columnas, unidades, decimales, incluir_ipc,
                            )
                            st.download_button(
                                "🖼️ Descargar ficha resumen PNG",
                                data=ficha_png,
                                file_name=f"Ficha_Comparador_{fecha_inicio:%Y%m%d}_{fecha_fin:%Y%m%d}.png",
                                mime="image/png",
                                key="descargar_png_comparador",
                            )
                        except Exception as error_png:
                            st.warning(f"No fue posible preparar la ficha PNG: {error_png}")
                except Exception as error:
                    st.error("No fue posible consultar o comparar las series históricas.")
                    st.exception(error)
