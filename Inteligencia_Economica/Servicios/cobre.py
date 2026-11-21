from datetime import date

import pandas as pd
import streamlit as st

from Inteligencia_Economica.Servicios.banco_central import conectar_banco_central


# ============================================================
# SERVICIO: PRECIO HISTÓRICO DEL COBRE
# Fuente: Banco Central de Chile
# Indicador: Precio del cobre refinado BML, grado A
# Unidad: dólares estadounidenses por libra (USD/lb)
# ============================================================

SERIE_COBRE_DIARIA = "F019.PPB.PRE.100.D"


@st.cache_data(ttl=3600)
def consultar_cobre(fecha_inicio: date, fecha_fin: date) -> pd.DataFrame:
    """Consulta el precio diario del cobre en el Banco Central de Chile."""

    if fecha_inicio > fecha_fin:
        raise ValueError(
            "La fecha inicial no puede ser posterior a la fecha final."
        )

    siete = conectar_banco_central()

    datos = siete.cuadro(
        series=[SERIE_COBRE_DIARIA],
        desde=fecha_inicio.strftime("%Y-%m-%d"),
        hasta=fecha_fin.strftime("%Y-%m-%d"),
    )

    if datos is None or datos.empty:
        return pd.DataFrame(columns=["COBRE_USD_LIBRA"])

    datos = datos.rename(
        columns={SERIE_COBRE_DIARIA: "COBRE_USD_LIBRA"}
    )

    datos.index = pd.to_datetime(datos.index)
    datos = datos.sort_index()

    if "COBRE_USD_LIBRA" not in datos.columns:
        datos["COBRE_USD_LIBRA"] = float("nan")

    datos["COBRE_USD_LIBRA"] = pd.to_numeric(
        datos["COBRE_USD_LIBRA"],
        errors="coerce",
    )

    # Excluir valores no disponibles o no válidos.
    datos = datos.dropna(subset=["COBRE_USD_LIBRA"])
    datos = datos[datos["COBRE_USD_LIBRA"] > 0]

    return datos[["COBRE_USD_LIBRA"]]
