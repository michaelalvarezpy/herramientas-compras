import streamlit as st
from datetime import date, timedelta
from Inteligencia_Economica.Servicios.banco_central import obtener_ultimos_valores, consultar_ipc
from Inteligencia_Economica.Servicios.cobre import consultar_cobre
from Inteligencia_Economica.Modulos.conversor_monedas import mostrar_conversor
from Inteligencia_Economica.Modulos.analisis_historico import mostrar_analisis_historico
from Inteligencia_Economica.Modulos.simulador_economico import mostrar_simulador
from Inteligencia_Economica.Modulos.ipc_reajustes import mostrar_ipc_reajustes
from Inteligencia_Economica.Modulos.comparador_indicadores import mostrar_comparador_indicadores


def mostrar_analisis_economico():
    # ENCABEZADO
    st.markdown(
        """
        <div style="background:linear-gradient(120deg,#14243A,#102C3B);
                    padding:25px;
                    border:1px solid #253D52;
                    border-radius:14px;
                    margin-bottom:25px;">
        <span style="color:#56D8CC;font-size:12px;
                     font-weight:700;letter-spacing:2px;">
        CENTRO DE ANÁLISIS ECONÓMICO
        </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.title("📊 Inteligencia Económica")

    st.caption(
        "Tipos de cambio, análisis histórico, "
        "simulaciones, IPC, cobre y reajustes."
    )

    # INDICADORES ECONÓMICOS
    st.subheader("Indicadores económicos")

    try:
        indicadores = obtener_ultimos_valores()

    except Exception as error:
        indicadores = {}
        st.error(
            f"No fue posible consultar el Banco Central: {error}"
        )

    columnas = st.columns(5)

    monedas = [
        ("USD", "🇺🇸 Dólar (USD)"),
        ("EUR", "🇪🇺 Euro (EUR)"),
        ("UF", "🇨🇱 UF")
    ]

    for columna, (codigo, nombre) in zip(
        columnas[:3], monedas
    ):

        with columna:

            informacion = indicadores.get(codigo)

            if informacion:
                valor = informacion["valor"]
                fecha = informacion["fecha"]

                valor_formateado = (
                    f"${valor:,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

                st.metric(nombre, valor_formateado)

                st.caption(
                    f"Fecha del valor: {fecha:%d-%m-%Y}"
                )

            else:
                st.metric(nombre, "Sin datos")

    # ============================================================
    # INDICADOR IPC - ÚLTIMO MES PUBLICADO
    # ============================================================
    # Consulta los últimos meses disponibles y muestra
    # el índice IPC y su variación mensual.

    with columnas[3]:

        try:
            datos_ipc = consultar_ipc(
                date.today() - timedelta(days=120),
                date.today()
            )

            datos_validos = datos_ipc.dropna(
                subset=["INDICE"]
            )

            if not datos_validos.empty:

                ultimo_ipc = datos_validos.iloc[-1]
                fecha_ipc = datos_validos.index[-1]

                st.metric(
                    "📊 IPC (Base 2023 = 100)",
                    f"{ultimo_ipc['INDICE']:.2f}",
                    delta=(
                        f"{ultimo_ipc['VARIACION_MENSUAL']:+.1f}% mensual"
                        if not datos_validos["VARIACION_MENSUAL"].isna().iloc[-1]
                        else None
                    )
                )

                st.caption(
                    f"Mes de referencia: {fecha_ipc:%m-%Y}"
                )

            else:
                st.metric("📊 IPC", "Sin datos")

        except Exception as error:
            st.metric("📊 IPC", "No disponible")
            st.caption(f"Error de consulta: {error}")

    # ============================================================
    # INDICADOR COBRE - ÚLTIMA COTIZACIÓN PUBLICADA
    # ============================================================
    # Reutiliza el servicio de cobre del análisis histórico.
    # La variación compara los dos últimos registros disponibles.
    with columnas[4]:
        try:
            datos_cobre = consultar_cobre(
                date.today() - timedelta(days=45),
                date.today()
            )

            if not datos_cobre.empty:
                ultimo_valor = float(datos_cobre["COBRE_USD_LIBRA"].iloc[-1])
                fecha_cobre = datos_cobre.index[-1]

                variacion_cobre = None
                if len(datos_cobre) >= 2:
                    valor_anterior = float(datos_cobre["COBRE_USD_LIBRA"].iloc[-2])
                    if valor_anterior > 0:
                        porcentaje = (ultimo_valor / valor_anterior - 1) * 100
                        variacion_cobre = f"{porcentaje:+.2f}% vs. registro anterior"

                valor_cobre = f"{ultimo_valor:.4f}".replace(".", ",")
                st.metric(
                    "⛏️ Cobre (USD/lb)",
                    valor_cobre,
                    delta=variacion_cobre
                )
                st.caption(f"Fecha del valor: {fecha_cobre:%d-%m-%Y}")
            else:
                st.metric("⛏️ Cobre (USD/lb)", "Sin datos")

        except Exception as error:
            st.metric("⛏️ Cobre (USD/lb)", "No disponible")
            st.caption(f"Error de consulta: {error}")

    st.caption(
        "Fuente: Banco Central de Chile. "
        "Se muestra el último registro disponible "
        "de cada indicador."
    )


    st.divider()
    pestañas = st.tabs([
        "💱 Conversor de Monedas",
        "📈 Análisis Histórico",
        "🔮 Simulador Económico",
        "📊 IPC y Reajustes",
        "📉 Comparador de Indicadores",
    ])
    with pestañas[0]:
        mostrar_conversor(indicadores)
    with pestañas[1]:
        mostrar_analisis_historico()
    with pestañas[2]:
        mostrar_simulador(indicadores)
    with pestañas[3]:
        mostrar_ipc_reajustes()

    # Quinta pestaña: módulo independiente del comparador.
    with pestañas[4]:
        mostrar_comparador_indicadores()
