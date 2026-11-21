"""Conversor individual y múltiple de monedas para Inteligencia Económica."""
import io
import math
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from PIL import Image, ImageDraw, ImageFont

from Inteligencia_Economica.Servicios.banco_central import consultar_monedas
from Inteligencia_Economica.Modulos.formatos import formato_moneda

MONEDAS = ["CLP", "USD", "EUR", "UF"]


def _numero(valor, decimales=2):
    return f"{valor:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")



def _leer_monto(texto):
    """Interpreta importes chilenos y entradas habituales sin perder decimales."""
    if isinstance(texto, (int, float)):
        numero = float(texto)
    else:
        limpio = str(texto or "").strip().replace(" ", "").replace("\u00a0", "")
        if not limpio:
            return 0.0
        if "," in limpio and "." in limpio:
            # El separador que aparece al final se considera decimal.
            decimal = "," if limpio.rfind(",") > limpio.rfind(".") else "."
            miles = "." if decimal == "," else ","
            limpio = limpio.replace(miles, "").replace(decimal, ".")
        elif "," in limpio:
            limpio = limpio.replace(",", ".")
        elif "." in limpio and limpio.count(".") > 1:
            limpio = limpio.replace(".", "")
        numero = float(limpio)
    if not math.isfinite(numero) or numero < 0:
        raise ValueError("El monto debe ser un número positivo o cero.")
    return numero


def _formatear_monto_texto(texto):
    try:
        return _numero(_leer_monto(texto))
    except (ValueError, TypeError):
        return str(texto)


def _normalizar_monto_individual():
    """Da formato chileno cuando el usuario confirma o abandona el campo."""
    st.session_state.conversor_monto_texto = _formatear_monto_texto(
        st.session_state.conversor_monto_texto
    )


def _normalizar_editor_montos():
    """Conserva todas las ediciones y actualiza la presentación de los montos."""
    clave = f"conversor_editor_{st.session_state.conversor_editor_version}"
    cambios = st.session_state.get(clave, {}).get("edited_rows", {})
    if not cambios:
        return
    datos = st.session_state.conversor_filas.copy()
    for indice, columnas in cambios.items():
        indice = int(indice)
        if indice >= len(datos):
            continue
        for columna, valor in columnas.items():
            if columna in datos.columns:
                datos.at[indice, columna] = (
                    _formatear_monto_texto(valor) if columna == "Monto" else valor
                )
    st.session_state.conversor_filas = datos
    st.session_state.conversor_editor_version += 1

def _fuente(tamano, negrita=False):
    rutas = (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]
             if negrita else ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"])
    for ruta in rutas:
        try:
            return ImageFont.truetype(ruta, tamano)
        except OSError:
            continue
    return ImageFont.load_default()


def _excel_conversion(filas, destino, fechas, modo, resumen_tasas=""):
    wb = Workbook()
    ws = wb.active
    ws.title = "Conversiones"
    ws.merge_cells("A1:E1")
    ws["A1"] = "CONVERSIÓN DE MONEDAS | HERRAMIENTAS DE COMPRAS"
    ws["A1"].font = Font(bold=True, color="FFFFFF", size=14)
    ws["A1"].fill = PatternFill("solid", fgColor="15243B")
    ws["A2"] = "Modalidad"
    ws["B2"] = modo
    ws["A3"] = "Destino"
    ws["B3"] = destino
    ws["A4"] = "Fechas de referencia"
    ws["B4"] = fechas or "Sin cotización externa (CLP)"
    ws.merge_cells("B4:E4")
    ws["A5"] = "Cotizaciones utilizadas"
    ws["B5"] = resumen_tasas or "Sin cotización externa"
    ws.merge_cells("B5:E5")
    headers = ["Detalle", "Monto origen", "Moneda origen", "Tipo de cambio (CLP)", f"Resultado ({destino})"]
    for col, titulo in enumerate(headers, 1):
        c = ws.cell(6, col, titulo)
        c.fill = PatternFill("solid", fgColor="203D58")
        c.font = Font(color="FFFFFF", bold=True)
        c.alignment = Alignment(wrap_text=True)
    for n, fila in enumerate(filas, 7):
        ws.cell(n, 1, fila["Detalle"])
        ws.cell(n, 2, fila["Monto"])
        ws.cell(n, 3, fila["Moneda"])
        ws.cell(n, 4, fila["Tipo de cambio (CLP)"])
        ws.cell(n, 5, fila["Resultado"])
        for col in (2, 4, 5):
            ws.cell(n, col).number_format = '#,##0.00;[Red]-#,##0.00'
    fila_total = 7 + len(filas)
    ws.cell(fila_total, 4, "TOTAL")
    ws.cell(fila_total, 5, sum(f["Resultado"] for f in filas))
    for col in (4, 5):
        ws.cell(fila_total, col).font = Font(bold=True, color="FFFFFF")
        ws.cell(fila_total, col).fill = PatternFill("solid", fgColor="087F8C")
    ws.cell(fila_total, 5).number_format = '#,##0.00;[Red]-#,##0.00'
    ws.merge_cells(start_row=fila_total + 2, start_column=1, end_row=fila_total + 2, end_column=5)
    ws.cell(fila_total + 2, 1, "Valores referenciales; pueden diferir de los tipos de cambio comerciales.")
    for col, ancho in enumerate([32, 21, 20, 27, 25], 1):
        ws.column_dimensions[get_column_letter(col)].width = ancho
    ws.freeze_panes = "A7"
    ws.auto_filter.ref = f"A6:E{fila_total-1}"
    archivo = io.BytesIO()
    wb.save(archivo)
    return archivo.getvalue()


