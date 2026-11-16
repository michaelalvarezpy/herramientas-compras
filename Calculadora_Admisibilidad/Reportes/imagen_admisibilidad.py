
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# GENERADOR DE TARJETA DE ADMISIBILIDAD PARA WHATSAPP
# ============================================================
# Crea una imagen PNG compacta con los tramos y porcentajes.
# No modifica los cálculos de admisibilidad.
# ============================================================

def generar_imagen_admisibilidad(tabla_admisibilidad):

    # Dimensiones de la tarjeta.
    ancho = 760
    alto = 570

    # Colores del diseño.
    fondo = "#101C2E"
    encabezado = "#18344B"
    blanco = "#F0F5FA"
    secundario = "#B6D1E2"
    turquesa = "#5EE0D2"
    linea = "#304052"

    # Crear imagen.
    imagen = Image.new("RGB", (ancho, alto), fondo)
    dibujo = ImageDraw.Draw(imagen)

    # Cargar tipografías.
    try:
        fuente_titulo = ImageFont.truetype("arialbd.ttf", 29)
        fuente_tabla = ImageFont.truetype("arial.ttf", 21)
        fuente_negrita = ImageFont.truetype("arialbd.ttf", 21)
        fuente_nota = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        fuente_titulo = ImageFont.load_default()
        fuente_tabla = ImageFont.load_default()
        fuente_negrita = ImageFont.load_default()
        fuente_nota = ImageFont.load_default()

    # Encabezado compacto.
    dibujo.rounded_rectangle(
        (15, 15, 745, 105),
        radius=12,
        fill=encabezado
    )

    dibujo.text(
        (32, 27),
        "EVALUACIÓN ECONÓMICA",
        font=fuente_nota,
        fill=turquesa
    )

    dibujo.text(
        (32, 52),
        "Tabla de admisibilidad",
        font=fuente_titulo,
        fill=blanco
    )

    # Encabezados de columnas.
    dibujo.text(
        (30, 125),
        "Monto de solicitud (USD)",
        font=fuente_negrita,
        fill=secundario
    )

    dibujo.text(
        (565, 125),
        "Admisibilidad",
        font=fuente_negrita,
        fill=secundario
    )

    # Filas de la tabla.
    inicio_y = 165
    altura_fila = 37

    for indice, fila in enumerate(tabla_admisibilidad):

        y = inicio_y + indice * altura_fila

        dibujo.text(
            (30, y),
            fila["Monto de solicitud (USD)"],
            font=fuente_tabla,
            fill=blanco
        )

        dibujo.text(
            (610, y),
            fila["Admisibilidad"],
            font=fuente_negrita,
            fill=turquesa
        )

        dibujo.line(
            (25, y + 30, 735, y + 30),
            fill=linea,
            width=1
        )

    # Nota inferior.
    dibujo.text(
        (30, 520),
        "Porcentaje determinado según el monto de solicitud en USD.",
        font=fuente_nota,
        fill=secundario
    )

    # Convertir imagen a archivo descargable.
    archivo = BytesIO()
    imagen.save(archivo, format="PNG")
    archivo.seek(0)

    return archivo.getvalue()
