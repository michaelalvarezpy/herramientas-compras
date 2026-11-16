
import streamlit as st
import pandas as pd
import json

from Calculadora_Admisibilidad.Servicios.tipo_cambio import obtener_cotizaciones_monedas

# ============================================================
# FUNCIÓN AUXILIAR: VALIDACIÓN DEL RUT CHILENO
# ============================================================

def validar_rut_chileno(rut):
    """
    Verifica que un RUT chileno tenga un dígito verificador válido.
    Utiliza el algoritmo de módulo 11.
    """

    # Eliminar puntos, guiones y espacios externos.
    # Convertir la letra K a mayúscula.
    rut = str(rut).replace(".", "").replace("-", "").strip().upper()

    # Comprobar que exista un número y un dígito verificador.
    if len(rut) < 2 or not rut[:-1].isdigit():
        return False

    # Separar el número del dígito verificador ingresado.
    numero = rut[:-1]
    digito = rut[-1]

    # Preparar las variables para calcular el módulo 11.
    suma = 0
    multiplicador = 2

    # Multiplicar los dígitos de derecha a izquierda por 2, 3, 4, 5, 6 y 7.
    for caracter in reversed(numero):
        suma += int(caracter) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    # Calcular el dígito verificador esperado.
    resultado = 11 - (suma % 11)

    # Convertir el resultado a 0, K o un número del 1 al 9.
    if resultado == 11:
        digito_esperado = "0"
    elif resultado == 10:
        digito_esperado = "K"
    else:
        digito_esperado = str(resultado)

    # Comparar el dígito ingresado con el calculado.
    return digito == digito_esperado

# ============================================================
# FUNCIÓN AUXILIAR: FORMATO DEL RUT CHILENO
# ============================================================

def formatear_rut_chileno(rut):
    # Eliminar puntos, guiones y espacios del RUT ingresado.
    rut_limpio = str(rut).replace(".", "").replace("-", "").strip().upper()

    # Evitar aplicar formato a valores vacíos o incompletos.
    if len(rut_limpio) < 2:
        return rut_limpio

    # Separar el número del dígito verificador.
    numero = rut_limpio[:-1]
    digito = rut_limpio[-1]

    # Incorporar puntos cada tres dígitos desde la derecha.
    numero_formateado = f"{int(numero):,}".replace(",", ".")

    # Devolver el RUT con su formato chileno.
    return f"{numero_formateado}-{digito}"

def formatear_monto_chileno(monto):
    # Formato chileno: punto para miles y coma para decimales.
    monto_formateado = f"{monto:,.2f}"

    return (
        monto_formateado
        .replace(",", "TEMP")
        .replace(".", ",")
        .replace("TEMP", ".")
    )

def validar_detalle_cotizacion(tabla):
    """Devuelve una advertencia o None si las filas cotizadas son válidas."""
    import numpy as np

    if tabla.empty:
        return "Ingrese al menos un artículo con precio antes de guardar."

    precio = pd.to_numeric(tabla["Precio unitario"], errors="coerce")
    cantidad = pd.to_numeric(tabla["Cantidad cotizada"], errors="coerce")
    requerida = pd.to_numeric(tabla["Cantidad"], errors="coerce")
    plazo = pd.to_numeric(tabla["Plazo"], errors="coerce")

    if precio.isna().any() or not np.isfinite(precio).all() or precio.le(0).any():
        return "Revise los precios unitarios: deben ser números mayores que cero."
    if (cantidad.isna().any() or requerida.isna().any()
            or not np.isfinite(cantidad).all() or not np.isfinite(requerida).all()
            or cantidad.le(0).any() or requerida.le(0).any()
            or cantidad.gt(requerida).any()):
        return ("Revise las cantidades cotizadas: deben ser mayores que cero "
                "y no superar las cantidades solicitadas.")
    if not tabla["Moneda"].isin(["CLP", "USD", "EUR", "UF"]).all():
        return "Seleccione una moneda válida (CLP, USD, EUR o UF) en cada artículo."
    if plazo.isna().any() or not np.isfinite(plazo).all() or plazo.lt(0).any():
        return "Revise los plazos: deben ser números mayores o iguales a cero."
    if not tabla["Unidad plazo"].isin(["Días", "Semanas"]).all():
        return "Seleccione Días o Semanas para cada plazo de entrega."
    return None


# ============================================================
# MÓDULO: EVALUACIÓN COMPARATIVA DE OFERTAS
# ============================================================