def _imagen_conversion(filas, destino, fechas, modo, resumen_tasas=""):
    # Tarjeta PNG dinámica: crece según la cantidad de filas.
    alto = 270 + len(filas) * 49 + 154
    ancho = 1120
    img = Image.new("RGB", (ancho, alto), "#FFFFFF")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, ancho, 106), fill="#14243A")
    d.text((42, 22), "CONVERSIÓN DE MONEDAS", font=_fuente(30, True), fill="#FFFFFF")
    d.text((42, 69), f"{modo}  |  Destino: {destino}", font=_fuente(17), fill="#B9D1E0")
    d.text((42, 128), "Detalle", font=_fuente(19, True), fill="#24364C")
    d.text((465, 128), "Monto origen", font=_fuente(19, True), fill="#24364C")
    d.text((770, 128), f"Resultado ({destino})", font=_fuente(19, True), fill="#24364C")
    d.line((42, 163, 1078, 163), fill="#D4E0E7", width=2)
    for i, fila in enumerate(filas):
        y = 182 + i * 49
        if i % 2 == 0:
            d.rounded_rectangle((34, y - 7, 1086, y + 36), radius=7, fill="#F0F5F8")
        detalle = str(fila["Detalle"])[:32]
        d.text((45, y), detalle, font=_fuente(17), fill="#20364D")
        d.text((465, y), f'{_numero(fila["Monto"])} {fila["Moneda"]}', font=_fuente(17), fill="#20364D")
        d.text((770, y), _numero(fila["Resultado"]), font=_fuente(18, True), fill="#087F8C")
    y_total = 195 + len(filas) * 49
    d.rounded_rectangle((34, y_total, 1086, y_total + 74), radius=12, fill="#E1F3F2")
    d.text((48, y_total + 21), "TOTAL CONVERTIDO", font=_fuente(21, True), fill="#13505B")
    total = sum(f["Resultado"] for f in filas)
    d.text((610, y_total + 21), f"{_numero(total)} {destino}", font=_fuente(22, True), fill="#13505B")
    pie = f"Referencia: {fechas or 'CLP'}"
    d.text((42, y_total + 95), pie[:110], font=_fuente(15), fill="#536B7B")
    d.text((42, y_total + 119), f"Tasas (CLP por unidad): {resumen_tasas or 'No aplica'}"[:110], font=_fuente(14), fill="#536B7B")
    d.text((42, y_total + 145), "Valores referenciales; no constituyen cotización comercial.", font=_fuente(14), fill="#536B7B")
    salida = io.BytesIO()
    img.save(salida, format="PNG")
    return salida.getvalue()


