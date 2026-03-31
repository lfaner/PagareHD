from datetime import date

from cgb_utils import (
    calcular_derechos_mercado_pagare,
    siguiente_habil,
    sumar_dias_habiles,
)


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def calcular_neto_pagare(
    valor_nominal: float,
    fecha_operacion: date,
    fecha_vencimiento: date,
    plazo_operacion: str,   # "T+0" o "T+1"
    tna_descuento: float,   # %
    tna_arancel: float,     # %
    comision_pct: float     # %
) -> dict:

    DIAS_ANIO = 365
    IVA_PCT = 0.21
    IIBB_PCT = 0.0001  # 0,01%

    if valor_nominal <= 0:
        raise ValueError("El valor nominal debe ser mayor a 0")
    if tna_descuento < 0:
        raise ValueError("La TNA de descuento no puede ser negativa")
    if tna_arancel < 0:
        raise ValueError("El arancel no puede ser negativo")
    if comision_pct < 0:
        raise ValueError("La comisión no puede ser negativa")
    if fecha_vencimiento < fecha_operacion:
        raise ValueError("La fecha de vencimiento no puede ser anterior a la operación")

    if plazo_operacion not in ("T+0", "T+1"):
        raise ValueError("plazo_operacion debe ser 'T+0' o 'T+1'")

    # ------------------------------------------------------
    # Fecha de acreditación
    # ------------------------------------------------------
    fecha_acreditacion = (
        fecha_operacion
        if plazo_operacion == "T+0"
        else sumar_dias_habiles(fecha_operacion, 1)
    )

    # ------------------------------------------------------
    # Fecha efectiva de cobro (clearing T+1 hábil)
    # ------------------------------------------------------
    fecha_vencimiento = siguiente_habil(fecha_vencimiento)
    fecha_cobro = sumar_dias_habiles(fecha_vencimiento, 1)

    # ------------------------------------------------------
    # Plazo financiero
    # ------------------------------------------------------
    plazo = (fecha_cobro - fecha_acreditacion).days
    if plazo <= 0:
        raise ValueError("El plazo financiero debe ser mayor a 0")

    # ------------------------------------------------------
    # Descuento financiero (fórmula correcta)
    # ------------------------------------------------------
    tasa_descuento_periodo = 1 - 1 / (1 + (tna_descuento / 100) * plazo / DIAS_ANIO)
    descuento = valor_nominal * tasa_descuento_periodo

    # ------------------------------------------------------
    # Valor descontado
    # ------------------------------------------------------
    valor_descontado = valor_nominal - descuento

    # ------------------------------------------------------
    # Derechos de mercado (sobre valor descontado)
    # ------------------------------------------------------
    derechos_mercado = calcular_derechos_mercado_pagare(valor_descontado, plazo)

    # ------------------------------------------------------
    # Arancel (TNA devengada)
    # ------------------------------------------------------
    arancel = valor_nominal * (tna_arancel / 100) * plazo / DIAS_ANIO

    # ------------------------------------------------------
    # Comisión
    # ------------------------------------------------------
    comision = valor_nominal * (comision_pct / 100)

    # ------------------------------------------------------
    # Impuestos
    # ------------------------------------------------------
    iva = (arancel + comision + derechos_mercado) * IVA_PCT
    iibb = valor_descontado * IIBB_PCT

    # ------------------------------------------------------
    # Neto final
    # ------------------------------------------------------
    neto = (
        valor_nominal
        - descuento
        - derechos_mercado
        - arancel
        - comision
        - iva
        - iibb
    )

    return {
        "valor_nominal": round(valor_nominal, 2),
        "tna_descuento": round(tna_descuento, 4),
        "fecha_operacion": fecha_operacion,
        "fecha_acreditacion": fecha_acreditacion,
        "fecha_vencimiento": fecha_vencimiento,
        "fecha_cobro": fecha_cobro,
        "plazo_dias": plazo,
        "descuento": round(descuento, 2),
        "valor_descontado": round(valor_descontado, 2),
        "derechos_mercado": round(derechos_mercado, 2),
        "arancel": round(arancel, 2),
        "comision": round(comision, 2),
        "iva": round(iva, 2),
        "iibb": round(iibb, 2),
        "neto_a_recibir": round(neto, 2),
    }
