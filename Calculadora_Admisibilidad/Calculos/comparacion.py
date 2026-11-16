import pandas as pd

from Calculadora_Admisibilidad.Calculos.admisibilidad import (
    calcular_desviacion,
    calcular_exceso,
    calcular_diferencia_inferior,
    calcular_descuento_requerido
)

def evaluar_proveedores(tabla_proveedores, monto, limite_inferior, limite_superior, moneda):
    resultados = []
    contador_ofertas = {}
    
    for indice, fila in tabla_proveedores.iterrows():
        proveedor = fila["Proveedor"]
        descripcion_oferta = fila["Descripción de la oferta"]
        oferta_proveedor = fila["Oferta"]
        
        plazo_entrega = fila.get("Plazo de entrega")
        unidad_plazo = fila.get("Unidad del plazo")
        
        if pd.isna(proveedor) or pd.isna(oferta_proveedor):
            continue
        
        if not isinstance(proveedor, str) or not proveedor.strip():
            continue

        if oferta_proveedor <= 0:
            continue
        
        proveedor = proveedor.strip()
        clave_proveedor = proveedor.casefold()

        contador_ofertas[clave_proveedor] = contador_ofertas.get(clave_proveedor, 0) + 1

        if pd.isna(descripcion_oferta) or not str(descripcion_oferta).strip():
            descripcion_oferta = f"Oferta {contador_ofertas[clave_proveedor]}"
        else:
            descripcion_oferta = str(descripcion_oferta).strip()
        
        desviacion = calcular_desviacion(monto, oferta_proveedor)
        
        if limite_inferior <= oferta_proveedor <= limite_superior:
            estado = "ADMISIBLE"
        else:
            estado = "FUERA DEL RANGO"
            
        exceso = 0

        if oferta_proveedor > limite_superior:
            exceso = calcular_exceso(oferta_proveedor, limite_superior)
            
        diferencia_inferior = 0

        if oferta_proveedor < limite_inferior:
            diferencia_inferior = calcular_diferencia_inferior(
                oferta_proveedor,
                limite_inferior
            )
            
        descuento_requerido = 0

        if exceso > 0:
            descuento_requerido = calcular_descuento_requerido(
                exceso,
                oferta_proveedor
            )
            
        resultados.append({
            "Proveedor": proveedor,
            "Descripción de la oferta": descripcion_oferta,
            "Oferta": oferta_proveedor,
            "Plazo de entrega": plazo_entrega,
            "Unidad del plazo": unidad_plazo,
            "Desviación (%)": desviacion,
            "Estado": estado,
            "Exceso sobre límite": exceso,
            "Monto bajo límite": diferencia_inferior,
            "Descuento requerido (%)": descuento_requerido
        })
        
    df_resultados = pd.DataFrame(resultados)
    return df_resultados

def obtener_mejores_ofertas(df_resultados):
    df_admisibles = df_resultados[
        df_resultados["Estado"] == "ADMISIBLE"
    ]

    if df_admisibles.empty:
        return None, [], []

    precio_minimo = df_admisibles["Oferta"].min()

    proveedores_empatados = df_admisibles[
        df_admisibles["Oferta"] == precio_minimo
    ]

    nombres_proveedores = proveedores_empatados["Proveedor"].drop_duplicates().tolist()
    
    alternativas_ganadoras = proveedores_empatados[
        ["Proveedor", "Descripción de la oferta"]
    ].to_dict("records")

    return precio_minimo, nombres_proveedores, alternativas_ganadoras

        
        