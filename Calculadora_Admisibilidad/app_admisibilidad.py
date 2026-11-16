import streamlit as st

from Calculadora_Admisibilidad.Servicios.tipo_cambio import (
    obtener_dolar_observado,
    obtener_tipo_cambio_eur_usd,
    obtener_uf_y_dolar,
    obtener_cotizaciones_monedas,
)

from Calculadora_Admisibilidad.Calculos.admisibilidad import (
    convertir_a_usd,
    convertir_moneda,
    obtener_porcentaje,
    calcular_limites,
    calcular_desviacion,
    calcular_exceso,
    calcular_descuento_requerido,
    calcular_diferencia_inferior,
)

# Generador de imagen PNG para compartir la tabla.
from Calculadora_Admisibilidad.Reportes.imagen_admisibilidad import (
    generar_imagen_admisibilidad,
)

from Calculadora_Admisibilidad.Reportes.excel_admisibilidad import (
    generar_excel_admisibilidad,
)

def formato_chileno(numero, decimales=0):
    numero_formateado = f"{numero:,.{decimales}f}"
    return numero_formateado.replace(",", "X").replace(".", ",").replace("X", ".")


def mostrar_calculadora(modo_fijo=None):
    """Calculadora de admisibilidad para una oferta individual.

    Se conserva modo_fijo por compatibilidad con el menú existente.
    """
    st.markdown(
        """
<div style="margin-bottom: 24px;">
    <div style="color: #56D8CC; font-size: 12px; font-weight: 700; letter-spacing: 1.5px; margin-bottom: 8px;">
        EVALUACIÓN ECONÓMICA
    </div>
    <div style="color: #FFFFFF; font-size: 26px; font-weight: 700; margin-bottom: 8px;">
        Calculadora de Admisibilidad
    </div>
    <div style="color: #A9BED0; font-size: 14px;">
        Análisis de admisibilidad económica de una oferta
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div style="margin: 18px 0 18px 0; padding: 16px 20px; background: #14243A; border-left: 3px solid #56D8CC; border-radius: 8px;">
    <div style="color: #56D8CC; font-size: 11px; font-weight: 700; letter-spacing: 1.5px;">
        01 / CONFIGURACIÓN DE LA EVALUACIÓN
    </div>
    <div style="color: #DCE7F2; font-size: 13px; margin-top: 6px;">
        Registre los antecedentes económicos de la solicitud y la oferta recibida.
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    col_moneda, col_monto = st.columns(2)
    with col_moneda:
        moneda = st.selectbox("Moneda de la solicitud", ["CLP", "USD", "EUR", "UF"])
    with col_monto:
        monto = st.number_input("Monto de la solicitud", min_value=0.0)
        
    # ============================================================
    # DATOS ECONÓMICOS DE LA OFERTA
    # ============================================================
    # La solicitud y la oferta pueden estar expresadas
    # en monedas diferentes.
    # ============================================================

    col_moneda_oferta, col_monto_oferta = st.columns(2)

    with col_moneda_oferta:
        moneda_oferta = st.selectbox(
            "Moneda de la oferta",
            ["CLP", "USD", "EUR", "UF"],
            index=["CLP", "USD", "EUR", "UF"].index(moneda)
        )

    with col_monto_oferta:
        oferta = st.number_input(
            "Monto de la oferta recibida",
            min_value=0.0
        )

    # ============================================================
    # COTIZACIONES DEL BANCO CENTRAL DE CHILE
    # ============================================================
    # Se identifican las monedas necesarias para evaluar
    # la solicitud y convertir la oferta a la misma moneda.
    # También se considera USD para determinar el porcentaje
    # de admisibilidad correspondiente.
    # ============================================================

    monedas_utilizadas = {moneda, moneda_oferta, "USD"}

    # Inicializar cotizaciones y fecha de referencia.
    dolar_clp = 0.0
    euro_usd = 0.0
    valor_uf = 0.0
    fecha_cotizacion = None

    # Consultar las cotizaciones del Banco Central.
    try:
        (
            dolar_clp,
            euro_usd,
            valor_uf,
            fecha_cotizacion
        ) = obtener_cotizaciones_monedas()

    except Exception:
        st.warning(
            "No fue posible obtener las cotizaciones del Banco Central. "
            "Ingrese manualmente los valores necesarios."
        )

    # Mostrar la fecha de las cotizaciones automáticas.
    if fecha_cotizacion is not None:
        st.caption(
            f"Cotizaciones Banco Central de Chile - "
            f"Fecha: {fecha_cotizacion:%d-%m-%Y}"
        )

    # ============================================================
    # TIPOS DE CAMBIO EDITABLES
    # ============================================================
    # Se muestran únicamente las cotizaciones necesarias
    # para las monedas seleccionadas.
    # ============================================================

    if "CLP" in monedas_utilizadas or "UF" in monedas_utilizadas:
        dolar_clp = st.number_input(
            "Dólar observado (1 USD en CLP)",
            min_value=0.0,
            value=float(dolar_clp),
            format="%.4f"
        )

    if "EUR" in monedas_utilizadas:
        euro_usd = st.number_input(
            "Tipo de cambio EUR/USD (1 EUR en USD)",
            min_value=0.0,
            value=float(euro_usd),
            format="%.6f"
        )

    if "UF" in monedas_utilizadas:
        valor_uf = st.number_input(
            "Valor UF en CLP",
            min_value=0.0,
            value=float(valor_uf),
            format="%.4f"
        )

    # ============================================================
    # TABLA DE REFERENCIA DE ADMISIBILIDAD
    # ============================================================
    # Muestra los tramos y porcentajes establecidos.
    # La tabla permanece oculta hasta que el usuario la despliega.
    # ============================================================

    with st.expander("📋 Ver tabla de porcentajes de admisibilidad"):

        tabla_admisibilidad = [
            {"Monto de solicitud (USD)": "Hasta 500", "Admisibilidad": "±40%"},
            {"Monto de solicitud (USD)": "Más de 500 hasta 1.000", "Admisibilidad": "±30%"},
            {"Monto de solicitud (USD)": "Más de 1.000 hasta 5.000", "Admisibilidad": "±20%"},
            {"Monto de solicitud (USD)": "Más de 5.000 hasta 10.000", "Admisibilidad": "±10%"},
            {"Monto de solicitud (USD)": "Más de 10.000 hasta 30.000", "Admisibilidad": "±7%"},
            {"Monto de solicitud (USD)": "Más de 30.000 hasta 50.000", "Admisibilidad": "±5%"},
            {"Monto de solicitud (USD)": "Más de 50.000 hasta 1.000.000", "Admisibilidad": "±3%"},
            {"Monto de solicitud (USD)": "Más de 1.000.000 hasta 5.000.000", "Admisibilidad": "±2%"},
            {"Monto de solicitud (USD)": "Más de 5.000.000", "Admisibilidad": "±1%"},
        ]

        st.dataframe(
            tabla_admisibilidad,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "El porcentaje aplicable se determina según el monto "
            "de la solicitud expresado en USD."
        )
        
        # ====================================================
        # COPIAR TABLA DE ADMISIBILIDAD
        # ====================================================
        # Presenta los tramos en formato de texto para
        # copiarlos y compartirlos por correo o WhatsApp.
        # ====================================================
        
        with st.popover("📋 Copiar tabla de admisibilidad"):
    
            texto_tabla = (
                "TABLA DE ADMISIBILIDAD\n"
                "Monto de solicitud (USD) | Admisibilidad\n"
                "Hasta 500 | ±40%\n"
                "Más de 500 hasta 1.000 | ±30%\n"
                "Más de 1.000 hasta 5.000 | ±20%\n"
                "Más de 5.000 hasta 10.000 | ±10%\n"
                "Más de 10.000 hasta 30.000 | ±7%\n"
                "Más de 30.000 hasta 50.000 | ±5%\n"
                "Más de 50.000 hasta 1.000.000 | ±3%\n"
                "Más de 1.000.000 hasta 5.000.000 | ±2%\n"
                "Más de 5.000.000 | ±1%\n"
                "\n"
                "El porcentaje aplicable se determina según "
                "el monto de la solicitud expresado en USD."
            )
            
            # Mostrar el texto con opción de copiar.
            st.code(texto_tabla, language=None)
            
        # ====================================================
        # DESCARGAR TARJETA DE ADMISIBILIDAD EN PNG
        # ====================================================
        # Genera una imagen compacta para compartir por WhatsApp.
        # ====================================================

        imagen_png = generar_imagen_admisibilidad(tabla_admisibilidad)

        st.download_button(
            label="🖼️ Descargar tarjeta PNG",
            data=imagen_png,
            file_name="Tabla_Admisibilidad.png",
            mime="image/png",
            use_container_width=False,
        )

    calcular = st.button(
        "Calcular admisibilidad",
        type="primary",
        icon=":material/calculate:",
        use_container_width=True,
    )
    

    if not calcular:
        return

    if monto <= 0:
        st.warning("Debes ingresar un monto de solicitud mayor a 0.")
        st.stop()
        
    # ============================================================
    # VALIDACIÓN DE LAS COTIZACIONES NECESARIAS
    # ============================================================
    # Se comprueba que las tasas utilizadas sean mayores a cero.
    # ============================================================

    if ("CLP" in monedas_utilizadas or "UF" in monedas_utilizadas) and dolar_clp <= 0:
        st.warning("Debes ingresar un valor del dólar mayor a 0.")
        st.stop()

    if "EUR" in monedas_utilizadas and euro_usd <= 0:
        st.warning("Debes ingresar un tipo de cambio EUR/USD mayor a 0.")
        st.stop()

    if "UF" in monedas_utilizadas and valor_uf <= 0:
        st.warning("Debes ingresar un valor UF mayor a 0.")
        st.stop()

    # ============================================================
    # CONVERSIÓN Y CÁLCULO DE ADMISIBILIDAD
    # ============================================================
    # La solicitud se convierte a USD para determinar
    # el porcentaje de admisibilidad correspondiente.
    # La oferta se convierte a la moneda de la solicitud.
    # ============================================================

    monto_usd = convertir_moneda(
        monto, moneda, "USD",
        dolar_clp, euro_usd, valor_uf
    )

    oferta_convertida = convertir_moneda(
        oferta, moneda_oferta, moneda,
        dolar_clp, euro_usd, valor_uf
    )

    porcentaje = obtener_porcentaje(monto_usd)

    limite_inferior, limite_superior = calcular_limites(
        monto, porcentaje
    )
    
    simbolo_moneda = {"CLP": "$", "USD": "USD", "EUR": "EUR", "UF": "UF"}[moneda]
    decimales = 0 if moneda == "CLP" else 2

    st.markdown(
        """
<div style="margin: 28px 0 20px 0; padding: 18px 22px; background: #14243A; border-left: 3px solid #56D8CC; border-radius: 8px;">
    <div style="color: #56D8CC; font-size: 11px; font-weight: 700; letter-spacing: 1.5px;">
        02 / RESULTADOS DE LA EVALUACIÓN
    </div>
    <div style="color: #FFFFFF; font-size: 20px; font-weight: 700; margin-top: 8px;">
        Resumen ejecutivo
    </div>
    <div style="color: #A9BED0; font-size: 13px; margin-top: 6px;">
        Indicadores económicos y límites de admisibilidad de la solicitud.
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )
    
    col_solicitud, col_oferta = st.columns(2)
    with col_solicitud:
        with st.container(border=True):
            st.caption("MONTO REFERENCIAL")
            st.metric("Monto de la solicitud", f"{simbolo_moneda} {formato_chileno(monto, decimales)}")
    with col_oferta:
        with st.container(border=True):
            st.caption("OFERTA EVALUADA")

            # Mostrar el valor original informado por el proveedor.
            simbolo_oferta = {
                "CLP": "$", "USD": "USD",
                "EUR": "EUR", "UF": "UF"
            }[moneda_oferta]

            decimales_oferta = 0 if moneda_oferta == "CLP" else 2

            st.metric(
                "Oferta del proveedor",
                f"{simbolo_oferta} {formato_chileno(oferta, decimales_oferta)}"
            )

            # Mostrar su equivalencia cuando las monedas son distintas.
            if moneda_oferta != moneda:
                st.caption(
                    f"Equivalente en {moneda}: "
                    f"{simbolo_moneda} {formato_chileno(oferta_convertida, decimales)}"
                )

    st.divider()
    st.subheader("Cálculo de admisibilidad")
    col_usd, col_porcentaje = st.columns(2)
    with col_usd:
        with st.container(border=True):
            st.caption("CONVERSIÓN MONETARIA")
            st.metric("Equivalente USD", f"USD {formato_chileno(monto_usd, 2)}")
    with col_porcentaje:
        with st.container(border=True):
            st.caption("CRITERIO DE EVALUACIÓN")
            st.metric("Porcentaje de admisibilidad", f"{porcentaje}%")

    col_inferior, col_superior = st.columns(2)
    with col_inferior:
        with st.container(border=True):
            st.caption("LÍMITE MÍNIMO PERMITIDO")
            st.metric("Límite inferior", f"{simbolo_moneda} {formato_chileno(limite_inferior, decimales)}")
    with col_superior:
        with st.container(border=True):
            st.caption("LÍMITE MÁXIMO PERMITIDO")
            st.metric("Límite superior", f"{simbolo_moneda} {formato_chileno(limite_superior, decimales)}")

    if oferta <= 0:
        return

    # ============================================================
    # EVALUACIÓN ECONÓMICA DE LA OFERTA
    # ============================================================
    # Calcula la desviación porcentual y la diferencia
    # monetaria respecto al monto de la solicitud.
    # Todos los valores se expresan en moneda de la solicitud.
    # ============================================================

    st.divider()
    st.subheader("Evaluación de la oferta")

    desviacion_oferta = calcular_desviacion(
        monto, oferta_convertida
    )

    diferencia_economica = oferta_convertida - monto

    # Mostrar ambos indicadores en columnas independientes.
    col_desviacion, col_diferencia = st.columns(2)

    with col_desviacion:
        with st.container(border=True):
            st.caption("VARIACIÓN PORCENTUAL")
            st.metric(
                "Desviación respecto a la solicitud",
                f"{formato_chileno(desviacion_oferta, 2)}%"
            )

    with col_diferencia:
        with st.container(border=True):
            st.caption("VARIACIÓN MONETARIA")
            st.metric(
                "Diferencia respecto a la solicitud",
                f"{simbolo_moneda} {formato_chileno(diferencia_economica, decimales)}"
            )

    if limite_inferior <= oferta_convertida <= limite_superior:
        st.success(
            "**OFERTA ADMISIBLE**\n\nLa oferta cumple con los límites económicos "
            "establecidos para esta solicitud.",
            icon=":material/check_circle:",
        )
    else:
        st.error(
            "**OFERTA FUERA DEL RANGO DE ADMISIBILIDAD**\n\n"
            "La oferta no cumple con los límites económicos establecidos para esta solicitud. "
            "Revise los indicadores que se presentan a continuación.",
            icon=":material/cancel:",
        )
        if oferta_convertida > limite_superior:
            exceso = calcular_exceso(oferta_convertida, limite_superior)
            descuento_requerido = calcular_descuento_requerido(
                exceso, oferta_convertida
            )
            col_exceso, col_descuento = st.columns(2)
            with col_exceso:
                with st.container(border=True):
                    st.caption("EXCESO ECONÓMICO")
                    st.metric("Monto sobre el límite admisible", f"{simbolo_moneda} {formato_chileno(exceso, decimales)}")
            with col_descuento:
                with st.container(border=True):
                    st.caption("AJUSTE REQUERIDO")
                    st.metric("Descuento mínimo requerido", f"{formato_chileno(descuento_requerido, 2)}%")
            with st.container(border=True):
                st.caption("VALOR MÁXIMO PERMITIDO")
                st.metric("Oferta máxima admisible", f"{simbolo_moneda} {formato_chileno(limite_superior, decimales)}")

            # ====================================================
            # RECOMENDACIÓN PARA NEGOCIACIÓN CON EL PROVEEDOR
            # ====================================================
            # Informa cuánto debe reducirse la oferta para
            # alcanzar el límite máximo de admisibilidad.
            # ====================================================

            # Mostrar recomendación con formato Markdown.
            # Se utiliza st.markdown para evitar que aparezcan
            # asteriscos visibles en los montos y porcentajes.

            st.markdown(
                f"""
                <div style="
                    background-color: #173454;
                    padding: 16px;
                    border-radius: 8px;
                    color: #DCEBFF;
                    margin-top: 12px;
                    margin-bottom: 12px;
                ">
                    <strong>Recomendación de negociación:</strong>
                    Solicitar al proveedor una rebaja mínima de
                    <strong>{simbolo_moneda} {formato_chileno(exceso, decimales)}</strong>,
                    equivalente al
                    <strong>{formato_chileno(descuento_requerido, 2)}%</strong>
                    de su oferta evaluada.
                    El nuevo valor no debería superar
                    <strong>{simbolo_moneda} {formato_chileno(limite_superior, decimales)}</strong>.
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # ====================================================
            # NEGOCIACIÓN EN LA MONEDA ORIGINAL DEL PROVEEDOR
            # ====================================================
            # Convierte la rebaja necesaria y el valor máximo
            # permitido a la moneda utilizada en la oferta.
            # ====================================================

            if moneda_oferta != moneda:

                rebaja_moneda_oferta = convertir_moneda(
                    exceso, moneda, moneda_oferta,
                    dolar_clp, euro_usd, valor_uf
                )

                maximo_moneda_oferta = convertir_moneda(
                    limite_superior, moneda, moneda_oferta,
                    dolar_clp, euro_usd, valor_uf
                )

                st.markdown(
                    f"""
                    <div style="
                        background-color: #173454;
                        padding: 16px;
                        border-radius: 8px;
                        color: #DCEBFF;
                        margin-top: 12px;
                        margin-bottom: 12px;
                    ">
                        <strong>Negociación en {moneda_oferta}:</strong>
                        El proveedor debe reducir su oferta en al menos
                        <strong>{simbolo_oferta} {formato_chileno(rebaja_moneda_oferta, decimales_oferta)}</strong>.
                        La nueva oferta no debería superar
                        <strong>{simbolo_oferta} {formato_chileno(maximo_moneda_oferta, decimales_oferta)}</strong>.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        if oferta_convertida < limite_inferior:
            diferencia_inferior = calcular_diferencia_inferior(
                oferta_convertida, limite_inferior
            )
            with st.container(border=True):
                st.caption("DIFERENCIA ECONÓMICA")
                st.metric("Monto bajo el límite admisible", f"{simbolo_moneda} {formato_chileno(diferencia_inferior, decimales)}")
                
    # ============================================================
    # DESCARGAR INFORME EXCEL
    # ============================================================

    es_admisible = limite_inferior <= oferta_convertida <= limite_superior
    sobre_maximo = oferta_convertida > limite_superior

    datos_excel = {
        "monto_solicitud": monto,
        "moneda_solicitud": moneda,
        "monto_oferta": oferta,
        "moneda_oferta": moneda_oferta,
        "oferta_convertida": oferta_convertida,
        "dolar_clp": dolar_clp,
        "euro_usd": euro_usd,
        "valor_uf": valor_uf,
        "fecha_cotizacion": fecha_cotizacion,
        "origen_cotizaciones": "Banco Central de Chile / valores ingresados",
        "monto_usd": monto_usd,
        "porcentaje": porcentaje,
        "limite_inferior": limite_inferior,
        "limite_superior": limite_superior,
        "desviacion": desviacion_oferta,
        "diferencia_economica": diferencia_economica,
        "resultado": (
            "OFERTA ADMISIBLE"
            if es_admisible
            else "OFERTA FUERA DEL RANGO DE ADMISIBILIDAD"
        ),
        "observacion": None,
        "rebaja_minima": (
            oferta_convertida - limite_superior if sobre_maximo else None
        ),
        "descuento_requerido": (
            (oferta_convertida - limite_superior)
            / oferta_convertida * 100
            if sobre_maximo else None
        ),
        "oferta_maxima": limite_superior if sobre_maximo else None,
        "rebaja_moneda_oferta": None,
        "maximo_moneda_oferta": None,
    }

    if sobre_maximo and moneda_oferta != moneda:
        datos_excel["rebaja_moneda_oferta"] = convertir_moneda(
            oferta_convertida - limite_superior,
            moneda,
            moneda_oferta,
            dolar_clp,
            euro_usd,
            valor_uf
        )

        datos_excel["maximo_moneda_oferta"] = convertir_moneda(
            limite_superior,
            moneda,
            moneda_oferta,
            dolar_clp,
            euro_usd,
            valor_uf
        )

    archivo_excel = generar_excel_admisibilidad(
        datos_excel,
        tabla_admisibilidad
    )

    st.divider()

    st.download_button(
        label="📊 Descargar informe Excel",
        data=archivo_excel,
        file_name="Informe_Admisibilidad.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        on_click="ignore",
    )