def mostrar_evaluacion_ofertas():
    # Restaurar widgets antes de que Streamlit los cree en esta ejecución.
    pendiente = st.session_state.pop("evaluacion_restauracion_pendiente", None)
    if pendiente is not None:
        for clave, valor in pendiente.items():
            st.session_state[clave] = valor

    # ========================================================
    # ENCABEZADO PRINCIPAL
    # ========================================================

    st.title("⚖️ Evaluación Comparativa de Ofertas")

    st.caption(
        "Análisis económico de proveedores por artículo, "
        "con evaluación técnica y ponderaciones opcionales."
    )

    # ========================================================
    # 01 / ANTECEDENTES DE LA SOLICITUD
    # ========================================================

    st.subheader("01 / Antecedentes de la solicitud")

    col1, col2 = st.columns(2)

    with col1:
        numero_solicitud = st.text_input(
            "Número de solicitud de compra (opcional)",
            key="evaluacion_numero_solicitud"
        )

        moneda_solicitud = st.selectbox(
            "Moneda de la solicitud",
            ["CLP", "USD", "EUR", "UF"],
            key="evaluacion_moneda_solicitud"
        )

    with col2:
        monto_solicitud = st.number_input(
            "Monto total de la solicitud",
            min_value=0.0,
            step=1000.0,
            key="evaluacion_monto_solicitud"
        )

        modalidad_adjudicacion = st.selectbox(
            "Modalidad de comparación",
            [
                "Por artículo",
                "Por oferta total",
                "Ambas modalidades"
            ],
            key="evaluacion_modalidad"
        )

    st.info(
        "La evaluación económica será independiente de la "
        "validación técnica y de las ponderaciones posteriores."
    )
    
    # ========================================================
    # TIPOS DE CAMBIO PARA COMPARACIÓN ECONÓMICA
    # ========================================================

    # Los tipos de cambio se cargan una vez por sesión y no se sobreescriben
    # al editar manualmente otros campos de la evaluación.
    def cargar_cotizaciones_banco_central():
        try:
            usd, eur_usd, uf, fecha = obtener_cotizaciones_monedas()
            cotizaciones = {
                "evaluacion_usd": float(usd),
                "evaluacion_eur": float(usd * eur_usd),
                "evaluacion_uf": float(uf),
            }
            if not all(importe > 0 for importe in cotizaciones.values()):
                raise ValueError("Las cotizaciones deben ser positivas.")
            st.session_state.update(cotizaciones)
            st.session_state["evaluacion_fecha_tipo_cambio"] = str(fecha.date() if hasattr(fecha, "date") else fecha)
            st.session_state["evaluacion_origen_tipo_cambio"] = "Banco Central de Chile"
            st.session_state["evaluacion_tc_modificados"] = []
            st.session_state["evaluacion_error_tipo_cambio"] = ""
        except Exception as error:
            st.session_state["evaluacion_error_tipo_cambio"] = str(error)
            st.session_state["evaluacion_origen_tipo_cambio"] = "Manual / última cotización conservada"
            for clave in ("evaluacion_usd", "evaluacion_eur", "evaluacion_uf"):
                st.session_state.setdefault(clave, 0.0)

    if "evaluacion_usd" not in st.session_state or "evaluacion_eur" not in st.session_state or "evaluacion_uf" not in st.session_state:
        cargar_cotizaciones_banco_central()

    # PASO 7.90: rastrear qué monedas fueron ajustadas manualmente.
    def marcar_tipo_cambio_manual(moneda):
        modificados = set(st.session_state.get("evaluacion_tc_modificados", []))
        modificados.add(moneda)
        st.session_state["evaluacion_tc_modificados"] = sorted(modificados)

    def descripcion_origen_tipos_cambio():
        origen = st.session_state.get("evaluacion_origen_tipo_cambio", "Manual")
        modificados = st.session_state.get("evaluacion_tc_modificados", [])
        if not modificados:
            return origen
        return f"{origen} (referencia); ajuste manual: {', '.join(modificados)}"

    with st.expander("💱 Tipos de cambio de referencia"):
        st.caption(
            "Cotizaciones expresadas en pesos chilenos (CLP). "
            "Puedes modificarlas manualmente antes de comparar las ofertas."
        )
        if st.button("🔄 Actualizar desde Banco Central", key="evaluacion_actualizar_cotizaciones"):
            cargar_cotizaciones_banco_central()

        fecha_tc = st.session_state.get("evaluacion_fecha_tipo_cambio")
        origen_tc = descripcion_origen_tipos_cambio()
        if fecha_tc:
            st.caption(f"Fuente: {origen_tc} · Fecha de referencia: {fecha_tc}")
        else:
            st.caption(f"Fuente: {origen_tc} · Sin fecha automática disponible")
        if st.session_state.get("evaluacion_error_tipo_cambio"):
            st.warning(
                "No fue posible consultar el Banco Central. "
                "Ingresa los valores manualmente o conserva los últimos valores revisados."
            )

        col_usd, col_eur, col_uf = st.columns(3)
        with col_usd:
            valor_usd = st.number_input(
                "1 USD en CLP", min_value=0.0, step=1.0,
                format="%.4f", key="evaluacion_usd",
                on_change=marcar_tipo_cambio_manual, args=("USD",)
            )
        with col_eur:
            valor_eur = st.number_input(
                "1 EUR en CLP", min_value=0.0, step=1.0,
                format="%.4f", key="evaluacion_eur",
                on_change=marcar_tipo_cambio_manual, args=("EUR",)
            )
        with col_uf:
            valor_uf = st.number_input(
                "1 UF en CLP", min_value=0.0, step=100.0,
                format="%.4f", key="evaluacion_uf",
                on_change=marcar_tipo_cambio_manual, args=("UF",)
            )

    if any(v <= 0 for v in (valor_usd, valor_eur, valor_uf)):
        st.warning("Completa los tres tipos de cambio con valores mayores a cero antes de comparar ofertas.")
        st.stop()

    # Equivalencia de cada moneda expresada en pesos chilenos.
    tipos_cambio_clp = {
        "CLP": 1.0,
        "USD": valor_usd,
        "EUR": valor_eur,
        "UF": valor_uf
    }

    # ========================================================
    # 02 / ARTÍCULOS DE LA SOLICITUD
    # ========================================================

    st.subheader("02 / Artículos de la solicitud")

    st.caption(
        "Ingrese los artículos requeridos. Puede agregar "
        "tantas filas como necesite."
    )

    if "articulos_solicitud" not in st.session_state:
        st.session_state["articulos_solicitud"] = pd.DataFrame({
            "Código de artículo": [""],
            "Descripción": [""],
            "Cantidad": [1.0],
            "Unidad de medida": ["UN"]
        })

    tabla_articulos = st.data_editor(
        st.session_state["articulos_solicitud"],
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_config={
            "Código de artículo": st.column_config.TextColumn(
                "Código de artículo"
            ),
            "Descripción": st.column_config.TextColumn(
                "Descripción",
                required=True
            ),
            "Cantidad": st.column_config.NumberColumn(
                "Cantidad",
                min_value=0.01,
                step=1.0,
                default=1.0,
                required=True
            ),
            "Unidad de medida": st.column_config.TextColumn(
                "Unidad de medida",
                default="UN",
                required=True
            )
        },
        key="editor_articulos_solicitud"
    )

    articulos_validos = tabla_articulos[
        tabla_articulos["Descripción"].fillna("").str.strip().ne("")
        & tabla_articulos["Cantidad"].notna()
        & tabla_articulos["Cantidad"].gt(0)
        & tabla_articulos["Unidad de medida"].fillna("").str.strip().ne("")
    ]
    
    # Identificación interna de artículos para comparar ofertas.
    articulos_validos = articulos_validos.copy()

    articulos_validos.insert(
        0,
        "Ítem",
        articulos_validos.index + 1
    )

    st.caption(
        f"Artículos registrados correctamente: "
        f"{len(articulos_validos)}"
    )
    
    # ========================================================
    # 03 / REGISTRO DE PROVEEDORES
    # ========================================================

    st.divider()

    st.subheader("03 / Registro de proveedores")

    st.caption(
        "Ingrese los proveedores que participan en la "
        "evaluación. Puede agregar tantos como necesite."
    )

    if "proveedores_evaluacion" not in st.session_state:
        st.session_state["proveedores_evaluacion"] = pd.DataFrame({
            "RUT": [""],
            "Proveedor": [""]
        })
    elif "RUT" not in st.session_state["proveedores_evaluacion"].columns:
        st.session_state["proveedores_evaluacion"].insert(
            0, "RUT", ""
        )

    tabla_proveedores = st.data_editor(
        st.session_state["proveedores_evaluacion"],
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_config={
            "RUT": st.column_config.TextColumn(
                "RUT del proveedor",
                help="Ejemplo: 12.345.678-9"
            ),
            "Proveedor": st.column_config.TextColumn(
                "Nombre del proveedor",
                required=True
            )
        },
        # Identificar el editor mediante su versión de formato.
        # Esto permitirá actualizar la visualización de los RUT
        # sin modificar los artículos ni las cotizaciones.
        key="editor_proveedores_evaluacion_estable"
    )

    # ========================================================
    # CONSERVAR EDICIONES SIN RECREAR EL EDITOR
    # ========================================================
    # El editor dinámico puede mostrar una fila nueva con índice None
    # mientras se está editando. No reiniciar su clave ni llamar st.rerun()
    # por formateo: eso puede descartar la fila antes de confirmarla.
    tabla_proveedores = tabla_proveedores.copy().reset_index(drop=True)
    for columna in ("RUT", "Proveedor"):
        tabla_proveedores[columna] = tabla_proveedores[columna].fillna("").astype(str)

    # Guardar todas las filas, incluso las incompletas, para que el
    # usuario pueda terminarlas en una edición posterior.
    st.session_state["proveedores_evaluacion"] = tabla_proveedores.copy()

    # Normalizar solo una COPIA para exportación y respaldo JSON.
    # El editor conserva el texto introducido, evitando perder el foco.
    tabla_proveedores_formateada = tabla_proveedores.copy()
    tabla_proveedores_formateada["RUT"] = (
        tabla_proveedores_formateada["RUT"].apply(
            lambda rut: formatear_rut_chileno(rut)
            if len(str(rut).replace(".", "").replace("-", "").strip()) >= 2
            and str(rut).replace(".", "").replace("-", "").strip()[:-1].isdigit()
            else rut
        )
    )

    # ========================================================
    # VALIDACIÓN DE PROVEEDORES REGISTRADOS
    # ========================================================

    # Comprobar que el proveedor tenga nombre y RUT ingresados.
    # Además, verificar que el dígito verificador del RUT sea correcto.
    proveedores_validos = tabla_proveedores[
        tabla_proveedores["Proveedor"].fillna("").str.strip().ne("")
        & tabla_proveedores["RUT"].fillna("").str.strip().ne("")
        & tabla_proveedores["RUT"].apply(validar_rut_chileno)
    ].copy()

    # ========================================================
    # ADVERTENCIA DE RUT INCORRECTO
    # ========================================================

    # Identificar los proveedores que tienen un RUT ingresado,
    # pero cuyo dígito verificador no es válido.
    proveedores_rut_invalidos = tabla_proveedores[
        tabla_proveedores["RUT"].fillna("").str.strip().ne("")
        & ~tabla_proveedores["RUT"].apply(validar_rut_chileno)
    ]

    # Mostrar una advertencia cuando existan RUT incorrectos.
    if not proveedores_rut_invalidos.empty:
        st.warning(
            f"⚠️ Se detectaron {len(proveedores_rut_invalidos)} "
            "proveedor(es) con RUT incorrecto. "
            "Revise los siguientes registros:"
        )

        # Mostrar únicamente el RUT y nombre de los proveedores
        # que necesitan una corrección.
        st.dataframe(
            proveedores_rut_invalidos[["RUT", "Proveedor"]],
            hide_index=True,
            width="stretch"
        )
        
        # ========================================================
    # DETECCIÓN DE RUT DUPLICADOS
    # ========================================================

    # Crear una copia de los proveedores válidos para revisar
    # si existen RUT repetidos en el registro.
    proveedores_revision = proveedores_validos.copy()

    # Normalizar los RUT eliminando puntos, guiones y espacios.
    # Esto permite identificar duplicados con distinto formato.
    proveedores_revision["RUT normalizado"] = (
        proveedores_revision["RUT"]
        .str.replace(".", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.strip()
        .str.upper()
    )

    # Identificar los registros que comparten un mismo RUT.
    proveedores_duplicados = proveedores_revision[
        proveedores_revision["RUT normalizado"].duplicated(keep=False)
    ]

    # Informar al usuario cuando existan proveedores duplicados.
    if not proveedores_duplicados.empty:
        st.warning(
            "Se detectaron proveedores con RUT duplicado. "
            "Revise los siguientes registros:"
        )

        # Mostrar los proveedores que tienen el mismo RUT.
        st.dataframe(
            proveedores_duplicados[["RUT", "Proveedor"]],
            hide_index=True,
            width="stretch"
        )

    # Mostrar la cantidad de proveedores correctamente registrados.
    st.caption(
        f"Proveedores registrados: {len(proveedores_validos)}"
    )
    
    # ========================================================
    # 04 / COTIZACIONES POR PROVEEDOR
    # ========================================================

    st.divider()

    st.subheader("04 / Cotizaciones por proveedor")

    st.caption(
        "Seleccione un proveedor para registrar los artículos "
        "cotizados y sus respectivas alternativas."
    )

    if articulos_validos.empty or proveedores_validos.empty:
        st.info(
            "Primero registre al menos un artículo y un proveedor "
            "para ingresar sus cotizaciones."
        )
    else:
        opciones_proveedores = (
            proveedores_validos["Proveedor"]
            .str.strip()
            .drop_duplicates()
            .tolist()
        )

        st.markdown("#### Datos de la cotización")

        col_proveedor, col_cotizacion = st.columns(2)

        with col_proveedor:
            proveedor_seleccionado = st.selectbox(
                "Seleccione el proveedor",
                options=opciones_proveedores,
                key="proveedor_cotizacion"
            )

        with col_cotizacion:
            numero_cotizacion = st.text_input(
                "Número de cotización (opcional)",
                placeholder="Ejemplo: COT-125",
                key=f"numero_cotizacion_{proveedor_seleccionado}"
            )

        rut_proveedor_seleccionado = proveedores_validos.loc[
            proveedores_validos["Proveedor"].str.strip()
            == proveedor_seleccionado,
            "RUT"
        ].iloc[0]

        st.caption(
            f"Proveedor seleccionado: {proveedor_seleccionado} "
            f"| RUT: {rut_proveedor_seleccionado}"
        )
        
        # ====================================================
        # ARTÍCULOS DISPONIBLES PARA COTIZAR
        # ====================================================

        st.markdown("#### Artículos de la solicitud")

        st.caption(
            "Los siguientes artículos corresponden a la "
            "solicitud de compra y estarán disponibles "
            "para registrar la oferta del proveedor seleccionado."
        )

        columnas_articulos = [
            "Ítem",
            "Código de artículo",
            "Descripción",
            "Cantidad",
            "Unidad de medida"
        ]

        tabla_base_cotizacion = articulos_validos[
            columnas_articulos
        ].copy()

        # ====================================================
        # IDENTIFICACIÓN DE ALTERNATIVAS POR ARTÍCULO
        # ====================================================

        # Cada artículo comienza con una alternativa A.
        # Las alternativas adicionales se incorporarán después
        # mediante un botón, sin modificar la solicitud original.
        tabla_base_cotizacion["Alternativa"] = "A"

        # La cantidad cotizada comienza con la cantidad solicitada,
        # pero podrá modificarse si el proveedor ofrece menos unidades.
        tabla_base_cotizacion["Cantidad cotizada"] = (
            tabla_base_cotizacion["Cantidad"].copy()
        )

        # Preparar los demás datos comerciales de cada alternativa.
        tabla_base_cotizacion["Marca / Modelo"] = ""
        tabla_base_cotizacion["Precio unitario"] = None
        tabla_base_cotizacion["Moneda"] = moneda_solicitud
        tabla_base_cotizacion["Plazo"] = None
        tabla_base_cotizacion["Unidad plazo"] = None

        # ====================================================
        # ALMACENAMIENTO TEMPORAL DE ALTERNATIVAS
        # ====================================================

        # Crear un espacio para almacenar las alternativas
        # adicionales de cada cotización durante la sesión.
        if "alternativas_cotizaciones" not in st.session_state:
            st.session_state["alternativas_cotizaciones"] = {}

        # Identificar cada cotización mediante el proveedor
        # y su número, para no mezclar alternativas de ofertas distintas.
        clave_alternativas = (
            proveedor_seleccionado,
            numero_cotizacion.strip()
        )

        # Inicializar la cotización con sus artículos originales
        # únicamente cuando todavía no tenga una tabla registrada.
        if clave_alternativas not in st.session_state["alternativas_cotizaciones"]:
            st.session_state["alternativas_cotizaciones"][
                clave_alternativas
            ] = tabla_base_cotizacion.copy()

        # Mostrar los artículos y alternativas correspondientes
        # exclusivamente al proveedor y cotización seleccionados.
        tabla_oferta_editada = st.data_editor(
            st.session_state["alternativas_cotizaciones"][clave_alternativas],
            hide_index=True,
            num_rows="fixed",
            width="stretch",
            # Bloquear los datos originales y la letra de alternativa.
            # Las alternativas se asignan automáticamente con el botón.
            disabled=columnas_articulos + ["Alternativa"],
            column_config={
                # Permitir ingresar la cantidad realmente ofertada.
                # Puede ser menor que la cantidad solicitada.
                "Cantidad cotizada": st.column_config.NumberColumn(
                    "Cantidad cotizada",
                    min_value=0.01,
                    step=1.0,
                    required=True
                ),
                "Precio unitario": st.column_config.NumberColumn(
                    "Precio unitario",
                    min_value=0.01
                ),
                "Moneda": st.column_config.SelectboxColumn(
                    "Moneda",
                    options=["CLP", "USD", "EUR", "UF"],
                    required=True
                ),
                "Plazo": st.column_config.NumberColumn(
                    "Plazo",
                    min_value=0,
                    step=1
                ),
                "Unidad plazo": st.column_config.SelectboxColumn(
                    "Unidad plazo",
                    options=["Días", "Semanas"]
                )
            },
            # Identificar el editor por cotización y cantidad de filas.
            # Cuando se agregue una alternativa, Streamlit creará
            # una nueva versión del editor y mostrará la fila adicional.
            key=(
                f"editor_oferta_{clave_alternativas}_"
                f"{len(st.session_state['alternativas_cotizaciones'][clave_alternativas])}"
            )
        )
        
        # ====================================================
        # CONSERVAR LOS DATOS EDITADOS DE LA COTIZACIÓN
        # ====================================================

        # Actualizar la tabla temporal con los precios, marcas
        # y plazos ingresados por el usuario.
        # Así, al agregar nuevas alternativas, podremos conservar
        # la información de las filas que ya fueron completadas.
        st.session_state["alternativas_cotizaciones"][
            clave_alternativas
        ] = tabla_oferta_editada.copy()

        # ====================================================
        # SELECCIONAR ARTÍCULO PARA AGREGAR ALTERNATIVA
        # ====================================================

        # Mostrar únicamente los artículos originales de la solicitud.
        # Esto evita que una alternativa ya creada aparezca
        # como si fuera un artículo diferente.
        opciones_items = articulos_validos["Ítem"].tolist()

        # Permitir seleccionar el artículo al que se desea
        # incorporar una segunda o tercera opción comercial.
        item_para_alternativa = st.selectbox(
            "¿Qué artículo tiene otra alternativa?",
            options=opciones_items,
            format_func=lambda item: (
                f"Ítem {item} — "
                f"{articulos_validos.loc[articulos_validos['Ítem'] == item, 'Descripción'].iloc[0]}"
            ),
            key=f"item_alternativa_{clave_alternativas}"
        )

        # ====================================================
        # AGREGAR NUEVA ALTERNATIVA AL ARTÍCULO
        # ====================================================

        # Crear una alternativa únicamente para el artículo
        # seleccionado, conservando los demás artículos.
        if st.button(
            "➕ Agregar alternativa",
            key=f"agregar_alternativa_{clave_alternativas}"
        ):

            # Recuperar la tabla actual de esta cotización.
            tabla_actual = st.session_state[
                "alternativas_cotizaciones"
            ][clave_alternativas].copy()

            # Identificar las alternativas existentes del artículo.
            alternativas_item = tabla_actual.loc[
                tabla_actual["Ítem"] == item_para_alternativa,
                "Alternativa"
            ].tolist()

            # Calcular la siguiente letra disponible: B, C, D...
            letras_usadas = [
                str(letra).strip().upper()
                for letra in alternativas_item
            ]

            siguiente_letra = chr(
                ord("A") + len(letras_usadas)
            )

            # Copiar los datos originales del artículo seleccionado.
            nueva_alternativa = tabla_base_cotizacion.loc[
                tabla_base_cotizacion["Ítem"] == item_para_alternativa
            ].copy()

            # Asignar la letra correspondiente a la nueva opción.
            nueva_alternativa["Alternativa"] = siguiente_letra

            # Incorporar la nueva alternativa a la cotización.
            st.session_state["alternativas_cotizaciones"][
                clave_alternativas
            ] = pd.concat(
                [tabla_actual, nueva_alternativa],
                ignore_index=True
            )

            # Actualizar la pantalla para mostrar la nueva fila.
            st.rerun()

        # ====================================================
        # GUARDAR COTIZACIÓN DEL PROVEEDOR
        # ====================================================

        if "ofertas_guardadas" not in st.session_state:
            st.session_state["ofertas_guardadas"] = {}

        if st.button(
            "💾 Guardar cotización",
            type="primary",
            key="guardar_cotizacion_proveedor"
        ):
            ofertas_con_precio = tabla_oferta_editada[
                tabla_oferta_editada["Precio unitario"].notna()
            ].copy()

            advertencia = validar_detalle_cotizacion(ofertas_con_precio)
            if advertencia:
                st.warning(advertencia)
            else:
                clave_oferta = (
                    proveedor_seleccionado,
                    numero_cotizacion.strip()
                )

                st.session_state["ofertas_guardadas"][
                    clave_oferta
                ] = ofertas_con_precio.copy()

                st.success(
                    f"Cotización guardada: {proveedor_seleccionado} "
                    f"({ofertas_con_precio['Ítem'].nunique()} "
                    "artículos cotizados)."
                )

        # ====================================================
        # RESUMEN DE COTIZACIONES GUARDADAS
        # ====================================================

        st.markdown("#### Cotizaciones registradas")
        
        # ====================================================
        # SELECCIONAR COTIZACIÓN PARA EDITAR
        # ====================================================

        claves_guardadas = list(
            st.session_state["ofertas_guardadas"].keys()
        )

        if claves_guardadas:
            cotizacion_para_editar = st.selectbox(
                "Seleccione una cotización para editar",
                options=claves_guardadas,
                format_func=lambda clave: (
                    f"{clave[0]} — "
                    f"{clave[1] or 'Sin número'}"
                ),
                index=None,
                placeholder="Seleccione una cotización guardada",
                key="cotizacion_para_editar"
            )

            if cotizacion_para_editar is not None:
                st.info(
                    "Cotización seleccionada: "
                    f"{cotizacion_para_editar[0]} — "
                    f"{cotizacion_para_editar[1] or 'Sin número'}"
                )

                oferta_seleccionada = st.session_state[
                    "ofertas_guardadas"
                ][cotizacion_para_editar].copy()

                st.markdown("##### Detalle de la oferta guardada")

                oferta_modificada = st.data_editor(
                    oferta_seleccionada,
                    hide_index=True,
                    num_rows="fixed",
                    width="stretch",
                    # Proteger los datos originales del artículo
                    # y la identificación automática de la alternativa.
                    disabled=[
                        "Ítem",
                        "Código de artículo",
                        "Descripción",
                        "Cantidad",
                        "Unidad de medida",
                        "Alternativa"
                    ],
                    column_config={
                        # Permitir corregir la cantidad cotizada
                        # en una oferta previamente guardada.
                        "Cantidad cotizada": st.column_config.NumberColumn(
                            "Cantidad cotizada",
                            min_value=0.01,
                            step=1.0,
                            required=True
                        ),
                        "Precio unitario": st.column_config.NumberColumn(
                            "Precio unitario",
                            min_value=0.01
                        ),
                        "Moneda": st.column_config.SelectboxColumn(
                            "Moneda",
                            options=["CLP", "USD", "EUR", "UF"],
                            required=True
                        ),
                        "Plazo": st.column_config.NumberColumn(
                            "Plazo",
                            min_value=0,
                            step=1
                        ),
                        "Unidad plazo": st.column_config.SelectboxColumn(
                            "Unidad plazo",
                            options=["Días", "Semanas"]
                        )
                    },
                    key=f"editar_oferta_{cotizacion_para_editar}"
                )

                if st.button(
                    "💾 Actualizar cotización",
                    type="primary",
                    key="actualizar_cotizacion"
                ):
                    advertencia = validar_detalle_cotizacion(oferta_modificada)
                    if advertencia:
                        st.warning(advertencia)
                    else:
                        st.session_state["ofertas_guardadas"][
                            cotizacion_para_editar
                        ] = oferta_modificada.copy()

                        st.success(
                            "Cotización actualizada correctamente."
                        )
                        st.rerun()

        if not st.session_state["ofertas_guardadas"]:
            st.info("Todavía no hay cotizaciones guardadas.")
        else:
            resumen_ofertas = []

            for clave, oferta in st.session_state[
                "ofertas_guardadas"
            ].items():
                proveedor, numero = clave

                coincidencias_rut = proveedores_validos.loc[
                    proveedores_validos["Proveedor"].str.strip() == proveedor,
                    "RUT"
                ]

                rut_proveedor = (
                    coincidencias_rut.iloc[0]
                    if not coincidencias_rut.empty
                    else "No disponible"
                )
                
                # Verificar si la oferta cubre todos los artículos
                # y las cantidades originales de la solicitud.
                cobertura_por_item = (
                    oferta.groupby("Ítem")
                    .apply(
                        lambda grupo: (
                            grupo["Cantidad cotizada"]
                            >= grupo["Cantidad"]
                        ).any(),
                        include_groups=False
                    )
                )

                oferta_completa = (
                    len(cobertura_por_item) == len(articulos_validos)
                    and cobertura_por_item.all()
                    and set(oferta["Ítem"]) == set(articulos_validos["Ítem"])
                )

                estado_oferta = (
                    "Completa" if oferta_completa else "Parcial"
                )

                # Preparar los precios convertidos de esta cotización.
                oferta_convertida = oferta.copy()

                # Convertir cada precio a la moneda de la solicitud.
                oferta_convertida["Precio unitario convertido"] = (
                    oferta_convertida["Precio unitario"]
                    * oferta_convertida["Moneda"].map(tipos_cambio_clp)
                    / tipos_cambio_clp[moneda_solicitud]
                )

                resumen_ofertas.append({
                    "RUT": rut_proveedor,
                    "Proveedor": proveedor,
                    "N° cotización": numero or "Sin número",
                    # Contar artículos únicos, sin duplicar las
                    # alternativas A, B, C de un mismo artículo.
                    "Artículos cotizados": oferta["Ítem"].nunique(),
                    "Estado de oferta": estado_oferta,
                    "Moneda": (
                        oferta["Moneda"].iloc[0]
                        if oferta["Moneda"].nunique() == 1
                        else "Varias monedas"
                    ),
                    "Moneda del total": moneda_solicitud,

                    # Calcular el total en la moneda de la solicitud.
                    # Considerar la alternativa completa más económica
                    # de cada artículo, utilizando precios convertidos.
                    "Total neto mínimo (alternativas)": (
                        oferta_convertida.loc[
                            oferta_convertida["Cantidad cotizada"]
                            >= oferta_convertida["Cantidad"]
                        ]
                        .assign(
                            subtotal=lambda datos: (
                                datos["Precio unitario convertido"]
                                * datos["Cantidad cotizada"]
                            )
                        )
                        .groupby("Ítem")["subtotal"]
                        .min()
                        .sum()
                        if oferta_completa
                        else None
                    )
                })

            st.dataframe(
                pd.DataFrame(resumen_ofertas),
                hide_index=True,
                width="stretch"
            )

            # Informar cuando una cotización utiliza varias monedas.
            if any(
                registro["Moneda"] == "Varias monedas"
                for registro in resumen_ofertas
            ):
                st.info(
                    "Existen cotizaciones con artículos expresados en "
                    "distintas monedas. Los totales de las ofertas "
                    "completas se han calculado utilizando los tipos "
                    "de cambio de referencia ingresados y están "
                    f"expresados en {moneda_solicitud}."
                )

            # Advertir cuando existan cotizaciones parciales.
            # No calcular un total comparable si faltan artículos
            # o cantidades solicitadas.
            if any(
                registro["Estado de oferta"] == "Parcial"
                for registro in resumen_ofertas
            ):
                st.warning(
                    "Existen cotizaciones parciales que no cubren "
                    "todos los artículos o cantidades solicitadas. "
                    "Por este motivo, no se calcula un total neto "
                    "comparable para estas cotizaciones. "
                    "Revise sus artículos en la comparación individual."
                )
                
            # ====================================================
            # 05 / COMPARACIÓN ECONÓMICA POR ARTÍCULO
            # ====================================================

            st.divider()

            st.subheader("05 / Comparación económica por artículo")

            st.caption(
                "Compare las alternativas cotizadas por los "
                "proveedores para cada artículo de la solicitud."
            )
            
            # Reunir todas las cotizaciones guardadas.
            tablas_comparacion = []

            for clave, oferta in st.session_state[
                "ofertas_guardadas"
            ].items():
                proveedor, numero = clave

                detalle_oferta = oferta.copy()
                detalle_oferta["Proveedor"] = proveedor
                detalle_oferta["N° cotización"] = (
                    numero or "Sin número"
                )

                tablas_comparacion.append(detalle_oferta)

            tabla_comparacion = pd.concat(
                tablas_comparacion,
                ignore_index=True
            )
            
            # Calcular el subtotal neto de cada alternativa.
            tabla_comparacion["Subtotal neto"] = (
                tabla_comparacion["Precio unitario"]
                * tabla_comparacion["Cantidad cotizada"]
            )
            
            # Convertir el precio unitario a la moneda de la solicitud.
            tabla_comparacion["Precio unitario convertido"] = (
                tabla_comparacion["Precio unitario"]
                * tabla_comparacion["Moneda"].map(tipos_cambio_clp)
                / tipos_cambio_clp[moneda_solicitud]
            )
            
            # Calcular el subtotal en la moneda de la solicitud.
            tabla_comparacion["Subtotal neto convertido"] = (
                tabla_comparacion["Precio unitario convertido"]
                * tabla_comparacion["Cantidad cotizada"]
            )
            
            # Convertir los plazos a días para compararlos.
            tabla_comparacion["Plazo (días)"] = (
                tabla_comparacion["Plazo"]
                * tabla_comparacion["Unidad plazo"].map({
                    "Días": 1,
                    "Semanas": 7
                })
            )
            
            # Identificar la cobertura de cada alternativa.
            tabla_comparacion["Cobertura"] = (
                tabla_comparacion["Cantidad cotizada"]
                >= tabla_comparacion["Cantidad"]
            ).map({True: "Completa", False: "Parcial"})
            
            # ====================================================
            # PROPUESTA DE ADJUDICACIÓN POR MENOR PRECIO
            # ====================================================

            # Considerar solamente alternativas con cobertura completa.
            ofertas_para_adjudicacion = tabla_comparacion[
                tabla_comparacion["Cobertura"] == "Completa"
            ].copy()

            # Ordenar por artículo, menor subtotal y menor plazo
            # para resolver empates económicos de forma consistente.
            ofertas_para_adjudicacion = ofertas_para_adjudicacion.sort_values(
                by=["Ítem", "Subtotal neto convertido", "Plazo (días)"],
                ascending=[True, True, True],
                kind="stable"
            )

            # Seleccionar una alternativa por cada artículo.
            propuesta_por_precio = ofertas_para_adjudicacion.drop_duplicates(
                subset=["Ítem"],
                keep="first"
            ).copy()

            # Calcular el total de la propuesta en moneda de solicitud.
            total_propuesta_precio = (
                propuesta_por_precio["Subtotal neto convertido"].sum()
            )
            
            # ====================================================
            # PROPUESTA DE ADJUDICACIÓN POR MENOR PLAZO
            # ====================================================

            # Utilizar solamente ofertas con cobertura completa.
            ofertas_para_plazo = tabla_comparacion[
                tabla_comparacion["Cobertura"] == "Completa"
            ].copy()

            # Priorizar el menor plazo y, en caso de empate,
            # seleccionar la alternativa de menor precio.
            ofertas_para_plazo = ofertas_para_plazo.sort_values(
                by=["Ítem", "Plazo (días)", "Subtotal neto convertido"],
                ascending=[True, True, True],
                kind="stable"
            )

            # Seleccionar una alternativa por cada artículo.
            propuesta_por_plazo = ofertas_para_plazo.drop_duplicates(
                subset=["Ítem"],
                keep="first"
            ).copy()

            # Calcular el total neto de la propuesta por plazo.
            total_propuesta_plazo = (
                propuesta_por_plazo["Subtotal neto convertido"].sum()
            )

            # Diferencia económica entre las dos propuestas.
            diferencia_precio_plazo = (
                total_propuesta_plazo - total_propuesta_precio
            )
            
            # ====================================================
            # ENCABEZADO DEL INFORME COMPARATIVO
            # ====================================================

            st.markdown("### 📊 Resumen de evaluación comercial")

            st.caption(
                "Comparación referencial de precios y plazos de entrega. "
                "Los resultados consideran únicamente alternativas "
                "con cobertura completa por artículo."
            )

            total_items_evaluados = len(propuesta_por_precio)
            total_items_solicitados = len(articulos_validos)

            evaluacion_completa = (
                total_items_evaluados == total_items_solicitados
            )

            col_presupuesto, col_precio, col_plazo = st.columns(3)

            with col_presupuesto:
                st.metric(
                    "Presupuesto de la solicitud",
                    f"{formatear_monto_chileno(monto_solicitud)} "
                    f"{moneda_solicitud}"
                )

            with col_precio:
                st.metric(
                    "Propuesta de menor precio",
                    f"{formatear_monto_chileno(total_propuesta_precio)} "
                    f"{moneda_solicitud}"
                )

            with col_plazo:
                st.metric(
                    "Propuesta de menor plazo",
                    f"{formatear_monto_chileno(total_propuesta_plazo)} "
                    f"{moneda_solicitud}"
                )

            if not evaluacion_completa:
                st.warning(
                    f"Evaluación incompleta: existen ofertas completas "
                    f"para {total_items_evaluados} de "
                    f"{total_items_solicitados} artículos. "
                    "Los totales mostrados son parciales y todavía "
                    "no deben compararse con el presupuesto total."
                )

            st.divider()
            
            # ====================================================
            # INFORME DE PROPUESTA ECONÓMICA POR ARTÍCULO
            # ====================================================

            st.markdown("### 📋 Propuesta económica por artículo")

            st.caption(
                "Selección referencial de la alternativa de menor "
                "precio por artículo, considerando cobertura completa. "
                "Pendiente de evaluación de admisibilidad y validación técnica."
            )

            if not propuesta_por_precio.empty:

                columnas_propuesta = [
                    "Ítem",
                    "Código de artículo",
                    "Descripción",
                    "Proveedor",
                    "N° cotización",
                    "Alternativa",
                    "Cantidad",
                    "Unidad de medida",
                    "Precio unitario convertido",
                    "Subtotal neto convertido",
                    "Plazo (días)"
                ]

                st.dataframe(
                    propuesta_por_precio[columnas_propuesta],
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Precio unitario convertido": st.column_config.NumberColumn(
                            f"Precio unitario ({moneda_solicitud})",
                            format="%.2f"
                        ),
                        "Subtotal neto convertido": st.column_config.NumberColumn(
                            f"Total neto ({moneda_solicitud})",
                            format="%.2f"
                        )
                    }
                )

                items_sin_propuesta = (
                    len(articulos_validos) - len(propuesta_por_precio)
                )

                if items_sin_propuesta > 0:
                    st.warning(
                        f"{items_sin_propuesta} artículo(s) todavía no "
                        "tienen una oferta con cobertura completa."
                    )

            else:
                st.warning(
                    "No existen ofertas completas para generar "
                    "una propuesta económica."
                )
                
            # ====================================================
            # INFORME DE PROPUESTA POR MENOR PLAZO DE ENTREGA
            # ====================================================

            st.markdown("### 🚚 Propuesta por menor plazo de entrega")

            st.caption(
                "Selección referencial de la alternativa con menor "
                "plazo de entrega por artículo. En caso de empate, "
                "se prioriza el menor precio. Pendiente de "
                "validación técnica y admisibilidad."
            )

            if not propuesta_por_plazo.empty:

                st.dataframe(
                    propuesta_por_plazo[columnas_propuesta],
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Precio unitario convertido": st.column_config.NumberColumn(
                            f"Precio unitario ({moneda_solicitud})",
                            format="%.2f"
                        ),
                        "Subtotal neto convertido": st.column_config.NumberColumn(
                            f"Total neto ({moneda_solicitud})",
                            format="%.2f"
                        )
                    }
                )

            else:
                st.warning(
                    "No existen ofertas completas para generar "
                    "una propuesta por menor plazo."
                )

            st.divider()
            
            # ====================================================
            # DIFERENCIA ECONÓMICA ENTRE AMBAS PROPUESTAS
            # ====================================================

            st.markdown("### 💰 Comparación de escenarios de compra")

            if evaluacion_completa and total_propuesta_precio > 0:

                diferencia_porcentaje = (
                    diferencia_precio_plazo
                    / total_propuesta_precio
                    * 100
                )

                col_diferencia, col_porcentaje = st.columns(2)

                with col_diferencia:
                    st.metric(
                        "Costo adicional por priorizar el plazo",
                        f"{formatear_monto_chileno(diferencia_precio_plazo)} "
                        f"{moneda_solicitud}"
                    )

                with col_porcentaje:
                    st.metric(
                        "Incremento respecto a la propuesta económica",
                        f"{formatear_monto_chileno(diferencia_porcentaje)}%"
                    )

                st.caption(
                    "La diferencia corresponde al costo adicional "
                    "de seleccionar las alternativas de menor plazo "
                    "en lugar de las alternativas de menor precio."
                )

            else:
                st.info(
                    "La comparación económica de escenarios estará "
                    "disponible cuando todos los artículos tengan "
                    "ofertas completas."
                )

            st.divider()
            
            # ====================================================
            # COMPARACIÓN DE PLAZOS Y COSTOS POR ARTÍCULO
            # ====================================================

            st.markdown("### ⏱️ Impacto del plazo por artículo")

            if evaluacion_completa:

                comparacion_plazos = propuesta_por_precio[
                    [
                        "Ítem",
                        "Descripción",
                        "Plazo (días)",
                        "Subtotal neto convertido"
                    ]
                ].merge(
                    propuesta_por_plazo[
                        [
                            "Ítem",
                            "Plazo (días)",
                            "Subtotal neto convertido"
                        ]
                    ],
                    on="Ítem",
                    suffixes=("_precio", "_plazo")
                )

                comparacion_plazos["Días ahorrados"] = (
                    comparacion_plazos["Plazo (días)_precio"]
                    - comparacion_plazos["Plazo (días)_plazo"]
                )

                comparacion_plazos["Costo adicional"] = (
                    comparacion_plazos["Subtotal neto convertido_plazo"]
                    - comparacion_plazos["Subtotal neto convertido_precio"]
                )

                comparacion_plazos = comparacion_plazos.rename(
                    columns={
                        "Plazo (días)_precio": "Plazo menor precio (días)",
                        "Plazo (días)_plazo": "Plazo menor entrega (días)",
                        "Subtotal neto convertido_precio": "Costo menor precio",
                        "Subtotal neto convertido_plazo": "Costo menor plazo"
                    }
                )

                st.dataframe(
                    comparacion_plazos[
                        [
                            "Ítem",
                            "Descripción",
                            "Plazo menor precio (días)",
                            "Plazo menor entrega (días)",
                            "Días ahorrados",
                            "Costo adicional"
                        ]
                    ],
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Costo adicional": st.column_config.NumberColumn(
                            f"Costo adicional ({moneda_solicitud})",
                            format="%.2f"
                        )
                    }
                )

                st.caption(
                    "Los días ahorrados se calculan individualmente "
                    "por artículo y no deben sumarse como si fueran "
                    "una reducción del plazo total de la compra."
                )

            else:
                st.info(
                    "La comparación de plazos estará disponible "
                    "cuando todos los artículos tengan ofertas completas."
                )

            st.divider()
            
            # ====================================================
            # COMPARACIÓN CON EL PRESUPUESTO DE LA SOLICITUD
            # ====================================================

            st.markdown("### 📑 Comparación con el presupuesto")

            if evaluacion_completa and monto_solicitud > 0:

                diferencia_presupuesto_precio = (
                    total_propuesta_precio - monto_solicitud
                )

                diferencia_presupuesto_plazo = (
                    total_propuesta_plazo - monto_solicitud
                )

                variacion_presupuesto_precio = (
                    diferencia_presupuesto_precio
                    / monto_solicitud * 100
                )

                variacion_presupuesto_plazo = (
                    diferencia_presupuesto_plazo
                    / monto_solicitud * 100
                )

                tabla_presupuesto = pd.DataFrame({
                    "Escenario": [
                        "Menor precio",
                        "Menor plazo"
                    ],
                    "Total propuesta": [
                        total_propuesta_precio,
                        total_propuesta_plazo
                    ],
                    "Presupuesto": [
                        monto_solicitud,
                        monto_solicitud
                    ],
                    "Diferencia": [
                        diferencia_presupuesto_precio,
                        diferencia_presupuesto_plazo
                    ],
                    "Variación (%)": [
                        variacion_presupuesto_precio,
                        variacion_presupuesto_plazo
                    ]
                })

                st.dataframe(
                    tabla_presupuesto,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Total propuesta": st.column_config.NumberColumn(
                            f"Total ({moneda_solicitud})",
                            format="%.2f"
                        ),
                        "Presupuesto": st.column_config.NumberColumn(
                            f"Presupuesto ({moneda_solicitud})",
                            format="%.2f"
                        ),
                        "Diferencia": st.column_config.NumberColumn(
                            f"Diferencia ({moneda_solicitud})",
                            format="%.2f"
                        ),
                        "Variación (%)": st.column_config.NumberColumn(
                            "Variación (%)",
                            format="%.2f%%"
                        )
                    }
                )

                st.caption(
                    "Una diferencia negativa representa un valor "
                    "inferior al presupuesto; una diferencia positiva "
                    "representa un valor superior. Esta comparación "
                    "no constituye una evaluación de admisibilidad."
                )

            elif monto_solicitud <= 0:
                st.info(
                    "Ingrese el monto total de la solicitud para "
                    "comparar los escenarios con el presupuesto."
                )

            else:
                st.info(
                    "La comparación presupuestaria estará disponible "
                    "cuando todos los artículos tengan ofertas completas."
                )

            st.divider()
            
            # ====================================================
            # GRÁFICO COMPARATIVO DE ESCENARIOS
            # ====================================================

            st.markdown("### 📊 Comparación gráfica de escenarios")

            if evaluacion_completa and monto_solicitud > 0:

                datos_grafico = pd.DataFrame({
                    "Escenario": [
                        "Presupuesto",
                        "Menor precio",
                        "Menor plazo"
                    ],
                    "Monto": [
                        monto_solicitud,
                        total_propuesta_precio,
                        total_propuesta_plazo
                    ]
                })

                st.bar_chart(
                    datos_grafico.set_index("Escenario"),
                    y="Monto",
                    horizontal=True,
                    x_label=f"Monto neto ({moneda_solicitud})",
                    color="#3274A1"
                )

                st.caption(
                    "Comparación de los valores netos expresados "
                    f"en {moneda_solicitud}. Los escenarios consideran "
                    "la selección de una alternativa por artículo."
                )

            else:
                st.info(
                    "El gráfico estará disponible cuando todos los "
                    "artículos tengan ofertas completas y se haya "
                    "ingresado el presupuesto de la solicitud."
                )

            st.divider()
            
            # ====================================================
            # CONCLUSIÓN COMERCIAL DE LA EVALUACIÓN
            # ====================================================

            st.markdown("### 📝 Conclusión comercial")

            if evaluacion_completa and total_propuesta_precio > 0:

                st.write(
                    "La propuesta de menor precio presenta un valor "
                    f"neto total de **{formatear_monto_chileno(total_propuesta_precio)} "
                    f"{moneda_solicitud}**, considerando la alternativa "
                    "económicamente más conveniente de cada artículo."
                )

                if diferencia_precio_plazo > 0:

                    porcentaje_adicional = (
                        diferencia_precio_plazo
                        / total_propuesta_precio * 100
                    )

                    st.write(
                        "Priorizar las alternativas de menor plazo de "
                        "entrega representa un costo adicional de "
                        f"**{formatear_monto_chileno(diferencia_precio_plazo)} "
                        f"{moneda_solicitud}** "
                        f"(**{formatear_monto_chileno(porcentaje_adicional)}%**) "
                        "respecto de la propuesta económica."
                    )

                else:
                    st.write(
                        "La selección de alternativas de menor plazo "
                        "no representa un costo adicional respecto "
                        "de la propuesta de menor precio."
                    )

                if monto_solicitud > 0:

                    if total_propuesta_precio <= monto_solicitud:
                        st.write(
                            "La propuesta de menor precio se encuentra "
                            "dentro del presupuesto informado."
                        )
                    else:
                        st.write(
                            "La propuesta de menor precio supera "
                            "el presupuesto informado."
                        )

                    if total_propuesta_plazo <= monto_solicitud:
                        st.write(
                            "La propuesta de menor plazo también se "
                            "encuentra dentro del presupuesto."
                        )
                    else:
                        st.write(
                            "La propuesta de menor plazo supera "
                            "el presupuesto informado."
                        )

                st.caption(
                    "Conclusión comercial referencial. La selección "
                    "definitiva requiere validar las especificaciones "
                    "técnicas, las condiciones comerciales y la "
                    "admisibilidad de las ofertas."
                )

            else:
                st.info(
                    "La conclusión comercial estará disponible cuando "
                    "todos los artículos tengan ofertas con cobertura "
                    "completa."
                )

            st.divider()
            
            with st.expander("🔎 06 / Análisis detallado por artículo", expanded=False):
                st.caption("Consulte los resultados, rankings y alternativas de cada artículo cuando necesite profundizar en la evaluación.")

                columnas_comparacion = [
                    "Ítem",
                    "Código de artículo",
                    "Descripción",
                    "Cantidad",
                    "Unidad de medida",
                    "Proveedor",
                    "N° cotización",
                    "Alternativa",
                    "Marca / Modelo",
                    "Cantidad cotizada",
                    "Cobertura",
                    "Precio unitario",
                    "Moneda",
                    "Subtotal neto",
                    "Precio unitario convertido",
                    "Subtotal neto convertido",
                    "Plazo",
                    "Unidad plazo",
                    "Plazo (días)"
                ]
            
                # Seleccionar el artículo que se desea comparar.
                item_comparar = st.selectbox(
                    "Seleccione el artículo para comparar",
                    options=articulos_validos["Ítem"].tolist(),
                    format_func=lambda item: (
                        f"Ítem {item} — "
                        f"{articulos_validos.loc[articulos_validos['Ítem'] == item, 'Descripción'].iloc[0]}"
                    ),
                    key="item_comparacion_economica"
                )

                # Mostrar únicamente las ofertas del artículo seleccionado.
                tabla_item = tabla_comparacion[
                    tabla_comparacion["Ítem"] == item_comparar
                ]
            
                # Identificar el artículo que se está evaluando.
                articulo_seleccionado = articulos_validos.loc[
                    articulos_validos["Ítem"] == item_comparar
                ].iloc[0]

                descripcion_item = articulo_seleccionado["Descripción"]
                codigo_item = articulo_seleccionado["Código de artículo"]

                titulo_articulo = (
                    f"Ítem {item_comparar} — {descripcion_item}"
                    f" | Código: {codigo_item}"
                )
            
                # Informar cuando existan ofertas en monedas diferentes.
                if not tabla_item.empty and (
                    tabla_item["Moneda"] != moneda_solicitud
                ).any():
                    st.info(
                        "Se detectaron cotizaciones en monedas distintas "
                        f"a la solicitud ({moneda_solicitud}). "
                        "Los precios se han convertido utilizando los "
                        "tipos de cambio de referencia ingresados. "
                        "La comparación económica se realiza en la "
                        "moneda de la solicitud."
                    )
            
                # Identificar las alternativas que cubren toda la cantidad.
                ofertas_completas_item = tabla_item[
                    tabla_item["Cobertura"] == "Completa"
                ]

                # Obtener el menor subtotal en la moneda de la solicitud.
                menor_subtotal_item = (
                    ofertas_completas_item["Subtotal neto convertido"].min()
                    if not ofertas_completas_item.empty
                    else None
                )
            
                # Identificar las mejores ofertas usando el subtotal convertido.
                if menor_subtotal_item is not None:
                    mejores_ofertas_item = ofertas_completas_item[
                        ofertas_completas_item["Subtotal neto convertido"]
                        == menor_subtotal_item
                    ].copy()
                else:
                    mejores_ofertas_item = pd.DataFrame()
                
                # ====================================================
                # RESUMEN EJECUTIVO: RESULTADO ECONÓMICO
                # ====================================================

                st.markdown("#### 📊 Resultado de la evaluación económica")

                if not mejores_ofertas_item.empty:
                    nombres_mejores = (
                        mejores_ofertas_item["Proveedor"]
                        .drop_duplicates()
                        .tolist()
                    )

                    st.metric(
                        "Menor valor neto ofertado",
                        f"{formatear_monto_chileno(menor_subtotal_item)} "
                        f"{moneda_solicitud}"
                    )

                    st.caption(
                        "Proveedor(es) con el menor valor: "
                        + ", ".join(nombres_mejores)
                    )
                
                # Mostrar las alternativas económicamente más convenientes.
                if not mejores_ofertas_item.empty:
                    for _, mejor_oferta in mejores_ofertas_item.iterrows():
                        st.success(
                            f"Mejor oferta económica: "
                            f"{mejor_oferta['Proveedor']} | "
                            f"Alternativa {mejor_oferta['Alternativa']} | "
                            f"Subtotal neto convertido: "
                            f"{formatear_monto_chileno(menor_subtotal_item)} "
                            f"{moneda_solicitud}"
                        )
                elif ofertas_completas_item.empty:
                    st.warning(
                        "No existen ofertas que cubran la cantidad "
                        "total solicitada para este artículo."
                    )

                # Identificar el menor plazo de entrega.
                menor_plazo_item = (
                    ofertas_completas_item["Plazo (días)"].min()
                    if not ofertas_completas_item.empty
                    else None
                )

                # Identificar las ofertas con el menor plazo.
                if menor_plazo_item is not None:
                    ofertas_menor_plazo_item = ofertas_completas_item[
                        ofertas_completas_item["Plazo (días)"]
                        == menor_plazo_item
                    ].copy()
                else:
                    ofertas_menor_plazo_item = pd.DataFrame()
                
                # ====================================================
                # RESUMEN EJECUTIVO: MEJOR PLAZO DE ENTREGA
                # ====================================================

                st.markdown("#### 🚚 Resultado de la evaluación de plazos")

                if not ofertas_menor_plazo_item.empty:
                    proveedores_mas_rapidos = (
                        ofertas_menor_plazo_item["Proveedor"]
                        .drop_duplicates()
                        .tolist()
                    )

                    st.metric(
                        "Menor plazo de entrega ofertado",
                        f"{menor_plazo_item:g} días"
                    )

                    st.caption(
                        "Proveedor(es) con el menor plazo: "
                        + ", ".join(proveedores_mas_rapidos)
                    )
                
                # Mostrar las ofertas con el menor plazo de entrega.
                if not ofertas_menor_plazo_item.empty:
                    for _, oferta_rapida in ofertas_menor_plazo_item.iterrows():
                        st.info(
                            f"Menor plazo de entrega: "
                            f"{oferta_rapida['Proveedor']} | "
                            f"Alternativa {oferta_rapida['Alternativa']} | "
                            f"{menor_plazo_item:g} días"
                        )

                # PASO 7.88: clasificar TODAS las ofertas, sin equiparar
                # subtotales de cantidades diferentes. El criterio económico
                # es el precio UNITARIO convertido; el plazo es por oferta.
                ranking_economico_item = tabla_item.sort_values(
                    by=["Precio unitario convertido", "Plazo (días)"],
                    ascending=[True, True], kind="stable"
                ).copy()
                ranking_plazo_item = tabla_item.sort_values(
                    by=["Plazo (días)", "Precio unitario convertido"],
                    ascending=[True, True], kind="stable"
                ).copy()
                for ranking in (ranking_economico_item, ranking_plazo_item):
                    ranking["Cobertura (%)"] = (
                        ranking["Cantidad cotizada"] / ranking["Cantidad"] * 100
                    ).clip(upper=100).round(1)

                # Para calcular ahorro entre alternativas de compra completa
                # se mantiene un ranking separado basado en subtotal total.
                ranking_completas_por_total = ofertas_completas_item.sort_values(
                    by="Subtotal neto convertido", ascending=True, kind="stable"
                )
                # Obtener los subtotales distintos en la moneda de la solicitud.
                subtotales_distintos = (
                    ranking_completas_por_total["Subtotal neto convertido"]
                    .drop_duplicates()
                    .tolist()
                )
            
                # Calcular el ahorro utilizando subtotales convertidos.
                if len(subtotales_distintos) >= 2:
                    segundo_subtotal_item = subtotales_distintos[1]

                    ahorro_item = (
                        segundo_subtotal_item - subtotales_distintos[0]
                    )

                    ahorro_porcentaje_item = (
                        ahorro_item / segundo_subtotal_item * 100
                        if segundo_subtotal_item > 0
                        else 0
                    )
                else:
                    segundo_subtotal_item = None
                    ahorro_item = None
                    ahorro_porcentaje_item = None
                
                # Mostrar el ahorro en la moneda de la solicitud.
                if ahorro_item is not None:
                    moneda_ahorro = moneda_solicitud

                    st.metric(
                        "Ahorro potencial frente al siguiente precio superior",
                        f"{formatear_monto_chileno(ahorro_item)} {moneda_ahorro}",
                        f"{formatear_monto_chileno(ahorro_porcentaje_item)}%"
                    )
                
                    st.caption(
                        f"Mejor subtotal: {formatear_monto_chileno(menor_subtotal_item)} "
                        f"{moneda_ahorro} | "
                        f"Siguiente subtotal superior: "
                        f"{formatear_monto_chileno(segundo_subtotal_item)} {moneda_ahorro}"
                    )
                else:
                    st.caption(
                        "No hay suficientes precios distintos de ofertas "
                        "completas para calcular un ahorro comparativo."
                    )
                
                st.caption(
                    "Los rankings incluyen ofertas completas y parciales. "
                    "El ranking económico ordena por precio unitario convertido "
                    "(no por subtotal de cantidades distintas). La mejor oferta "
                    "individual completa se evalúa por el costo total requerido."
                )
                if not tabla_item.empty:
                    mejor_unitario = ranking_economico_item.iloc[0]
                    mas_rapida = ranking_plazo_item.iloc[0]
                    st.info(
                        f"Menor precio unitario: {mejor_unitario['Proveedor']} "
                        f"({formatear_monto_chileno(mejor_unitario['Precio unitario convertido'])} "
                        f"{moneda_solicitud}/unidad; "
                        f"{mejor_unitario['Cantidad cotizada']:g} de "
                        f"{mejor_unitario['Cantidad']:g} unidades; "
                        f"{mejor_unitario['Cobertura']}). "
                        f"Menor plazo ofertado: {mas_rapida['Proveedor']} "
                        f"({mas_rapida['Plazo (días)']:g} días; "
                        f"{mas_rapida['Cobertura']})."
                    )
            
                # Informar cuando no existan ofertas completas para el artículo.
                if ofertas_completas_item.empty:
                    st.info(
                        "No hay ofertas completas para una adjudicación individual "
                        "de toda la cantidad. Revise las ofertas parciales y el simulador."
                    )
                
                # Numerar las ofertas del ranking económico.
                ranking_economico_item = ranking_economico_item.copy()
                ranking_economico_item.insert(
                    0, "Posición", range(1, len(ranking_economico_item) + 1)
                )
            
                # Mostrar los indicadores de cobertura en tres columnas.
                col_total, col_completas, col_parciales = st.columns(3)

                with col_total:
                    st.metric("Total de alternativas", len(tabla_item))

                with col_completas:
                    st.metric(
                        "Alternativas completas evaluadas",
                        len(ofertas_completas_item)
                    )

                with col_parciales:
                    st.metric(
                        "Alternativas parciales",
                        len(tabla_item) - len(ofertas_completas_item)
                    )
                
                # Mostrar el ranking económico en la moneda de la solicitud.
                st.markdown(f"#### Ranking económico — {titulo_articulo}")
                st.caption(
                    f"Ordenado por precio unitario en {moneda_solicitud}; "
                    "los subtotales corresponden únicamente a las cantidades cotizadas."
                )
                st.dataframe(
                    ranking_economico_item[
                        ["Posición", "Proveedor", "N° cotización",
                         "Alternativa", "Cantidad", "Cantidad cotizada",
                         "Cobertura", "Cobertura (%)", "Moneda",
                         "Precio unitario convertido", "Subtotal neto convertido",
                         "Plazo (días)"]
                    ],
                    hide_index=True,
                    width="stretch"
                )

                # Numerar las ofertas del ranking por plazo.
                ranking_plazo_item = ranking_plazo_item.copy()
                ranking_plazo_item.insert(
                    0, "Posición", range(1, len(ranking_plazo_item) + 1)
                )

                # Mostrar el ranking por plazo con valores convertidos.
                st.markdown(f"#### Ranking por plazo — {titulo_articulo}")
                st.caption(
                    "Ordenado por plazo; incluye cantidades y cobertura "
                    "para distinguir ofertas parciales y completas."
                )
                st.dataframe(
                    ranking_plazo_item[
                        ["Posición", "Proveedor", "N° cotización",
                         "Alternativa", "Plazo (días)", "Cantidad",
                         "Cantidad cotizada", "Cobertura", "Cobertura (%)",
                         "Precio unitario convertido", "Subtotal neto convertido"]
                    ],
                    hide_index=True,
                    width="stretch"
                )
            
                # Mostrar todas las alternativas del artículo seleccionado.
                st.markdown(f"#### Comparación detallada — {titulo_articulo}")

                st.dataframe(
                    tabla_item[columnas_comparacion].sort_values(
                        by=["Cobertura", "Subtotal neto convertido"],
                        ascending=[True, True]
                    ),
                    hide_index=True,
                    width="stretch"
                )







    # ========================================================
    # PASO 7.87 / SIMULADOR DE ADJUDICACIÓN COMBINADA
    # ========================================================
    st.divider()
    with st.expander("07 / Simulador de adjudicación combinada (opcional)", expanded=False):
        st.caption(
            "Asigne cantidades a ofertas completas o parciales. El análisis considera "
            "la suma de todos los proveedores frente al presupuesto total de la solicitud."
        )

        if not st.session_state.get("ofertas_guardadas"):
            st.info("Primero guarde al menos una cotización para utilizar el simulador.")
        else:
            # Construir las opciones directamente desde las cotizaciones guardadas.
            # Cada fila conserva su identidad, incluso si el proveedor tiene alternativas.
            opciones_simulador = []
            for (prov_sim, cot_sim), df_sim in st.session_state["ofertas_guardadas"].items():
                for indice_sim, fila_sim in df_sim.reset_index(drop=True).iterrows():
                    item_sim = fila_sim.get("Ítem")
                    if item_sim not in articulos_validos["Ítem"].values:
                        continue
                    moneda_sim = str(fila_sim.get("Moneda", ""))
                    precio_sim = pd.to_numeric(fila_sim.get("Precio unitario"), errors="coerce")
                    cantidad_sim = pd.to_numeric(fila_sim.get("Cantidad cotizada"), errors="coerce")
                    plazo_sim = pd.to_numeric(fila_sim.get("Plazo"), errors="coerce")
                    unidad_sim = str(fila_sim.get("Unidad plazo", ""))
                    if (pd.isna(precio_sim) or precio_sim <= 0 or pd.isna(cantidad_sim)
                            or cantidad_sim <= 0 or moneda_sim not in tipos_cambio_clp
                            or pd.isna(plazo_sim) or unidad_sim not in ("Días", "Semanas")):
                        continue
                    opciones_simulador.append({
                        "clave": json.dumps([prov_sim, cot_sim, int(indice_sim), str(item_sim)], ensure_ascii=False),
                        "Ítem": item_sim,
                        "Proveedor": prov_sim,
                        "N° cotización": cot_sim or "Sin número",
                        "Alternativa": fila_sim.get("Alternativa", "A"),
                        "Marca / Modelo": fila_sim.get("Marca / Modelo", ""),
                        "Cantidad cotizada": float(cantidad_sim),
                        "Precio unitario convertido": float(precio_sim) * tipos_cambio_clp[moneda_sim] / tipos_cambio_clp[moneda_solicitud],
                        "Plazo (días)": float(plazo_sim) * (7 if unidad_sim == "Semanas" else 1),
                    })

            if not opciones_simulador:
                st.info("No existen ofertas válidas para simular una adjudicación.")
            else:
                st.info(
                    "Las cantidades son propuestas de adjudicación, no modifican las "
                    "cotizaciones originales. Una oferta parcial también puede seleccionarse."
                )
                detalle_simulacion = []
                for _, articulo_sim in articulos_validos.iterrows():
                    item_sim = articulo_sim["Ítem"]
                    cantidad_requerida_sim = float(articulo_sim["Cantidad"])
                    ofertas_item_sim = [o for o in opciones_simulador if o["Ítem"] == item_sim]
                    with st.expander(
                        f"Ítem {item_sim} — {articulo_sim['Descripción']} "
                        f"({cantidad_requerida_sim:g} {articulo_sim['Unidad de medida']})",
                        expanded=True,
                    ):
                        if not ofertas_item_sim:
                            st.warning("No hay ofertas registradas para este artículo.")
                        for oferta_sim in ofertas_item_sim:
                            clave_widget_sim = "sim_adjudicacion_" + oferta_sim["clave"]
                            maximo_sim = min(cantidad_requerida_sim, oferta_sim["Cantidad cotizada"])
                            # Los valores se limitan al máximo de la oferta si esta cambió.
                            if clave_widget_sim in st.session_state:
                                anterior_sim = st.session_state[clave_widget_sim]
                                if anterior_sim > maximo_sim or anterior_sim < 0:
                                    st.session_state[clave_widget_sim] = 0.0
                            cantidad_elegida_sim = st.number_input(
                                f"{oferta_sim['Proveedor']} · {oferta_sim['N° cotización']} · "
                                f"Alt. {oferta_sim['Alternativa']} · Disponible: "
                                f"{oferta_sim['Cantidad cotizada']:g} · "
                                f"Unitario: {formatear_monto_chileno(oferta_sim['Precio unitario convertido'])} "
                                f"{moneda_solicitud} · {oferta_sim['Plazo (días)']:g} días",
                                min_value=0.0,
                                max_value=float(maximo_sim),
                                value=0.0,
                                step=1.0,
                                key=clave_widget_sim,
                            )
                            if cantidad_elegida_sim > 0:
                                detalle_simulacion.append({
                                    **{k: v for k, v in oferta_sim.items() if k != "clave"},
                                    "Descripción": articulo_sim["Descripción"],
                                    "Cantidad solicitada": cantidad_requerida_sim,
                                    "Cantidad adjudicada": float(cantidad_elegida_sim),
                                    "Subtotal adjudicado": float(cantidad_elegida_sim) * oferta_sim["Precio unitario convertido"],
                                })

                cantidades_por_item_sim = {
                    articulo["Ítem"]: sum(
                        r["Cantidad adjudicada"] for r in detalle_simulacion
                        if r["Ítem"] == articulo["Ítem"]
                    )
                    for _, articulo in articulos_validos.iterrows()
                }
                estado_items_sim = []
                exceso_sim = False
                completo_sim = True
                for _, articulo_sim in articulos_validos.iterrows():
                    requerida_sim = float(articulo_sim["Cantidad"])
                    asignada_sim = cantidades_por_item_sim[articulo_sim["Ítem"]]
                    pendiente_sim = max(0.0, requerida_sim - asignada_sim)
                    if asignada_sim > requerida_sim + 1e-8:
                        exceso_sim = True
                    if abs(asignada_sim - requerida_sim) > 1e-8:
                        completo_sim = False
                    estado_items_sim.append({
                        "Ítem": articulo_sim["Ítem"],
                        "Descripción": articulo_sim["Descripción"],
                        "Solicitado": requerida_sim,
                        "Adjudicado": asignada_sim,
                        "Pendiente": pendiente_sim,
                        "Exceso": max(0.0, asignada_sim - requerida_sim),
                    })

                st.markdown("#### Control de cobertura")
                st.dataframe(pd.DataFrame(estado_items_sim), hide_index=True, width="stretch")
                total_sim = sum(r["Subtotal adjudicado"] for r in detalle_simulacion)
                plazo_total_sim = max((r["Plazo (días)"] for r in detalle_simulacion), default=0.0)
                col_sim_1, col_sim_2, col_sim_3 = st.columns(3)
                col_sim_1.metric("Total seleccionado", f"{formatear_monto_chileno(total_sim)} {moneda_solicitud}")
                col_sim_2.metric("Plazo para completar entregas", f"{plazo_total_sim:g} días" if detalle_simulacion else "—")
                col_sim_3.metric("Cobertura", "Completa" if completo_sim and not exceso_sim else "Incompleta / excedida")

                if exceso_sim:
                    st.error("La cantidad adjudicada supera la solicitada en uno o más artículos. Ajuste las cantidades.")
                elif not completo_sim:
                    st.warning("La propuesta todavía no cubre todas las cantidades. El total es referencial y no corresponde evaluar la admisibilidad definitiva.")
                elif monto_solicitud <= 0:
                    st.info("La propuesta cubre toda la solicitud. Ingrese un presupuesto mayor que cero para compararla.")
                else:
                    diferencia_sim = total_sim - monto_solicitud
                    variacion_sim = diferencia_sim / monto_solicitud * 100
                    st.success("La propuesta cubre el 100% de los artículos y cantidades solicitadas.")
                    st.metric("Diferencia frente al presupuesto total", f"{formatear_monto_chileno(diferencia_sim)} {moneda_solicitud}", f"{variacion_sim:+.2f}%")
                    st.caption(
                        "Esta es una comparación presupuestaria. La clasificación formal "
                        "de admisibilidad se aplicará con los límites de la Calculadora de Admisibilidad."
                    )
                if detalle_simulacion:
                    st.markdown("#### Detalle de la adjudicación propuesta")
                    st.dataframe(pd.DataFrame(detalle_simulacion).drop(columns=["Cantidad cotizada"], errors="ignore"), hide_index=True, width="stretch")

                # Guardar el resultado para incluirlo en el respaldo y el Excel.
                st.session_state["evaluacion_simulacion_actual"] = {
                    "detalle": detalle_simulacion,
                    "cobertura": estado_items_sim,
                    "completa": bool(completo_sim and not exceso_sim),
                    "total": total_sim,
                    "plazo": plazo_total_sim,
                }

    # ========================================================
    # 07 / GUARDAR Y RECUPERAR EVALUACIÓN
    # ========================================================
    st.divider()
    st.subheader("08 / Guardar y recuperar evaluación")
    st.caption(
        "Descargue un archivo JSON para continuar otro día. "
        "El respaldo se genera con el estado actual de las cotizaciones guardadas."
    )

    def tabla_a_registros(tabla):
        return json.loads(tabla.to_json(orient="records", force_ascii=False))

    cotizaciones_respaldo = [
        {
            "proveedor": clave[0],
            "numero_cotizacion": clave[1],
            "articulos": tabla_a_registros(tabla),
        }
        for clave, tabla in st.session_state.get("ofertas_guardadas", {}).items()
    ]
    alternativas_respaldo = [
        {
            "proveedor": clave[0],
            "numero_cotizacion": clave[1],
            "articulos": tabla_a_registros(tabla),
        }
        for clave, tabla in st.session_state.get("alternativas_cotizaciones", {}).items()
    ]

    respaldo_evaluacion = {
        "version": 1,
        "numero_solicitud": numero_solicitud,
        "moneda_solicitud": moneda_solicitud,
        "monto_solicitud": monto_solicitud,
        "modalidad_comparacion": modalidad_adjudicacion,
        "tipos_cambio": tipos_cambio_clp,
        "articulos": tabla_a_registros(tabla_articulos),
        "proveedores": tabla_a_registros(tabla_proveedores_formateada),
        "cotizaciones": cotizaciones_respaldo,
        "alternativas_en_edicion": alternativas_respaldo,
        "cantidades_simulador": {
            k: v for k, v in st.session_state.items()
            if k.startswith("sim_adjudicacion_") and isinstance(v, (int, float))
        },
    }
    nombre_respaldo = "".join(
        c if c.isalnum() or c in "-_" else "_"
        for c in (numero_solicitud.strip() or "Sin_numero")
    )
    st.download_button(
        "📥 Descargar evaluación",
        data=json.dumps(respaldo_evaluacion, ensure_ascii=False, indent=4),
        file_name=f"Evaluacion_{nombre_respaldo}.json",
        mime="application/json",
        key="descargar_evaluacion_json",
    )
    st.caption(f"Cotizaciones guardadas incluidas: {len(cotizaciones_respaldo)}")

    with st.expander("📂 Cargar evaluación guardada", expanded=False):
        archivo = st.file_uploader(
            "Seleccione un respaldo JSON",
            type=["json"],
            key="archivo_evaluacion_json",
        )
        recuperar_borrador = st.checkbox(
            "Si el archivo antiguo no tiene cotizaciones guardadas, "
            "recuperar las alternativas completas como cotizaciones",
            value=False,
            help="Úselo para recuperar el respaldo SC-001 anterior. "
                 "Solo se recuperan filas con precio, plazo, moneda y cantidad válidos.",
        )
        if archivo is not None:
            try:
                datos_carga = json.loads(archivo.getvalue().decode("utf-8-sig"))
                if not isinstance(datos_carga, dict) or datos_carga.get("version") != 1:
                    raise ValueError("Formato o versión del respaldo no compatible.")
                for campo in ("articulos", "proveedores", "cotizaciones", "alternativas_en_edicion"):
                    if not isinstance(datos_carga.get(campo), list):
                        raise ValueError(f"El campo '{campo}' debe ser una lista.")
                if datos_carga.get("moneda_solicitud") not in ("CLP", "USD", "EUR", "UF"):
                    raise ValueError("Moneda de solicitud inválida.")
                if datos_carga.get("modalidad_comparacion") not in (
                    "Por artículo", "Por oferta total", "Ambas modalidades"
                ):
                    raise ValueError("Modalidad de comparación inválida.")
                if not isinstance(datos_carga.get("tipos_cambio"), dict):
                    raise ValueError("Faltan los tipos de cambio.")
                for moneda in ("USD", "EUR", "UF"):
                    if float(datos_carga["tipos_cambio"].get(moneda, 0)) <= 0:
                        raise ValueError(f"Tipo de cambio {moneda} inválido.")
                if float(datos_carga.get("monto_solicitud", -1)) < 0:
                    raise ValueError("Presupuesto inválido.")
                columnas_art = ["Código de artículo", "Descripción", "Cantidad", "Unidad de medida"]
                columnas_prov = ["RUT", "Proveedor"]
                df_art = pd.DataFrame(datos_carga["articulos"])
                df_prov = pd.DataFrame(datos_carga["proveedores"])
                if not set(columnas_art).issubset(df_art.columns) or not set(columnas_prov).issubset(df_prov.columns):
                    raise ValueError("El respaldo no contiene las columnas de artículos o proveedores.")
                for campo in ("cotizaciones", "alternativas_en_edicion"):
                    for registro in datos_carga[campo]:
                        if not isinstance(registro, dict) or not isinstance(registro.get("articulos"), list):
                            raise ValueError(f"Estructura inválida en {campo}.")
                        if not isinstance(registro.get("proveedor"), str) or not isinstance(registro.get("numero_cotizacion"), str):
                            raise ValueError(f"Identificación inválida en {campo}.")

                st.info(
                    f"Solicitud: {datos_carga.get('numero_solicitud') or 'Sin número'} | "
                    f"Artículos: {len(df_art)} | Proveedores: {len(df_prov)} | "
                    f"Cotizaciones guardadas: {len(datos_carga['cotizaciones'])}"
                )
                if st.button("📂 Restaurar esta evaluación", type="primary", key="restaurar_evaluacion"):
                    ofertas = {}
                    alternativas = {}
                    for registro in datos_carga["cotizaciones"]:
                        clave = (registro["proveedor"], registro["numero_cotizacion"])
                        ofertas[clave] = pd.DataFrame(registro["articulos"])
                    for registro in datos_carga["alternativas_en_edicion"]:
                        clave = (registro["proveedor"], registro["numero_cotizacion"])
                        alternativas[clave] = pd.DataFrame(registro["articulos"])

                    if not ofertas and recuperar_borrador:
                        for clave, tabla in alternativas.items():
                            columnas = ["Precio unitario", "Cantidad cotizada", "Cantidad", "Moneda", "Plazo", "Unidad plazo"]
                            if not set(columnas).issubset(tabla.columns):
                                continue
                            precios = pd.to_numeric(tabla["Precio unitario"], errors="coerce")
                            cantidades = pd.to_numeric(tabla["Cantidad cotizada"], errors="coerce")
                            solicitadas = pd.to_numeric(tabla["Cantidad"], errors="coerce")
                            plazos = pd.to_numeric(tabla["Plazo"], errors="coerce")
                            mascara = (
                                precios.gt(0) & cantidades.gt(0) & cantidades.le(solicitadas)
                                & plazos.ge(0) & tabla["Moneda"].isin(["CLP", "USD", "EUR", "UF"])
                                & tabla["Unidad plazo"].isin(["Días", "Semanas"])
                            )
                            if mascara.any():
                                ofertas[clave] = tabla.loc[mascara].copy()

                    # Limpiar el estado de los editores y selectores de la evaluación anterior.
                    for clave in list(st.session_state.keys()):
                        if clave.startswith((
                            "editor_articulos_solicitud", "editor_proveedores_evaluacion_",
                            "editor_oferta_", "editar_oferta_", "item_alternativa_",
                            "numero_cotizacion_", "item_comparacion_economica", "sim_adjudicacion_",
                        )) or clave in (
                            "proveedor_cotizacion", "cotizacion_para_editar",
                        ):
                            del st.session_state[clave]

                    st.session_state["evaluacion_restauracion_pendiente"] = {
                        "evaluacion_numero_solicitud": str(datos_carga.get("numero_solicitud", "")),
                        "evaluacion_moneda_solicitud": datos_carga["moneda_solicitud"],
                        "evaluacion_monto_solicitud": float(datos_carga["monto_solicitud"]),
                        "evaluacion_modalidad": datos_carga["modalidad_comparacion"],
                        "evaluacion_usd": float(datos_carga["tipos_cambio"]["USD"]),
                        "evaluacion_eur": float(datos_carga["tipos_cambio"]["EUR"]),
                        "evaluacion_uf": float(datos_carga["tipos_cambio"]["UF"]),
                    }
                    # Un respaldo recuperado no garantiza que sus tasas sigan
                    # siendo las oficiales de la fecha indicada.
                    st.session_state["evaluacion_origen_tipo_cambio"] = "Valores recuperados desde respaldo JSON"
                    st.session_state["evaluacion_tc_modificados"] = []
                    st.session_state["articulos_solicitud"] = df_art[columnas_art].copy()
                    st.session_state["proveedores_evaluacion"] = df_prov[columnas_prov].copy()
                    st.session_state["version_editor_proveedores"] = st.session_state.get("version_editor_proveedores", 0) + 1
                    st.session_state["ofertas_guardadas"] = ofertas
                    st.session_state.pop("evaluacion_simulacion_actual", None)
                    st.session_state["alternativas_cotizaciones"] = alternativas
                    for clave_sim, valor_sim in datos_carga.get("cantidades_simulador", {}).items():
                        if clave_sim.startswith("sim_adjudicacion_") and isinstance(valor_sim, (int, float)):
                            st.session_state[clave_sim] = float(valor_sim)
                    st.session_state["evaluacion_restaurada_mensaje"] = (
                        f"Evaluación recuperada: {len(ofertas)} cotización(es) guardada(s)."
                    )
                    st.rerun()
            except (ValueError, TypeError, KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
                st.error(f"No se pudo leer el respaldo: {error}")

    # ========================================================
    # 08 / EXPORTAR INFORME COMERCIAL A EXCEL (PASO 7.82)
    # ========================================================
    st.divider()
    st.subheader("09 / Exportar informe completo a Excel")
    st.caption(
        "Descargue un informe comercial con antecedentes, artículos, proveedores, "
        "cotizaciones, comparación económica y plazos. El archivo Excel no reemplaza "
        "el respaldo JSON utilizado para recuperar la evaluación."
    )

    if not st.session_state.get("ofertas_guardadas"):
        st.info("Guarde al menos una cotización para generar el informe Excel.")
    else:
        try:
            from io import BytesIO
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            from openpyxl.chart import BarChart, Reference

            def numero_excel(valor):
                try:
                    n = float(valor)
                    return n if pd.notna(n) else None
                except (TypeError, ValueError):
                    return None

            moneda_base = moneda_solicitud
            tc_base = numero_excel(tipos_cambio_clp.get(moneda_base))
            filas_detalle = []
            for (nombre_proveedor, numero_cot), df_cot in st.session_state["ofertas_guardadas"].items():
                for _, r in df_cot.iterrows():
                    cantidad = numero_excel(r.get("Cantidad cotizada"))
                    requerida = numero_excel(r.get("Cantidad"))
                    precio = numero_excel(r.get("Precio unitario"))
                    plazo = numero_excel(r.get("Plazo"))
                    unidad_plazo = str(r.get("Unidad plazo", ""))
                    moneda = str(r.get("Moneda", ""))
                    tc = numero_excel(tipos_cambio_clp.get(moneda))
                    subtotal = cantidad * precio if cantidad is not None and precio is not None else None
                    subtotal_convertido = subtotal * tc / tc_base if subtotal is not None and tc and tc_base else None
                    precio_convertido = precio * tc / tc_base if precio is not None and tc and tc_base else None
                    dias = plazo * (7 if unidad_plazo == "Semanas" else 1) if plazo is not None and unidad_plazo in ("Días", "Semanas") else None
                    cobertura = "Completa" if cantidad is not None and requerida is not None and cantidad >= requerida else "Parcial"
                    filas_detalle.append({
                        "Ítem": r.get("Ítem"),
                        "Código de artículo": str(r.get("Código de artículo", "")),
                        "Descripción": r.get("Descripción", ""),
                        "Cantidad solicitada": requerida,
                        "Unidad de medida": r.get("Unidad de medida", ""),
                        "Proveedor": nombre_proveedor,
                        "N° cotización": numero_cot or "Sin número",
                        "Alternativa": r.get("Alternativa", "A"),
                        "Marca / Modelo": r.get("Marca / Modelo", ""),
                        "Cantidad cotizada": cantidad,
                        "Cobertura": cobertura,
                        "Precio unitario": precio,
                        "Moneda": moneda,
                        "Subtotal neto": subtotal,
                        f"Precio unitario ({moneda_base})": precio_convertido,
                        f"Subtotal neto ({moneda_base})": subtotal_convertido,
                        "Plazo ofertado": plazo,
                        "Unidad plazo": unidad_plazo,
                        "Plazo (días)": dias,
                    })

            def llave_item(fila):
                return str(fila.get("Ítem"))

            completas = [r for r in filas_detalle if r["Cobertura"] == "Completa" and r[f"Subtotal neto ({moneda_base})"] is not None and r["Plazo (días)"] is not None]
            grupos = {}
            for r in completas:
                grupos.setdefault(llave_item(r), []).append(r)
            menor_precio = [min(grupo, key=lambda r: (r[f"Subtotal neto ({moneda_base})"], r["Plazo (días)"])) for grupo in grupos.values()]
            menor_plazo = [min(grupo, key=lambda r: (r["Plazo (días)"], r[f"Subtotal neto ({moneda_base})"])) for grupo in grupos.values()]
            menor_precio.sort(key=lambda r: numero_excel(r["Ítem"]) or 0)
            menor_plazo.sort(key=lambda r: numero_excel(r["Ítem"]) or 0)
            n_articulos = len(articulos_validos)
            evaluacion_completa_excel = len(grupos) == n_articulos and n_articulos > 0
            total_precio = sum(r[f"Subtotal neto ({moneda_base})"] for r in menor_precio)
            total_plazo = sum(r[f"Subtotal neto ({moneda_base})"] for r in menor_plazo)

            libro = Workbook()
            libro.remove(libro.active)
            azul = "122238"
            turquesa = "12B8AD"
            claro = "EAF3F7"
            gris = "66788A"
            formato_monto = '#,##0.00;[Red](#,##0.00)'
            formato_entero = '#,##0'

            def hoja(nombre, titulo, encabezados, filas, columnas_monto=()):
                ws = libro.create_sheet(nombre)
                n = max(1, len(encabezados))
                ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n)
                celda = ws.cell(1, 1, titulo)
                celda.fill = PatternFill("solid", fgColor=azul)
                celda.font = Font(name="Aptos", size=16, bold=True, color="FFFFFF")
                celda.alignment = Alignment(vertical="center")
                ws.row_dimensions[1].height = 34
                ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=n)
                ws.cell(2, 1, "Evaluación comercial referencial · Sujeta a validación técnica y de admisibilidad")
                ws.cell(2, 1).font = Font(name="Aptos", size=10, italic=True, color=gris)
                for j, h in enumerate(encabezados, 1):
                    c = ws.cell(4, j, h)
                    c.fill = PatternFill("solid", fgColor=azul)
                    c.font = Font(name="Aptos", bold=True, color="FFFFFF")
                    c.alignment = Alignment(wrap_text=True, vertical="center")
                ws.row_dimensions[4].height = 32
                for i, valores in enumerate(filas, 5):
                    for j, valor in enumerate(valores, 1):
                        if hasattr(valor, "item"):
                            valor = valor.item()
                        if pd.isna(valor) if not isinstance(valor, (list, dict)) else False:
                            valor = None
                        c = ws.cell(i, j, valor)
                        c.font = Font(name="Aptos", size=10, color=azul)
                        c.alignment = Alignment(vertical="center", wrap_text=False)
                        if i % 2 == 0:
                            c.fill = PatternFill("solid", fgColor=claro)
                        if j in columnas_monto and isinstance(valor, (int, float)):
                            c.number_format = formato_monto
                for j, h in enumerate(encabezados, 1):
                    largo = max([len(str(h))] + [len(str(f[j-1])) for f in filas if len(f) >= j and f[j-1] is not None] + [12])
                    ws.column_dimensions[get_column_letter(j)].width = min(max(largo + 3, 15), 48)
                # Mantener datos identificadores visibles en tablas extensas.
                ws.freeze_panes = (
                    "F5" if nombre in ("Cotizaciones", "Recomendación adjudicación")
                    else "D5" if nombre in ("Comparación económica", "Ranking por artículo")
                    else "C5" if nombre in ("Plazos de entrega", "Adjudicación combinada")
                    else "A5"
                )
                ws.auto_filter.ref = f"A4:{get_column_letter(n)}{max(5, 4+len(filas))}"
                ws.sheet_view.showGridLines = False
                ws.sheet_properties.pageSetUpPr.fitToPage = True
                ws.page_setup.fitToWidth = 1
                return ws

            resumen = [
                ["N° solicitud", numero_solicitud or "Sin número"],
                ["Modalidad informada", modalidad_adjudicacion],
                ["Moneda de comparación", moneda_base],
                ["Presupuesto", numero_excel(monto_solicitud)],
                ["Artículos solicitados", n_articulos],
                ["Proveedores registrados", len(proveedores_validos)],
                ["Cotizaciones guardadas", len(st.session_state["ofertas_guardadas"])],
                ["Artículos con ofertas completas", len(grupos)],
                ["Estado de cobertura", "Completa" if evaluacion_completa_excel else "Incompleta"],
                ["Propuesta menor precio", total_precio if evaluacion_completa_excel else None],
                ["Propuesta menor plazo", total_plazo if evaluacion_completa_excel else None],
                ["Costo adicional por menor plazo", (total_plazo - total_precio) if evaluacion_completa_excel else None],
                ["Incremento respecto a menor precio (%)", (total_plazo / total_precio - 1) * 100 if evaluacion_completa_excel and total_precio else None],
                ["Diferencia menor precio vs presupuesto", total_precio - monto_solicitud if evaluacion_completa_excel else None],
                ["Diferencia menor plazo vs presupuesto", total_plazo - monto_solicitud if evaluacion_completa_excel else None],
                ["Conclusión", "La propuesta de menor precio es la referencia económica; la decisión final requiere validación técnica y de admisibilidad." if evaluacion_completa_excel else "No hay cobertura completa de todos los artículos; no corresponde comparar propuestas totales con el presupuesto."],
                ["Tipo cambio USD a CLP", tipos_cambio_clp.get("USD")],
                ["Tipo cambio EUR a CLP", tipos_cambio_clp.get("EUR")],
                ["Tipo cambio UF a CLP", tipos_cambio_clp.get("UF")],
                ["Origen tipos de cambio", descripcion_origen_tipos_cambio()],
                ["Monedas ajustadas manualmente", ", ".join(st.session_state.get("evaluacion_tc_modificados", [])) or "Ninguna registrada"],
                ["Fecha referencia tipos de cambio", st.session_state.get("evaluacion_fecha_tipo_cambio", "Sin fecha automática")],
            ]
            ws_res = hoja("Resumen ejecutivo", "RESUMEN EJECUTIVO", ["Indicador", "Resultado"], resumen, (2,))
            ws_res.column_dimensions["A"].width = 43
            ws_res.column_dimensions["B"].width = 62
            # PASO 7.86: formatos específicos según el tipo de indicador.
            for fila_excel in (9, 10, 11, 12):
                ws_res.cell(fila_excel, 2).number_format = formato_entero
            ws_res.cell(17, 2).number_format = '0.00"%"'
            for fila_excel in (21, 22, 23):
                ws_res.cell(fila_excel, 2).number_format = formato_monto

            # Destacar los resultados principales sin modificar sus valores.
            for fila_excel in (14, 15):
                celda_resultado = ws_res.cell(fila_excel, 2)
                celda_resultado.fill = PatternFill("solid", fgColor="DCFCE7" if fila_excel == 14 else "DBEAFE")
                celda_resultado.font = Font(name="Aptos", size=11, bold=True, color="166534" if fila_excel == 14 else "1D4ED8")

            # La conclusión se muestra dentro de la celda, sin invadir columnas vecinas.
            ws_res.cell(20, 2).alignment = Alignment(wrap_text=True, vertical="center")
            ws_res.row_dimensions[20].height = 46
            ws_res.page_setup.orientation = "portrait"
            ws_res.print_options.horizontalCentered = True
            # PASO 7.83: hoja ejecutiva de recomendación económica por artículo.
            encabezados_recomendacion = [
                "Ítem", "Código de artículo", "Descripción", "Cantidad", "Unidad",
                "Proveedor recomendado", "RUT", "N° cotización", "Alternativa",
                "Marca / Modelo", "Moneda oferta", "Precio unitario original",
                f"Precio unitario ({moneda_base})", f"Total neto ({moneda_base})",
                "Plazo (días)", "Estado",
            ]
            proveedores_rut_excel = {
                str(r["Proveedor"]).strip(): str(r["RUT"])
                for _, r in proveedores_validos.iterrows()
            }
            propuestas_por_item_excel = {llave_item(r): r for r in menor_precio}
            filas_recomendacion = []
            for _, articulo in articulos_validos.iterrows():
                oferta = propuestas_por_item_excel.get(str(articulo["Ítem"]))
                if oferta is None:
                    filas_recomendacion.append([
                        articulo["Ítem"], articulo["Código de artículo"],
                        articulo["Descripción"], numero_excel(articulo["Cantidad"]),
                        articulo["Unidad de medida"], None, None, None, None,
                        None, None, None, None, None, None, "Sin oferta completa",
                    ])
                else:
                    filas_recomendacion.append([
                        oferta["Ítem"], oferta["Código de artículo"],
                        oferta["Descripción"], oferta["Cantidad solicitada"],
                        oferta["Unidad de medida"], oferta["Proveedor"],
                        proveedores_rut_excel.get(str(oferta["Proveedor"]).strip()),
                        oferta["N° cotización"], oferta["Alternativa"],
                        oferta["Marca / Modelo"], oferta["Moneda"],
                        oferta["Precio unitario"],
                        oferta[f"Precio unitario ({moneda_base})"],
                        oferta[f"Subtotal neto ({moneda_base})"],
                        oferta["Plazo (días)"], "Recomendado por precio",
                    ])

            ws_rec = hoja(
                "Recomendación adjudicación",
                "RECOMENDACIÓN ECONÓMICA DE ADJUDICACIÓN",
                encabezados_recomendacion, filas_recomendacion, (12, 13, 14),
            )
            ws_rec.sheet_properties.tabColor = "16A34A" if evaluacion_completa_excel else "D97706"
            ws_rec["A2"] = (
                "Menor precio por artículo · Valores netos · "
                "Pendiente de validación técnica, comercial y admisibilidad"
            )
            ws_rec["A2"].font = Font(name="Aptos", size=10, italic=True, color=gris)
            for fila_excel in range(5, 5 + len(filas_recomendacion)):
                celda_estado = ws_rec.cell(fila_excel, 16)
                if celda_estado.value == "Sin oferta completa":
                    celda_estado.fill = PatternFill("solid", fgColor="FEE2E2")
                    celda_estado.font = Font(name="Aptos", bold=True, color="991B1B")
                else:
                    celda_estado.fill = PatternFill("solid", fgColor="DCFCE7")
                    celda_estado.font = Font(name="Aptos", bold=True, color="166534")
            fila_totales = 6 + len(filas_recomendacion)
            ws_rec.cell(fila_totales, 12, "TOTAL NETO RECOMENDADO")
            ws_rec.cell(
                fila_totales, 14,
                total_precio if evaluacion_completa_excel else None,
            )
            ws_rec.cell(fila_totales, 16, (
                "COBERTURA COMPLETA" if evaluacion_completa_excel
                else "INCOMPLETA - NO HAY TOTAL GENERAL"
            ))
            for col in range(1, 17):
                c = ws_rec.cell(fila_totales, col)
                c.fill = PatternFill("solid", fgColor="166534" if evaluacion_completa_excel else "92400E")
                c.font = Font(name="Aptos", bold=True, color="FFFFFF")
                c.alignment = Alignment(vertical="center")
            ws_rec.cell(fila_totales, 14).number_format = formato_monto
            ws_rec.row_dimensions[fila_totales].height = 28
            if evaluacion_completa_excel and monto_solicitud > 0:
                fila_presupuesto = fila_totales + 2
                diferencia = total_precio - monto_solicitud
                for fila, etiqueta, valor in (
                    (fila_presupuesto, "Presupuesto de solicitud", monto_solicitud),
                    (fila_presupuesto + 1, "Diferencia vs presupuesto", diferencia),
                    (fila_presupuesto + 2, "Variación vs presupuesto (%)", diferencia / monto_solicitud * 100),
                ):
                    ws_rec.cell(fila, 12, etiqueta)
                    celda_valor = ws_rec.cell(fila, 14, valor)
                    celda_valor.number_format = formato_monto if fila != fila_presupuesto + 2 else '0.00"%"'
                    if fila == fila_presupuesto + 1:
                        celda_valor.font = Font(
                            name="Aptos", bold=True,
                            color="166534" if diferencia <= 0 else "B91C1C",
                        )
            ws_rec.column_dimensions["C"].width = 42
            ws_rec.column_dimensions["F"].width = 30
            ws_rec.column_dimensions["P"].width = 31
            ws_rec.print_options.horizontalCentered = True
            ws_rec.sheet_properties.pageSetUpPr.fitToPage = True

            art_cols = ["Código de artículo", "Descripción", "Cantidad", "Unidad de medida"]
            ws_art = hoja("Artículos", "ARTÍCULOS DE LA SOLICITUD", art_cols, [[r.get(c) for c in art_cols] for _, r in articulos_validos.iterrows()])
            ws_art.column_dimensions["A"].width = 24
            ws_art.column_dimensions["B"].width = 42
            ws_art.column_dimensions["C"].width = 18
            ws_art.column_dimensions["D"].width = 24
            for fila_excel in range(5, ws_art.max_row + 1):
                ws_art.cell(fila_excel, 3).number_format = formato_entero
                ws_art.cell(fila_excel, 3).alignment = Alignment(horizontal="center", vertical="center")
                ws_art.cell(fila_excel, 4).alignment = Alignment(horizontal="center", vertical="center")
            prov_cols = ["RUT", "Proveedor"]
            ws_prov = hoja("Proveedores", "PROVEEDORES PARTICIPANTES", prov_cols, [[r.get(c) for c in prov_cols] for _, r in proveedores_validos.iterrows()])
            ws_prov.column_dimensions["A"].width = 28
            ws_prov.column_dimensions["B"].width = 44
            det_cols = list(filas_detalle[0].keys()) if filas_detalle else []
            hoja("Cotizaciones", "DETALLE DE TODAS LAS ALTERNATIVAS", det_cols, [[r.get(c) for c in det_cols] for r in filas_detalle], (12,14,15,16))
            columnas_prop = ["Ítem", "Código de artículo", "Descripción", "Proveedor", "N° cotización", "Alternativa", "Cantidad solicitada", "Unidad de medida", f"Precio unitario ({moneda_base})", f"Subtotal neto ({moneda_base})", "Plazo (días)"]
            filas_prop = []
            for criterio, propuestas in (("Menor precio", menor_precio), ("Menor plazo", menor_plazo)):
                for r in propuestas:
                    filas_prop.append([criterio] + [r.get(c) for c in columnas_prop])
            ws_comp = hoja("Comparación económica", "PROPUESTAS ECONÓMICAS POR ARTÍCULO", ["Escenario"] + columnas_prop, filas_prop, (10,11))
            for fila_excel in range(5, ws_comp.max_row + 1):
                escenario = ws_comp.cell(fila_excel, 1)
                if escenario.value == "Menor precio":
                    escenario.fill = PatternFill("solid", fgColor="DCFCE7")
                    escenario.font = Font(name="Aptos", bold=True, color="166534")
                elif escenario.value == "Menor plazo":
                    escenario.fill = PatternFill("solid", fgColor="DBEAFE")
                    escenario.font = Font(name="Aptos", bold=True, color="1D4ED8")
            filas_plazo = []
            for clave in sorted(grupos, key=lambda x: numero_excel(x) or 0):
                por_precio = next(r for r in menor_precio if llave_item(r) == clave)
                por_plazo = next(r for r in menor_plazo if llave_item(r) == clave)
                filas_plazo.append([
                    por_precio["Ítem"], por_precio["Descripción"], por_precio["Proveedor"],
                    por_precio["Plazo (días)"], por_plazo["Proveedor"], por_plazo["Plazo (días)"],
                    por_precio["Plazo (días)"] - por_plazo["Plazo (días)"],
                    por_plazo[f"Subtotal neto ({moneda_base})"] - por_precio[f"Subtotal neto ({moneda_base})"],
                ])
            ws_plazos = hoja("Plazos de entrega", "IMPACTO DEL PLAZO POR ARTÍCULO", ["Ítem", "Descripción", "Proveedor menor precio", "Plazo menor precio (días)", "Proveedor menor plazo", "Plazo menor entrega (días)", "Días ahorrados", f"Costo adicional ({moneda_base})"], filas_plazo, (8,))
            for fila_excel in range(5, ws_plazos.max_row + 1):
                ws_plazos.cell(fila_excel, 7).font = Font(name="Aptos", bold=True, color="166534")
                ws_plazos.cell(fila_excel, 8).font = Font(name="Aptos", bold=True, color="9A3412")
            # PASO 7.85: ranking integral de alternativas por artículo.
            # Todas las alternativas reciben posición por precio UNITARIO y plazo.
            encabezados_ranking = [
                "Ítem", "Código de artículo", "Descripción", "Proveedor",
                "N° cotización", "Alternativa", "Marca / Modelo",
                "Cantidad solicitada", "Cantidad cotizada", "Cobertura",
                "Moneda oferta", "Precio unitario original", "Subtotal original",
                f"Precio unitario ({moneda_base})", f"Total neto ({moneda_base})",
                "Plazo ofertado", "Unidad plazo", "Plazo (días)",
                "Posición por precio", "Posición por plazo", "Cobertura (%)",
            ]
            posiciones_precio = {}
            posiciones_plazo = {}
            # Se utilizan índices de registro para distinguir incluso alternativas idénticas.
            for clave_item in {llave_item(r) for r in filas_detalle}:
                indices_validos = [
                    i for i, r in enumerate(filas_detalle)
                    if llave_item(r) == clave_item
                    and r[f"Precio unitario ({moneda_base})"] is not None
                    and r["Plazo (días)"] is not None
                ]
                por_precio = sorted(
                    indices_validos,
                    key=lambda i: (
                        filas_detalle[i][f"Precio unitario ({moneda_base})"],
                        filas_detalle[i]["Plazo (días)"], i,
                    ),
                )
                por_plazo = sorted(
                    indices_validos,
                    key=lambda i: (
                        filas_detalle[i]["Plazo (días)"],
                        filas_detalle[i][f"Precio unitario ({moneda_base})"], i,
                    ),
                )
                posiciones_precio.update({i: n for n, i in enumerate(por_precio, 1)})
                posiciones_plazo.update({i: n for n, i in enumerate(por_plazo, 1)})

            indices_ordenados = sorted(
                range(len(filas_detalle)),
                key=lambda i: (
                    numero_excel(filas_detalle[i]["Ítem"]) or 0,
                    posiciones_precio.get(i, float("inf")), i,
                ),
            )
            filas_ranking = []
            for i in indices_ordenados:
                r = filas_detalle[i]
                filas_ranking.append([
                    r["Ítem"], r["Código de artículo"], r["Descripción"],
                    r["Proveedor"], r["N° cotización"], r["Alternativa"],
                    r["Marca / Modelo"], r["Cantidad solicitada"],
                    r["Cantidad cotizada"], r["Cobertura"], r["Moneda"],
                    r["Precio unitario"], r["Subtotal neto"],
                    r[f"Precio unitario ({moneda_base})"],
                    r[f"Subtotal neto ({moneda_base})"],
                    r["Plazo ofertado"], r["Unidad plazo"], r["Plazo (días)"],
                    posiciones_precio.get(i), posiciones_plazo.get(i),
                    (min(100, 100 * r["Cantidad cotizada"] / r["Cantidad solicitada"])
                     if r["Cantidad solicitada"] and r["Cantidad cotizada"] is not None else None),
                ])
            ws_ranking = hoja(
                "Ranking por artículo", "RANKING COMPLETO POR ARTÍCULO",
                encabezados_ranking, filas_ranking, (12, 13, 14, 15, 21),
            )
            ws_ranking.freeze_panes = "D5"
            ws_ranking.column_dimensions["C"].width = 42
            ws_ranking.column_dimensions["D"].width = 30
            ws_ranking.column_dimensions["G"].width = 27
            ws_ranking.column_dimensions["S"].width = 22
            ws_ranking.column_dimensions["T"].width = 22
            ws_ranking.column_dimensions["U"].width = 18
            ws_ranking["A2"] = (
                "Ranking inclusivo por precio unitario convertido y plazo. "
                "Las ofertas parciales se identifican por cantidad y cobertura; "
                "sus subtotales no equivalen al costo de toda la solicitud."
            )
            ws_ranking["A2"].font = Font(
                name="Aptos", size=10, italic=True, color=gris,
            )
            for fila_excel in range(5, 5 + len(filas_ranking)):
                cobertura_celda = ws_ranking.cell(fila_excel, 10)
                if cobertura_celda.value == "Parcial":
                    cobertura_celda.fill = PatternFill("solid", fgColor="FEF3C7")
                    cobertura_celda.font = Font(name="Aptos", bold=True, color="92400E")
                for columna in (19, 20):
                    posicion = ws_ranking.cell(fila_excel, columna)
                    posicion.alignment = Alignment(horizontal="center", vertical="center")
                    posicion.number_format = formato_entero
                    if posicion.value == 1:
                        posicion.fill = PatternFill("solid", fgColor="DCFCE7")
                        posicion.font = Font(name="Aptos", bold=True, color="166534")
                    elif posicion.value == 2:
                        posicion.fill = PatternFill("solid", fgColor="DBEAFE")
                        posicion.font = Font(name="Aptos", bold=True, color="1D4ED8")

            # PASO 7.87: propuesta manual con cantidades de distintos proveedores.
            simulacion_excel = st.session_state.get("evaluacion_simulacion_actual", {})
            detalle_excel_sim = simulacion_excel.get("detalle", [])
            encabezados_excel_sim = [
                "Ítem", "Descripción", "Proveedor", "N° cotización", "Alternativa",
                "Cantidad solicitada", "Cantidad adjudicada", "Precio unitario convertido",
                "Subtotal adjudicado", "Plazo (días)",
            ]
            filas_excel_sim = [[r.get(c) for c in encabezados_excel_sim] for r in detalle_excel_sim]
            ws_sim = hoja(
                "Adjudicación combinada", "SIMULACIÓN DE ADJUDICACIÓN COMBINADA",
                encabezados_excel_sim, filas_excel_sim, (8, 9),
            )
            hay_simulacion = bool(filas_excel_sim)
            ws_sim["A2"] = (
                "Simulación manual · "
                + (
                    ("Cobertura completa" if simulacion_excel.get("completa") else "Cobertura incompleta o excedida")
                    if hay_simulacion else "Sin simulación registrada"
                )
                + " · Validar condiciones comerciales y admisibilidad"
            )
            ws_sim.cell(6 + len(filas_excel_sim), 7, "TOTAL SELECCIONADO" if hay_simulacion else "ESTADO DE SIMULACIÓN")
            ws_sim.cell(6 + len(filas_excel_sim), 9, simulacion_excel.get("total", 0) if hay_simulacion else "Sin simulación registrada")
            if hay_simulacion:
                ws_sim.cell(6 + len(filas_excel_sim), 9).number_format = formato_monto
            ws_sim.cell(8 + len(filas_excel_sim), 7, "PRESUPUESTO SOLICITUD")
            ws_sim.cell(8 + len(filas_excel_sim), 9, monto_solicitud)
            ws_sim.cell(8 + len(filas_excel_sim), 9).number_format = formato_monto
            if simulacion_excel.get("completa") and monto_solicitud > 0:
                ws_sim.cell(9 + len(filas_excel_sim), 7, "DIFERENCIA VS PRESUPUESTO")
                ws_sim.cell(9 + len(filas_excel_sim), 9, simulacion_excel.get("total", 0) - monto_solicitud)
                ws_sim.cell(9 + len(filas_excel_sim), 9).number_format = formato_monto

            # Impresión horizontal para las hojas de comparación extensas.
            for ws_informe in libro.worksheets:
                if ws_informe.title != "Resumen ejecutivo":
                    ws_informe.page_setup.orientation = "landscape"
                ws_informe.page_setup.paperSize = ws_informe.PAPERSIZE_A3 if ws_informe.max_column > 12 else ws_informe.PAPERSIZE_A4
                ws_informe.sheet_properties.pageSetUpPr.fitToPage = True
                ws_informe.page_setup.fitToWidth = 1
                ws_informe.page_setup.fitToHeight = 0
                ws_informe.print_title_rows = "1:4"

            salida = BytesIO()
            libro.save(salida)
            st.download_button(
                "📊 Descargar informe completo Excel",
                data=salida.getvalue(),
                file_name=f"Informe_Comparativo_{nombre_respaldo}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="descargar_informe_excel_782",
                type="primary",
            )
            if not evaluacion_completa_excel:
                st.warning("El informe contiene ofertas parciales: los totales globales se omiten hasta cubrir todos los artículos.")
        except Exception as error:
            st.error(f"No se pudo preparar el informe Excel: {error}")

    if st.session_state.get("evaluacion_restaurada_mensaje"):
        st.success(st.session_state.pop("evaluacion_restaurada_mensaje"))
