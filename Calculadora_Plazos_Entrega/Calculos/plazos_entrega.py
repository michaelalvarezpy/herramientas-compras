from datetime import date, timedelta

import holidays

def calcular_fecha_entrega(fecha_inicio, dias_plazo):
    fecha_entrega = fecha_inicio + timedelta(days=dias_plazo)
    
    return fecha_entrega

def calcular_dias_habiles(fecha_inicio, dias_plazo, excluir_feriados=True):
    
    fecha_entrega = fecha_inicio
    dias_contados = 0
    
    feriados_chile = holidays.country_holidays("CL", language="es")
    
    while dias_contados < dias_plazo:
        
        fecha_entrega += timedelta(days=1)
        
        es_dia_semana = fecha_entrega.weekday() < 5
        
        es_feriado = (
            excluir_feriados
            and fecha_entrega in feriados_chile
        )
        
        if es_dia_semana and not es_feriado:
            dias_contados += 1
            
    return fecha_entrega

def obtener_feriados_chile(anio):

    feriados = holidays.country_holidays(
        "CL",
        years=anio,
        language="es"
    )

    lista_feriados = []

    for fecha, nombre in sorted(feriados.items()):

        lista_feriados.append({
            "Fecha": fecha,
            "Feriado": nombre,
            "Día": fecha.strftime("%A")
        })

    return lista_feriados

def obtener_feriados_periodo(fecha_inicio, fecha_entrega):

    feriados = holidays.country_holidays("CL", language="es")

    lista_feriados = []

    fecha_actual = fecha_inicio + timedelta(days=1)

    while fecha_actual <= fecha_entrega:

        if fecha_actual in feriados:

            es_habil = fecha_actual.weekday() < 5

            lista_feriados.append({
                "Fecha": fecha_actual,
                "Feriado": feriados.get(fecha_actual),
                "Día hábil": es_habil
            })

        fecha_actual += timedelta(days=1)

    return lista_feriados

if __name__ == "__main__":
    fecha = date(2026, 10, 20)
    plazo = 15
    
    resultado = calcular_fecha_entrega(fecha, plazo)
    
    print("Fecha estimada de entrega:", resultado)
    
    resultado_habiles = calcular_dias_habiles(fecha, plazo)
    
    print("Fecha de entrega en días hábiles:", resultado_habiles)
    
    fecha_prueba = date(2026,12, 1)
    
    sin_feriados = calcular_dias_habiles(
        fecha_prueba, 10, excluir_feriados=False
    )
    
    con_feriados = calcular_dias_habiles(
        fecha_prueba, 10, excluir_feriados=True
    )
    
    print("Sin excluir feriados:", sin_feriados)
    print("Excluyendo feriados:", con_feriados)
    
    
    
    
    
    
    