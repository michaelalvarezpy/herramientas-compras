import requests, os,bcchapi
from datetime import date, timedelta

token = os.getenv("BCCH_API_TOKEN")

if not token:
    raise ValueError("No se ha configurado el token del Banco Central.")

siete = bcchapi.Siete(token=token)

# ===========================================
# Obtener el valor del dolar observado
# ===========================================
def obtener_dolar_observado():
    hoy = date.today()
    inicio = hoy - timedelta(days=10)

    datos = siete.cuadro(
        series=["F073.TCO.PRE.Z.D"],
        desde=inicio.strftime("%Y-%m-%d"),
        hasta=hoy.strftime("%Y-%m-%d")
    )

    valores = datos["F073.TCO.PRE.Z.D"].dropna()

    if valores.empty:
        raise ValueError("No hay valores disponibles del dólar observado.")

    fecha = valores.index[-1]
    valor = float(valores.iloc[-1])

    return valor, fecha

# ===========================================
# Obtener el valor de la UF
# ===========================================
def obtener_valor_uf():
    hoy = date.today()
    inicio = hoy - timedelta(days=10)

    datos = siete.cuadro(
        series=["F073.UFF.PRE.Z.D"],
        desde=inicio.strftime("%Y-%m-%d"),
        hasta=hoy.strftime("%Y-%m-%d")
    )

    valores = datos["F073.UFF.PRE.Z.D"].dropna()

    if valores.empty:
        raise ValueError("No hay valores disponibles de la UF.")

    fecha = valores.index[-1]
    valor = float(valores.iloc[-1])

    return valor, fecha

# =============================================
# Obtener el valor del Euro en pesos chilenos
# =============================================
def obtener_valor_euro():
    hoy = date.today()
    inicio = hoy - timedelta(days=10)

    datos = siete.cuadro(
        series=["F072.CLP.EUR.N.O.D"],
        desde=inicio.strftime("%Y-%m-%d"),
        hasta=hoy.strftime("%Y-%m-%d")
    )

    valores = datos["F072.CLP.EUR.N.O.D"].dropna()

    if valores.empty:
        raise ValueError("No hay valores disponibles del euro.")

    fecha = valores.index[-1]
    valor = float(valores.iloc[-1])

    return valor, fecha

# ======================================================
# Obtener tipo de cambio EUR/USD con fecha coincidente
# ======================================================
# Consulta el euro y el dólar en una misma solicitud.
# Utiliza la última fecha en que ambas monedas
# tengan una cotización disponible.
def obtener_tipo_cambio_eur_usd():
    hoy = date.today()
    inicio = hoy - timedelta(days=10)
    
    datos = siete.cuadro(
        series=["F072.CLP.EUR.N.O.D",
            "F073.TCO.PRE.Z.D"
        ],
        desde=inicio.strftime("%Y-%m-%d"),
        hasta=hoy.strftime("%Y-%m-%d")
    )
    
    valores = datos[
        ["F072.CLP.EUR.N.O.D", "F073.TCO.PRE.Z.D"]
    ].dropna()
    
    if valores.empty:
        raise ValueError(
            "No existen cotizaciones del euro y dólar "
            "correspondientes a una misma fecha."
        )
        
    fecha = valores.index[-1]
    euro_clp = float(valores["F072.CLP.EUR.N.O.D"].iloc[-1])
    dolar_clp = float(valores["F073.TCO.PRE.Z.D"].iloc[-1])

    if dolar_clp <= 0:
        raise ValueError("El valor del dólar no es válido.")

    tipo_cambio = euro_clp / dolar_clp

    return tipo_cambio, fecha


# ==================================================
# Obtener UF y dólar con fecha coincidente
# ==================================================
# Consulta ambos valores en una misma solicitud.
# Selecciona la última fecha con datos disponibles
# para las dos cotizaciones.

def obtener_uf_y_dolar():
    hoy = date.today()
    inicio = hoy - timedelta(days=10)

    datos = siete.cuadro(
        series=[
            "F073.UFF.PRE.Z.D",
            "F073.TCO.PRE.Z.D"
        ],
        desde=inicio.strftime("%Y-%m-%d"),
        hasta=hoy.strftime("%Y-%m-%d")
    )

    valores = datos[
        ["F073.UFF.PRE.Z.D", "F073.TCO.PRE.Z.D"]
    ].dropna().sort_index()

    if valores.empty:
        raise ValueError(
            "No existen cotizaciones de UF y dólar "
            "correspondientes a una misma fecha."
        )

    fecha = valores.index[-1]
    valor_uf = float(valores["F073.UFF.PRE.Z.D"].iloc[-1])
    valor_dolar = float(valores["F073.TCO.PRE.Z.D"].iloc[-1])

    if valor_uf <= 0 or valor_dolar <= 0:
        raise ValueError("Los valores de UF y dólar deben ser positivos.")

    return valor_uf, valor_dolar, fecha

# ============================================================
# COTIZACIONES PARA CONVERSIÓN ENTRE MÚLTIPLES MONEDAS
# ============================================================
# Obtiene dólar, euro y UF desde el Banco Central de Chile.
# Utiliza la última fecha en que las tres cotizaciones
# tengan valores disponibles.
#
# Esta función permitirá convertir ofertas entre monedas
# diferentes utilizando cotizaciones consistentes.
# ============================================================

def obtener_cotizaciones_monedas():

    # Definir el período de consulta.
    hoy = date.today()
    inicio = hoy - timedelta(days=10)

    # Consultar las tres series en una misma solicitud.
    datos = siete.cuadro(
        series=[
            "F073.TCO.PRE.Z.D",    # Dólar observado en CLP
            "F072.CLP.EUR.N.O.D",  # Euro en CLP
            "F073.UFF.PRE.Z.D"     # UF en CLP
        ],
        desde=inicio.strftime("%Y-%m-%d"),
        hasta=hoy.strftime("%Y-%m-%d")
    )

    # Conservar únicamente fechas con las tres cotizaciones.
    valores = datos[
        [
            "F073.TCO.PRE.Z.D",
            "F072.CLP.EUR.N.O.D",
            "F073.UFF.PRE.Z.D"
        ]
    ].dropna().sort_index()

    # Verificar que existan datos disponibles.
    if valores.empty:
        raise ValueError(
            "No existen cotizaciones coincidentes "
            "para dólar, euro y UF."
        )

    # Seleccionar la última fecha disponible.
    fecha = valores.index[-1]

    # Extraer las cotizaciones correspondientes.
    dolar_clp = float(valores["F073.TCO.PRE.Z.D"].iloc[-1])
    euro_clp = float(valores["F072.CLP.EUR.N.O.D"].iloc[-1])
    valor_uf = float(valores["F073.UFF.PRE.Z.D"].iloc[-1])

    # Validar que las cotizaciones sean positivas.
    if dolar_clp <= 0 or euro_clp <= 0 or valor_uf <= 0:
        raise ValueError("Las cotizaciones deben ser positivas.")

    # Calcular cuántos dólares equivale un euro.
    euro_usd = euro_clp / dolar_clp

    # Devolver los valores y la fecha utilizada.
    return dolar_clp, euro_usd, valor_uf, fecha