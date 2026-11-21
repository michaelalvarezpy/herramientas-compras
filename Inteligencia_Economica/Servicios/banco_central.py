
import os
import math
from datetime import date, timedelta

import bcchapi
import pandas as pd
import streamlit as st


# SERIES DEL BANCO CENTRAL
SERIES = {
    "USD": "F073.TCO.PRE.Z.D",
    "EUR": "F072.CLP.EUR.N.O.D",
    "UF": "F073.UFF.PRE.Z.D",
}

# SERIES DEL IPC - BASE 2023 = 100
SERIES_IPC = {
    "INDICE": "F074.IPC.IND.Z.EP23.C.M",
    "VARIACION_MENSUAL": "F074.IPC.VAR.Z.EP23.C.M",
}

@st.cache_resource
def conectar_banco_central():

    token = os.getenv("BCCH_API_TOKEN")

    if not token:
        raise ValueError(
            "No se encontró BCCH_API_TOKEN."
        )

    return bcchapi.Siete(token=token)


@st.cache_data(ttl=3600)
def consultar_monedas(fecha_inicio, fecha_fin):

    if fecha_inicio > fecha_fin:
        raise ValueError(
            "La fecha inicial no puede superar la final."
        )

    siete = conectar_banco_central()

    datos = siete.cuadro(
        series=list(SERIES.values()),
        desde=fecha_inicio.strftime("%Y-%m-%d"),
        hasta=fecha_fin.strftime("%Y-%m-%d")
    )

    if datos is None or datos.empty:
        return pd.DataFrame(
            columns=["USD", "EUR", "UF"]
        )

    datos = datos.rename(
        columns={
            codigo: moneda
            for moneda, codigo in SERIES.items()
        }
    )

    datos.index = pd.to_datetime(datos.index)
    datos = datos.sort_index()

    for moneda in SERIES:

        if moneda not in datos.columns:
            datos[moneda] = float("nan")

        datos[moneda] = pd.to_numeric(
            datos[moneda],
            errors="coerce"
        )

    return datos[list(SERIES.keys())]


def obtener_ultimos_valores():

    hoy = date.today()
    inicio = hoy - timedelta(days=15)

    datos = consultar_monedas(inicio, hoy)

    resultados = {}

    for moneda in SERIES:

        # Excluir tasas nulas, negativas o no finitas antes de elegir la última.
        valores = datos[moneda].dropna()
        valores = valores[valores.apply(lambda valor: math.isfinite(float(valor)) and float(valor) > 0)]

        if valores.empty:
            resultados[moneda] = None
            continue

        resultados[moneda] = {
            "valor": float(valores.iloc[-1]),
            "fecha": valores.index[-1].date()
        }

    return resultados

# ============================================================
# CONSULTA DE IPC - BANCO CENTRAL DE CHILE
# ============================================================
# Objetivo:
# Obtener los valores oficiales del IPC para un período.
#
# Datos consultados:
# - INDICE: nivel del IPC, base 2023 = 100.
# - VARIACION_MENSUAL: variación porcentual de cada mes.
#
# Parámetros:
# - fecha_inicio: fecha inicial de consulta.
# - fecha_fin: fecha final de consulta.
#
# Resultado:
# DataFrame con fechas, índice IPC y variación mensual.
#
# Los datos permitirán calcular reajustes de contratos,
# actualizar precios y analizar la inflación histórica.
# ============================================================

@st.cache_data(ttl=3600)
def consultar_ipc(fecha_inicio, fecha_fin):

    if fecha_inicio > fecha_fin:
        raise ValueError(
            "La fecha inicial no puede superar la fecha final."
        )

    siete = conectar_banco_central()

    datos = siete.cuadro(
        series=list(SERIES_IPC.values()),
        desde=fecha_inicio.strftime("%Y-%m-%d"),
        hasta=fecha_fin.strftime("%Y-%m-%d")
    )

    if datos is None or datos.empty:
        return pd.DataFrame(
            columns=["INDICE", "VARIACION_MENSUAL"]
        )

    datos = datos.rename(
        columns={
            codigo: nombre
            for nombre, codigo in SERIES_IPC.items()
        }
    )


    datos.index = pd.to_datetime(datos.index)
    datos = datos.sort_index()

    for nombre in SERIES_IPC:

        if nombre not in datos.columns:
            datos[nombre] = float("nan")

        datos[nombre] = pd.to_numeric(
            datos[nombre],
            errors="coerce"
        )

    return datos[list(SERIES_IPC.keys())]