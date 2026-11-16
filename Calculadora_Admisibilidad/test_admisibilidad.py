import math

from Calculadora_Admisibilidad.Calculos.admisibilidad import (
    obtener_porcentaje,
    calcular_limites,
    convertir_a_usd,
    calcular_desviacion,
    calcular_exceso,
    calcular_descuento_requerido,
    calcular_diferencia_inferior
)

monto_usd = convertir_a_usd(1000000, "CLP", 1000, 0)

assert math.isclose(monto_usd, 1000, abs_tol=0.000001)

print("Prueba de conversión CLP a USD commpletada correctamente")

monto_usd = convertir_a_usd(1500, "USD", 1, 0)

assert math.isclose(monto_usd, 1500, abs_tol=0.000001)

print("Prueba de conversión USD completada correctamente")

monto_usd = convertir_a_usd(2000, "EUR", 1.15, 0)

assert math.isclose(monto_usd, 2300, abs_tol=0.000001)

print("Prueba de conversión EUR completada correctamente")

monto_usd = convertir_a_usd(80, "UF", 1000, 40000)

assert math.isclose(monto_usd, 3200, abs_tol=0.000001)

print("Prueba de conversión UF completada correctamente")

verificar_desviacion = calcular_desviacion(2000000, 1600000)

assert math.isclose(verificar_desviacion, -20, rel_tol=0, abs_tol=0.000001)

print("Prueba de revision de desviación completada correctamente")


verificar_exceso = calcular_exceso(1800000, 1500000)
assert math.isclose(verificar_exceso, 300000, abs_tol=0.000001)
print("Prueba de revisión de exceso completada correctamente")

verificar_descuento_requerido = calcular_descuento_requerido(400000, 2000000)
assert math.isclose(verificar_descuento_requerido, 20, abs_tol=0.000001)
print("Prueba de revisión de descuento requerido completada correctamente")

verificar_diferencia_inferior = calcular_diferencia_inferior(850000, 1000000)
assert math.isclose(verificar_diferencia_inferior, 150000, abs_tol=0.000001)
print("Prueba de revisión de diferencia inferior completada correctamente")

monto_usd = convertir_a_usd(3000000, "CLP", 1000, 0)
porcentaje = obtener_porcentaje(monto_usd)
assert math.isclose(monto_usd, 3000, abs_tol=0.000001)
assert math.isclose(porcentaje, 20, abs_tol=0.000001)
print("Prueba de revisión monto usd y porcentaje completada correctamente")

limite_inferior, limite_superior = calcular_limites(3000000, porcentaje)
assert math.isclose(limite_inferior, 2400000, abs_tol=0.000001)
assert math.isclose(limite_superior, 3600000, abs_tol=0.000001)

print("Prueba revisión limites inferior y superior completada correctamente")


oferta = 4000000
exceso = calcular_exceso(oferta, limite_superior)
assert math.isclose(exceso, 400000, abs_tol=0.000001)

descuento_requerido = calcular_descuento_requerido(exceso, oferta)
assert math.isclose(descuento_requerido, 10, abs_tol=0.000001)

print("Prueba de exceso y descuento mínimo commpletada correctamente")


if limite_inferior <= oferta <= limite_superior:
    estado = "ADMISIBLE"
else:
    estado = "FUERA DEL RANGO"

assert estado == "FUERA DEL RANGO"

print("Prueba de estado de admisibilidad completada correctamente")    
    