def convertir_a_usd(monto, moneda, tipo_cambio, valor_uf=0):
    if moneda == "CLP":
        monto_usd = monto / tipo_cambio
    elif moneda == "USD":
        monto_usd = monto
    elif moneda == "EUR":
        monto_usd = monto * tipo_cambio
    elif moneda == "UF":
        monto_usd = (monto * valor_uf) / tipo_cambio
        
    return monto_usd

def obtener_porcentaje(monto_usd):
    if monto_usd <= 500:
        return 40
    elif monto_usd <= 1000:
        return 30
    elif monto_usd <= 5000:
        return 20
    elif monto_usd <= 10000:
        return 10
    elif monto_usd <= 30000:
        return 7
    elif monto_usd <= 50000:
        return 5
    elif monto_usd <= 1000000:
        return 3
    elif monto_usd <= 5000000:
        return 2
    else:
        return 1

def calcular_limites(monto, porcentaje):
    desviacion = monto * (porcentaje / 100)
    
    limite_inferior = monto - desviacion
    limite_superior = monto + desviacion
    
    return limite_inferior, limite_superior

def calcular_desviacion(monto, oferta):
    desviacion = ((oferta - monto) / monto) * 100
    return desviacion

def calcular_exceso(oferta, limite_superior):
    exceso = oferta - limite_superior
    return exceso

def calcular_diferencia_inferior(oferta, limite_inferior):
    diferencia = limite_inferior - oferta
    return diferencia

def calcular_descuento_requerido(exceso, oferta):
    descuento = (exceso / oferta) * 100
    return descuento

# ============================================================
# CONVERSIÓN AUTOMÁTICA ENTRE MONEDAS
# ============================================================
# Permite convertir ofertas entre CLP, USD, EUR y UF.
# El resultado se expresa en la moneda de la solicitud.
#
# Esta función también podrá reutilizarse en el módulo
# Evaluación Comparativa de Ofertas.
# ============================================================

def convertir_moneda(
    monto,
    moneda_origen,
    moneda_destino,
    dolar_clp,
    euro_usd,
    valor_uf
):
    """
    Convierte un monto entre CLP, USD, EUR y UF.

    Parámetros:
    - monto: valor original que se desea convertir.
    - moneda_origen: moneda en que está expresado el monto.
    - moneda_destino: moneda en que se necesita el resultado.
    - dolar_clp: pesos chilenos equivalentes a 1 USD.
    - euro_usd: dólares equivalentes a 1 EUR.
    - valor_uf: pesos chilenos equivalentes a 1 UF.

    Retorna:
    - Monto convertido a la moneda de destino.
    """

    # Validar que ambas monedas estén disponibles.
    monedas_validas = ("CLP", "USD", "EUR", "UF")

    if moneda_origen not in monedas_validas:
        raise ValueError("Moneda de origen no válida.")

    if moneda_destino not in monedas_validas:
        raise ValueError("Moneda de destino no válida.")

    # Evitar convertir montos negativos.
    if monto < 0:
        raise ValueError("El monto no puede ser negativo.")

    # Si ambas monedas son iguales, no se necesita conversión.
    if moneda_origen == moneda_destino:
        return monto

    # Establecer el valor de cada moneda expresado en CLP.
    # El peso chileno funciona como moneda intermedia.
    tasas_clp = {
        "CLP": 1,
        "USD": dolar_clp,
        "EUR": dolar_clp * euro_usd,
        "UF": valor_uf
    }

    # Comprobar que las cotizaciones utilizadas sean válidas.
    if tasas_clp[moneda_origen] <= 0:
        raise ValueError("Tipo de cambio de origen no válido.")

    if tasas_clp[moneda_destino] <= 0:
        raise ValueError("Tipo de cambio de destino no válido.")

    # Paso 1: convertir el monto original a pesos chilenos.
    monto_clp = monto * tasas_clp[moneda_origen]

    # Paso 2: convertir los pesos a la moneda solicitada.
    monto_convertido = monto_clp / tasas_clp[moneda_destino]

    # Entregar el resultado sin redondearlo.
    # El formato de decimales se aplicará en la interfaz.
    return monto_convertido