import pandas as pd
from io import BytesIO
from openpyxl.styles import Font, PatternFill, Alignment

def generar_excel_comparacion(
    df_resultados, 
    moneda, proveedor_resumen, 
    precio_minimo, 
    alternativas_ganadoras,
    datos_solicitud=None
):
    archivo_excel = BytesIO()
    
    with pd.ExcelWriter(archivo_excel, engine="openpyxl") as writer:
        
        df_resultados.drop(columns=["Oferta_numero"]).to_excel(
            
            writer,
            sheet_name ="Comparacion",
            index=False
        )
        
        total_proveedores = df_resultados["Proveedor"].str.strip().str.casefold().nunique()
        total_ofertas = len(df_resultados)
        
        total_admisibles = (
            df_resultados["Estado"] == "ADMISIBLE"
        ).sum()
        
        total_fuera_rango = (
            df_resultados["Estado"] == "FUERA DEL RANGO"
        ).sum()
        
        detalle_alternativas = ", ".join(
            f"{oferta['Proveedor']} - {oferta['Descripción de la oferta']}"
            for oferta in alternativas_ganadoras
        )

        if not detalle_alternativas:
            detalle_alternativas = "Sin ofertas admisibles"
            
        ahorro_economico = 0
        porcentaje_ahorro = 0

        if (
            datos_solicitud is not None
            and precio_minimo is not None
        ):
            monto_solicitud = datos_solicitud["Monto de la solicitud"]

            if monto_solicitud > 0 and precio_minimo < monto_solicitud:
                ahorro_economico = monto_solicitud - precio_minimo
                porcentaje_ahorro = (ahorro_economico / monto_solicitud) * 100
        
        df_resumen = pd.DataFrame({
            "Indicador": [
                "Total de proveedores",
                "Total de ofertas evaluadas",
                "Ofertas admisibles",
                "Ofertas fuera de rango",
                "Proveedor(es) con menor oferta admisible",
                "Menor oferta admisible",
                "Descripción de la(s) oferta(s) ganadora(s)",
                "Ahorro económico",
                "Porcentaje de ahorro"
            ],
            "Cantidad": [
                total_proveedores,
                total_ofertas,
                total_admisibles,
                total_fuera_rango,
                proveedor_resumen,
                precio_minimo if precio_minimo is not None else "Sin ofertas admisibles",
                detalle_alternativas,
                ahorro_economico,
                porcentaje_ahorro
            ]
        })
        
        df_resumen.to_excel(
            writer,
            sheet_name="Resumen",
            index=False
        )
        
        # =============================================
        # Hoja: Datos de la solicitud
        # =============================================
        # Registra los antecedentes utilizados
        # para calcular la admisibilidad.
        if datos_solicitud is not None:
            
            df_datos_solicitud = pd.DataFrame(
                list(datos_solicitud.items()),
                columns=["Concepto", "Valor"]
            )
            
            df_datos_solicitud.to_excel(
                writer,
                sheet_name="Datos_Solicitud",
                index=False
            )
            
        hoja_resumen = writer.sheets["Resumen"]
        
        hoja_resumen.column_dimensions["A"].width = 45
        hoja_resumen.column_dimensions["B"].width = 45
        
        fondo_azul = PatternFill(
            start_color="17365D",
            end_color="17365D",
            fill_type="solid"
        )
        
        for celda in hoja_resumen[1]:
            celda.fill = fondo_azul
            celda.font = Font(color="FFFFFF", bold=True)
            
        # ============================================
        # Formato de la hoja Datos_Solicitud
        # ============================================
        if datos_solicitud is not None:

            hoja_datos = writer.sheets["Datos_Solicitud"]

            # Ajustar el ancho de las columnas.
            hoja_datos.column_dimensions["A"].width = 40
            hoja_datos.column_dimensions["B"].width = 25

            # Aplicar formato al encabezado.
            for celda in hoja_datos[1]:
                celda.fill = fondo_azul
                celda.font = Font(color="FFFFFF", bold=True)
            
            # Formato del monto de la solicitud según la moneda.
            if moneda == "CLP":
                hoja_datos["B3"].number_format = '#,##0'
            else:
                hoja_datos["B3"].number_format = '#,##0.00'
                
            # Mostrar el equivalente USD con dos decimales.
            hoja_datos["B5"].number_format = '#,##0.00'
            
            # Formato de los límites según la moneda.
            formato_limites = '#,##0' if moneda == "CLP" else '#,##0.00'

            hoja_datos["B7"].number_format = formato_limites
            hoja_datos["B8"].number_format = formato_limites
            
            # Formato del dólar observado utilizado.
            if moneda in ("CLP", "UF"):
                hoja_datos["B9"].number_format = '#,##0.00'
                
            # Formato del tipo de cambio EUR/USD.
            if moneda == "EUR":
                hoja_datos["B9"].number_format = '#,##0.000000'
                
            # Formato del valor UF utilizado.
            if moneda == "UF":
                hoja_datos["B10"].number_format = '#,##0.00'
            
        formatos_monedas = {
            "CLP": '"$" #,##0',
            "USD": '"USD" #,##0.00',
            "EUR": '"EUR" #,##0.00',
            "UF": '"UF" #,##0.00'
        }
        
        if precio_minimo is not None:
            hoja_resumen["B7"].number_format = formatos_monedas[moneda]
            
        hoja_resumen["B9"].number_format = formatos_monedas[moneda]
        hoja_resumen["B10"].number_format = '0.00"%"'
        
        # Destacar los indicadores de ahorro económico.
        fondo_ahorro = PatternFill(
            start_color="E2F0D9",
            end_color="E2F0D9",
            fill_type="solid"
        )

        for fila in (9, 10):
            for celda in hoja_resumen[f"A{fila}:B{fila}"][0]:
                celda.fill = fondo_ahorro
                celda.font = Font(color="006100", bold=True)
            
        hoja = writer.sheets["Comparacion"]
        
        for celda in hoja[1]:
            celda.fill = fondo_azul
            celda.font = Font(color="FFFFFF", bold=True)
            
        fondo_verde = PatternFill(
            start_color="C6EFCE",
            end_color="C6EFCE",
            fill_type="solid"
        )

        fondo_rojo = PatternFill(
            start_color="FFC7CE",
            end_color="FFC7CE",
            fill_type="solid"
        )
        
        for fila in range(2, hoja.max_row + 1):
            celda_estado = hoja[f"G{fila}"]
            
            if celda_estado.value == "ADMISIBLE":
                celda_estado.fill = fondo_verde
            
            elif celda_estado.value == "FUERA DEL RANGO":
                celda_estado.fill = fondo_rojo
                
        hoja.auto_filter.ref = hoja.dimensions
        
        formato_monto = '#,##0' if moneda == "CLP" else '#,##0.00'
        
        for fila in range(2, hoja.max_row + 1):
            hoja[f"C{fila}"].number_format = formato_monto
            hoja[f"D{fila}"].number_format = '0'
            hoja[f"F{fila}"].number_format = '0.00"%"'
            hoja[f"H{fila}"].number_format = formato_monto
            hoja[f"I{fila}"].number_format = formato_monto
            hoja[f"J{fila}"].number_format = '0.00"%"'
            
        anchos = {
            "A": 25,  # Proveedor
            "B": 35,  # Descripción de la oferta
            "C": 20,  # Oferta económica
            "D": 20,  # Plazo de entrega
            "E": 20,  # Unidad del plazo
            "F": 20,  # Desviación (%)
            "G": 23,  # Estado de admisibilidad
            "H": 25,  # Exceso sobre límite
            "I": 25,  # Monto bajo límite
            "J": 28   # Descuento requerido (%)
        }
        
        for columna, ancho in anchos.items():
            hoja.column_dimensions[columna].width = ancho
            
    archivo_excel.seek(0)
    return archivo_excel
        
        
    
    