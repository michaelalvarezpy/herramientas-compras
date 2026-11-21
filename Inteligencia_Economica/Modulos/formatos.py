"""Formatos numéricos de la herramienta económica."""

def formato_moneda(valor):
    return (
        f"{valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

def formato_pesos(valor):
    signo = "-" if valor < 0 else ""
    return f"{signo}${formato_moneda(abs(valor))}"