def mostrar_conversor(indicadores):
    st.subheader("💱 Conversor de Monedas")
    st.caption("Convierte montos entre CLP, USD, EUR y UF con cotizaciones actuales, históricas o ingresadas manualmente.")

    modo_conversion = st.radio("Fuente del tipo de cambio", ["Últimos valores disponibles", "Fecha histórica", "Tipo de cambio manual"], horizontal=True, key="modo_conversion")
    st.caption("Automático: última cotización publicada. Histórico: cotización de una fecha. Manual: ingresa tus propias tasas, sin consultar la API desde este conversor.")
    fecha_conversion = None
    buscar_anterior = False
    if modo_conversion == "Fecha histórica":
        fecha_conversion = st.date_input("Selecciona la fecha de conversión", value=date.today(), max_value=date.today(), format="DD/MM/YYYY", key="fecha_conversion")
        buscar_anterior = st.checkbox("Utilizar el último valor disponible anterior si no existe cotización en la fecha seleccionada", value=False, key="buscar_cotizacion_anterior")

    modalidad = st.radio("Modalidad", ["Conversión individual", "Conversión múltiple"], horizontal=True, key="conversor_modalidad")
    tasas = {"CLP": 1.0}
    fechas_tasas = {}
    indicadores_conversion = indicadores or {}
    if modo_conversion == "Tipo de cambio manual":
        st.info("Modo manual: ingresa cuánto vale **1 unidad** de cada moneda en pesos chilenos (CLP). Solo necesitas completar las monedas que utilizarás. CLP siempre equivale a 1.")
        columnas_manual = st.columns(3)
        for columna, codigo in zip(columnas_manual, ["USD", "EUR", "UF"]):
            with columna:
                valor_manual = st.number_input(
                    f"1 {codigo} = CLP", min_value=0.0, value=0.0,
                    step=1.0, format="%.4f", key=f"conversor_manual_{codigo}",
                    help="Introduce un valor positivo. Cero significa que esta moneda no está configurada.",
                )
                if math.isfinite(valor_manual) and valor_manual > 0:
                    tasas[codigo] = float(valor_manual)
        st.caption("Las cotizaciones manuales se aplican tanto a la conversión individual como a la múltiple y quedarán identificadas en las exportaciones.")
        indicadores_conversion = {}
    elif modo_conversion == "Fecha histórica":
        try:
            fecha_inicio = fecha_conversion - timedelta(days=10) if buscar_anterior else fecha_conversion
            datos_fecha = consultar_monedas(fecha_inicio, fecha_conversion)
            indicadores_conversion = {}
            for codigo in ["USD", "EUR", "UF"]:
                if codigo not in datos_fecha:
                    continue
                valores = datos_fecha[codigo].dropna()
                if not buscar_anterior:
                    valores = valores[valores.index.date == fecha_conversion]
                valores = valores[pd.to_numeric(valores, errors="coerce").gt(0)]
                if not valores.empty:
                    indicadores_conversion[codigo] = {"valor": float(valores.iloc[-1]), "fecha": valores.index[-1].date()}
            if not indicadores_conversion:
                st.warning("No existen valores publicados para la fecha seleccionada.")
        except Exception as error:
            indicadores_conversion = {}
            st.error(f"No fue posible consultar la fecha: {error}")

    for codigo in ([] if modo_conversion == "Tipo de cambio manual" else ["USD", "EUR", "UF"]):
        info = indicadores_conversion.get(codigo)
        if not info:
            continue
        try:
            valor = float(info["valor"])
            if math.isfinite(valor) and valor > 0:
                tasas[codigo] = valor
                fechas_tasas[codigo] = info["fecha"]
        except (TypeError, ValueError, KeyError):
            continue

    filas = []
    if modalidad == "Conversión individual":
        col_monto, col_origen, col_destino = st.columns(3)
        with col_monto:
            if "conversor_monto_texto" not in st.session_state:
                st.session_state.conversor_monto_texto = "0,00"
            texto_monto = st.text_input(
                "Monto a convertir", key="conversor_monto_texto",
                on_change=_normalizar_monto_individual,
                help="Ejemplo: 1250000,50. Al confirmar se mostrará 1.250.000,50.",
            )
            try:
                monto = _leer_monto(texto_monto)
            except (ValueError, TypeError):
                monto = None
                st.warning("Ingresa un monto válido, por ejemplo 1.250.000,50.")
        with col_origen:
            origen = st.selectbox("Moneda de origen", MONEDAS, index=1, key="conversor_origen")
        with col_destino:
            destino = st.selectbox("Moneda de destino", MONEDAS, index=0, key="conversor_destino")
        entradas = [{"Detalle": "Conversión individual", "Monto": monto, "Moneda": origen}]
    else:
        destino = st.selectbox("Moneda de destino común", MONEDAS, index=0, key="conversor_destino_multiple")
        st.caption("Agrega o elimina filas en la tabla. Selecciona la moneda de origen de cada monto; la moneda comienza en «Seleccionar moneda». El detalle es opcional.")
        # Una fila inicial vacía, sin importes de ejemplo.
        if "conversor_filas" not in st.session_state:
            st.session_state.conversor_filas = pd.DataFrame([
                {"Eliminar": False, "Detalle": "", "Monto": "0,00", "Moneda": "Seleccionar moneda"}
            ])
        if "conversor_editor_version" not in st.session_state:
            st.session_state.conversor_editor_version = 0

        # Convertir los montos anteriores (numéricos) a texto formateado.
        st.session_state.conversor_filas["Monto"] = st.session_state.conversor_filas["Monto"].map(
            _formatear_monto_texto
        )
        editadas = st.data_editor(
            st.session_state.conversor_filas,
            num_rows="fixed", hide_index=True, use_container_width=True,
            column_config={
                "Eliminar": st.column_config.CheckboxColumn("Eliminar", help="Marca las filas que quieras eliminar"),
                "Detalle": st.column_config.TextColumn("Detalle / referencia", help="Descripción opcional del monto"),
                "Monto": st.column_config.TextColumn("Monto", required=True, help="Ejemplo: 1.250.000,50"),
                "Moneda": st.column_config.SelectboxColumn("Moneda origen", options=["Seleccionar moneda"] + MONEDAS, required=True, help="Selecciona la moneda antes de convertir. Las filas sin moneda no se incluyen en el total."),
            },
            key=f"conversor_editor_{st.session_state.conversor_editor_version}",
            on_change=_normalizar_editor_montos,
        )
        boton_agregar, boton_eliminar = st.columns(2)
        with boton_agregar:
            agregar = st.button("➕ Agregar monto", use_container_width=True)
        with boton_eliminar:
            eliminar = st.button("🗑️ Eliminar seleccionados", use_container_width=True)
        if agregar or eliminar:
            actualizadas = editadas.copy()
            if eliminar:
                actualizadas = actualizadas.loc[~actualizadas["Eliminar"].fillna(False)].copy()
                if actualizadas.empty:
                    actualizadas = pd.DataFrame([
                        {"Eliminar": False, "Detalle": "", "Monto": "0,00", "Moneda": "Seleccionar moneda"}
                    ])
            else:
                actualizadas = pd.concat([
                    actualizadas,
                    pd.DataFrame([{"Eliminar": False, "Detalle": "", "Monto": "0,00", "Moneda": "Seleccionar moneda"}])
                ], ignore_index=True)
            actualizadas["Eliminar"] = False
            st.session_state.conversor_filas = actualizadas.reset_index(drop=True)
            st.session_state.conversor_editor_version += 1
            st.rerun()
        entradas = editadas.drop(columns=["Eliminar"]).to_dict("records")

    invalidas = []
    pendientes_moneda = []
    for i, entrada in enumerate(entradas, 1):
        origen = entrada.get("Moneda")
        monto = entrada.get("Monto")
        # Una fila nueva sin moneda y sin monto no es un error: espera la selección del usuario.
        if modalidad == "Conversión múltiple" and (origen is None or pd.isna(origen) or origen in ("", "Seleccionar moneda")) and (monto is None or pd.isna(monto) or str(monto).strip() in ("", "0", "0,00", "0.00")):
            continue
        # Una moneda pendiente de selección es un dato incompleto, no un fallo de la API.
        if modalidad == "Conversión múltiple" and (origen is None or pd.isna(origen) or origen in ("", "Seleccionar moneda")):
            pendientes_moneda.append(i)
            continue
        if origen not in MONEDAS or monto is None or pd.isna(monto):
            invalidas.append(i)
            continue
        try:
            monto = _leer_monto(monto)
        except (TypeError, ValueError):
            invalidas.append(i)
            continue
        if not math.isfinite(monto) or monto < 0:
            invalidas.append(i)
            continue
        if origen not in tasas or destino not in tasas:
            invalidas.append(i)
            continue
        filas.append({"Detalle": str(entrada.get("Detalle") or f"Monto {i}"), "Monto": monto,
                      "Moneda": origen, "Tipo de cambio (CLP)": tasas[origen],
                      "Resultado": monto * tasas[origen] / tasas[destino]})

    if pendientes_moneda:
        numero_filas = ", ".join(map(str, pendientes_moneda))
        st.info(f"Selecciona la moneda de origen de la(s) fila(s) {numero_filas} para completar la conversión.")
    if invalidas:
        st.warning(f"No se pudieron convertir las filas {', '.join(map(str, invalidas))}. Revisa sus datos o la disponibilidad de cotizaciones.")
    if not filas:
        # Evitar duplicar el mensaje cuando ya hay montos sin moneda seleccionada.
        if not pendientes_moneda and not invalidas:
            st.info("Selecciona una moneda de origen e ingresa un monto para comenzar la conversión.")
        return

    if modalidad == "Conversión individual":
        resultado = filas[0]["Resultado"]
        decimales = 6 if resultado != 0 and abs(resultado) < 0.01 else 2
        st.metric("Resultado de la conversión", f"{_numero(resultado, decimales)} {destino}")
        tasa_conversion = tasas[filas[0]["Moneda"]] / tasas[destino]
        decimales_tasa = 6 if tasa_conversion < 0.01 else 2
        st.caption(f'1 {filas[0]["Moneda"]} = {_numero(tasa_conversion, decimales_tasa)} {destino}')
    else:
        tabla = pd.DataFrame([{"Detalle": f["Detalle"], "Monto origen": _numero(f["Monto"]),
                               "Moneda": f["Moneda"], "Tipo de cambio (CLP)": _numero(f["Tipo de cambio (CLP)"]),
                               f"Resultado ({destino})": _numero(f["Resultado"])} for f in filas])
        st.dataframe(tabla, use_container_width=True, hide_index=True)
        st.metric(f"Total convertido ({destino})", _numero(sum(f["Resultado"] for f in filas)))
        if invalidas or pendientes_moneda:
            st.caption("El total considera solamente las filas convertidas correctamente.")

    fechas_usadas = {fechas_tasas[c] for f in filas for c in (f["Moneda"], destino) if c in fechas_tasas}
    fechas = ", ".join(f.strftime("%d-%m-%Y") for f in sorted(fechas_usadas))
    if fechas:
        st.caption(f"Fecha(s) de referencia: {fechas}")
    elif modo_conversion == "Tipo de cambio manual":
        st.caption("Fuente: tipos de cambio ingresados manualmente por el usuario.")
    else:
        st.caption("No se utilizaron cotizaciones externas (solo CLP).")
    monedas_usadas = {c for f in filas for c in (f["Moneda"], destino) if c != "CLP"}
    resumen_tasas = " | ".join(f"1 {c} = {_numero(tasas[c], 4)} CLP" for c in ["USD", "EUR", "UF"] if c in monedas_usadas and c in tasas)
    if resumen_tasas:
        st.caption(f"Cotizaciones utilizadas: {resumen_tasas}")
    referencia_exportacion = fechas if modo_conversion != "Tipo de cambio manual" else "Ingresado manualmente por el usuario"
    st.caption("Conversión referencial. Los valores pueden diferir de los tipos de cambio comerciales.")

    st.markdown("#### Exportar resultados")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📊 Descargar Excel", data=_excel_conversion(filas, destino, referencia_exportacion, modo_conversion, resumen_tasas),
                           file_name="Conversion_Monedas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True, key="conversor_excel")
    with c2:
        st.download_button("🖼️ Descargar tarjeta PNG", data=_imagen_conversion(filas, destino, referencia_exportacion, modo_conversion, resumen_tasas),
                           file_name="Conversion_Monedas.png", mime="image/png", use_container_width=True, key="conversor_png")
