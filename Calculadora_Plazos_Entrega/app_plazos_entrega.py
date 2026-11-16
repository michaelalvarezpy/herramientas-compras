import streamlit as st 
from datetime import date

from Calculadora_Plazos_Entrega.Calculos.plazos_entrega import (
    calcular_fecha_entrega,
    calcular_dias_habiles,
    obtener_feriados_chile,
    obtener_feriados_periodo
)

def mostrar_calculadora_plazos():

    st.markdown(
        '<div style="color:#2DD4D7; font-size:12px; '
        'font-weight:700; letter-spacing:2px;">'
        'PLANIFICACIÓN DE SUMINISTROS'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<h2 style="margin-top:10px; margin-bottom:8px;">'
        'Calculadora de Plazos de Entrega'
        '</h2>',
        unsafe_allow_html=True
    )

    st.caption(
        "Estimación de fechas de entrega según días corridos, "
        "días hábiles y feriados de Chile."
    )
    
    st.markdown(
        """
        <div style="
            background-color:#16263D;
            border-left:3px solid #2DD4D7;
            border-radius:6px;
            padding:16px 20px;
            margin-top:24px;
            margin-bottom:20px;
        ">
            <div style="
                color:#2DD4D7;
                font-size:12px;
                font-weight:700;
                letter-spacing:1.5px;
            ">
                01 / CONFIGURACIÓN DEL PLAZO
            </div>
            <div style="margin-top:8px; font-size:13px;">
                Ingrese la fecha de inicio y las condiciones
                del plazo de entrega.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    modalidad = st.radio(
        "Modalidad de cálculo",
        ["Cálculo individual", "Cálculo múltiple"],
        horizontal=True
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        fecha_inicio = st.date_input(
            "Fecha de inicio",
            value=date.today()
        )

        unidad_plazo = st.selectbox(
            "Unidad del plazo",
            ["Días", "Semanas"]
        )

    with col2:

        if modalidad == "Cálculo individual":
            dias_plazo = st.number_input(
                "Cantidad del plazo",
                min_value=0,
                value=15,
                step=1
            )

        else:
            plazos_texto = st.text_input(
                "Ingrese los plazos de entrega",
                placeholder="Ejemplo: 4, 10, 15, 20"
            )

        tipo_dias = st.radio(
            "Tipo de plazo",
            ["Días corridos", "Días hábiles"],
            horizontal=True
        )

    excluir_feriados = st.checkbox(
        "Excluir feriados de Chile",
        value=(tipo_dias == "Días hábiles"),
        disabled=(tipo_dias == "Días corridos")
    )

    plazos_invalidos = []

    if modalidad == "Cálculo individual":
        lista_plazos = [dias_plazo]

    else:
        lista_plazos = []

        if plazos_texto.strip():

            for plazo in plazos_texto.split(","):
                plazo = plazo.strip()

                if plazo.isdigit():
                    lista_plazos.append(int(plazo))

                else:
                    plazos_invalidos.append(plazo)

    if plazos_invalidos:
        st.error(
            "Se encontraron plazos incorrectos. "
            "Ingrese solamente números enteros separados por comas."
        )

    configuracion_actual = {
        "modalidad": modalidad,
        "fecha_inicio": fecha_inicio,
        "unidad_plazo": unidad_plazo,
        "tipo_dias": tipo_dias,
        "excluir_feriados": excluir_feriados,
        "lista_plazos": lista_plazos.copy()
    }

    if (
        "configuracion_plazos" in st.session_state
        and st.session_state["configuracion_plazos"] != configuracion_actual
    ):
        st.session_state.pop("resultados_plazos", None)

    if st.button(
        "📅 Calcular fecha de entrega",
        type="primary",
        use_container_width=True,
        disabled=bool(plazos_invalidos) or not lista_plazos
    ):
        
        resultados = []

        for plazo in lista_plazos:

            if unidad_plazo == "Semanas":
                if tipo_dias == "Días corridos":
                    plazo_calculado = plazo * 7
                else:
                    plazo_calculado = plazo * 5
            else:
                plazo_calculado = plazo

            if tipo_dias == "Días corridos":
                resultado = calcular_fecha_entrega(
                    fecha_inicio,
                    plazo_calculado
                )
            else:
                resultado = calcular_dias_habiles(
                    fecha_inicio,
                    plazo_calculado,
                    excluir_feriados=excluir_feriados
                )

            resultados.append({
                "Plazo": plazo,
                "Días calculados": plazo_calculado,
                "Fecha estimada": resultado
            })
            
        st.session_state["resultados_plazos"] = resultados

        st.session_state["configuracion_plazos"] = configuracion_actual
        
    if st.session_state.get("resultados_plazos"):

        resultados = st.session_state["resultados_plazos"]
        configuracion = st.session_state["configuracion_plazos"]

        modalidad = configuracion["modalidad"]
        fecha_inicio = configuracion["fecha_inicio"]
        unidad_plazo = configuracion["unidad_plazo"]
        tipo_dias = configuracion["tipo_dias"]
        excluir_feriados = configuracion["excluir_feriados"]
            
        st.markdown(
            """
            <div style="
                background-color:#16263D;
                border-left:3px solid #2DD4D7;
                border-radius:6px;
                padding:16px 20px;
                margin-top:24px;
                margin-bottom:20px;
            ">
                <div style="
                    color:#2DD4D7;
                    font-size:12px;
                    font-weight:700;
                    letter-spacing:1.5px;
                ">
                    02 / RESULTADO DEL CÁLCULO
                </div>
                <div style="margin-top:8px; font-size:13px;">
                    Fecha estimada según las condiciones del plazo seleccionado.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if modalidad == "Cálculo individual":

            st.metric(
                label="Fecha estimada de entrega",
                value=resultados[0]["Fecha estimada"].strftime("%d-%m-%Y")
            )

            st.markdown("#### Detalle del cálculo")

            col1, col2 = st.columns(2, gap="large")

            with col1:
                st.write(
                    f"**Fecha de inicio:** "
                    f"{fecha_inicio.strftime('%d-%m-%Y')}"
                )

                st.write(
                    f"**Plazo ingresado:** "
                    f"{resultados[0]['Plazo']} {unidad_plazo.lower()}"
                )

            with col2:
                st.write(f"**Tipo de plazo:** {tipo_dias}")

                st.write(
                    f"**Feriados de Chile:** "
                    f"{'Excluidos' if tipo_dias == 'Días hábiles' and excluir_feriados else 'No excluidos'}"
                )

            st.info(
                f"El plazo equivale a {resultados[0]['Días calculados']} días "
                f"según la modalidad seleccionada."
            )

        else:

            if resultados:

                tabla_resultados = []

                for item in resultados:
                    tabla_resultados.append({
                        "Plazo": f"{item['Plazo']} {unidad_plazo.lower()}",
                        "Días calculados": item["Días calculados"],
                        "Fecha estimada": item["Fecha estimada"].strftime("%d-%m-%Y")
                    })

                st.markdown("#### Fechas estimadas de entrega")

                st.dataframe(
                    tabla_resultados,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    f"Fecha de inicio: {fecha_inicio.strftime('%d-%m-%Y')} "
                    f"| Modalidad: {tipo_dias}"
                )

            else:
                st.warning(
                    "Ingrese al menos un plazo válido, separado por comas."
                )
                
        if resultados:

            with st.expander(
                "📅 Ver feriados considerados en el cálculo",
                expanded=False
            ):

                if modalidad == "Cálculo individual":
                    resultado_seleccionado = resultados[0]

                else:
                    indice_plazo = st.selectbox(
                        "Seleccione el plazo que desea revisar",
                        range(len(resultados)),
                        format_func=lambda i: (
                            f"{resultados[i]['Plazo']} "
                            f"{unidad_plazo.lower()} - "
                            f"{resultados[i]['Fecha estimada'].strftime('%d-%m-%Y')}"
                        )
                    )

                    resultado_seleccionado = resultados[indice_plazo]

                feriados_periodo = obtener_feriados_periodo(
                    fecha_inicio,
                    resultado_seleccionado["Fecha estimada"]
                )

                if feriados_periodo:

                    tabla_feriados = []

                    for feriado in feriados_periodo:

                        excluido = (
                            tipo_dias == "Días hábiles"
                            and excluir_feriados
                            and feriado["Día hábil"]
                        )

                        tabla_feriados.append({
                            "Fecha": feriado["Fecha"].strftime("%d-%m-%Y"),
                            "Feriado": feriado["Feriado"],
                            "Situación": (
                                "Excluido del cálculo"
                                if excluido
                                else "No genera exclusión adicional"
                            )
                        })

                    st.dataframe(
                        tabla_feriados,
                        use_container_width=True,
                        hide_index=True
                    )

                    total_excluidos = sum(
                        item["Situación"] == "Excluido del cálculo"
                        for item in tabla_feriados
                    )

                    st.info(
                        f"Total de feriados excluidos del cálculo: "
                        f"{total_excluidos}"
                    )

                else:
                    st.info(
                        "No se encontraron feriados de Chile "
                        "dentro del período seleccionado."
                    )
                    
    with st.expander(
        "📆 Consultar calendario anual de feriados de Chile",
        expanded=False
    ):

        anio_consulta = st.number_input(
            "Seleccione el año",
            min_value=2020,
            max_value=2100,
            value=fecha_inicio.year,
            step=1
        )

        feriados_anuales = obtener_feriados_chile(
            anio_consulta
        )

        if feriados_anuales:

            tabla_anual = []

            dias_semana = [
                "Lunes", "Martes", "Miércoles",
                "Jueves", "Viernes", "Sábado", "Domingo"
            ]

            for feriado in feriados_anuales:

                tabla_anual.append({
                    "Fecha": feriado["Fecha"].strftime("%d-%m-%Y"),
                    "Día": dias_semana[feriado["Fecha"].weekday()],
                    "Feriado": feriado["Feriado"]
                })

            st.dataframe(
                tabla_anual,
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                f"Total de feriados registrados en {anio_consulta}: "
                f"{len(tabla_anual)}"
            )

        else:
            st.info(
                "No se encontraron feriados para el año seleccionado."
            )
