import streamlit as st

from Calculadora_Admisibilidad.app_admisibilidad import mostrar_calculadora
from Calculadora_Plazos_Entrega.app_plazos_entrega import mostrar_calculadora_plazos
from Evaluacion_Ofertas.app_evaluacion import mostrar_evaluacion_ofertas
from Inteligencia_Economica.app_inteligencia_economica import mostrar_analisis_economico

st.set_page_config(
    page_title="Herramientas de Compras | Enterprise",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
<div style="padding: 24px 30px; background: linear-gradient(120deg, #14243A, #102C3B); border: 1px solid #253D52; border-radius: 14px; margin-bottom: 28px;">
    <div style="color: #56D8CC; font-size: 12px; font-weight: 700; letter-spacing: 2px; margin-bottom: 8px;">
        PROCUREMENT INTELLIGENCE
    </div>
    <div style="color: #FFFFFF; font-size: 30px; font-weight: 700; margin-bottom: 8px;">
        Herramientas de Compras
    </div>
    <div style="color: #A9BED0; font-size: 14px;">
        Plataforma de análisis y apoyo a decisiones de abastecimiento
    </div>
</div>
    """,
    unsafe_allow_html=True
)


with st.sidebar:
    st.markdown(
        """
<div style="padding: 12px 4px 20px 4px;">
    <div style="color: #56D8CC; font-size: 12px; font-weight: 700; letter-spacing: 1.5px;">
        PROCUREMENT SUITE
    </div>
    <div style="color: #FFFFFF; font-size: 20px; font-weight: 700; margin-top: 8px;">
        Panel de herramientas
    </div>
    <div style="color: #91A4BC; font-size: 12px; margin-top: 6px;">
        Gestión y análisis de compras
    </div>
</div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # ========================================================
    # MENÚ PRINCIPAL DE HERRAMIENTAS
    # ========================================================

    herramienta = st.radio(
        "HERRAMIENTAS DISPONIBLES",
        [
            "Evaluación de Ofertas",
            "Calculadora de Plazos de Entrega",
            "Inteligencia Económica"
        ]
    )

# ============================================================
# SECCIÓN 1 - EVALUACIÓN DE OFERTAS
# ============================================================

if herramienta == "Evaluación de Ofertas":

    st.subheader("📋 Evaluación de Ofertas")

    st.caption(
        "Herramientas para analizar la admisibilidad, "
        "comparación económica y cumplimiento de ofertas."
    )

    # ========================================================
    # SELECCIÓN DE HERRAMIENTAS DE EVALUACIÓN DE OFERTAS
    # ========================================================

    modulo_ofertas = st.radio(
        "Selecciona una herramienta",
        [
            "Calculadora de Admisibilidad",
            "Evaluación Comparativa de Ofertas"
        ],
        horizontal=True,
        key="modulo_evaluacion_ofertas"
    )

    if modulo_ofertas == "Calculadora de Admisibilidad":
        mostrar_calculadora(modo_fijo="Oferta individual")

    elif modulo_ofertas == "Evaluación Comparativa de Ofertas":
        mostrar_evaluacion_ofertas()
    
elif herramienta == "Calculadora de Plazos de Entrega":
    mostrar_calculadora_plazos()


elif herramienta == "Inteligencia Económica":
    mostrar_analisis_economico()
