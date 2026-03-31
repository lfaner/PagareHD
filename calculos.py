from datetime import date

from cgb_utils import (
    calcular_derechos_mercado,
    siguiente_habil,
    sumar_dias_habiles,
)


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def calcular_neto_pagare(
    valor_nominal: float,       # USD
    fecha_operacion: date,
    fecha_vencimiento: date,
    plazo_operacion: str,       # "T+0" o "T+1"
    tna_descuento: float,       # %
    tna_arancel: float,         # %
    comision_pct: float,        # %
    tipo_cambio_bna: float,     # ARS/USD — vendedor BNA del día hábil anterior
) -> dict:
    """
    Calcula el neto de un pagaré Hard Dólar.

    Monedas:
      USD : valor nominal, descuento, valor descontado, arancel,
            comisión, IVA (sobre arancel + comisión), IIBB, neto
      ARS : derechos de mercado, IVA sobre derechos
            (convertidos desde USD usando tipo_cambio_bna)
    """

    DIAS_ANIO = 365
    IVA_PCT   = 0.21
    IIBB_PCT  = 0.0001   # 0,01%

    # ----------------------------------------------------------
    # Validaciones
    # ----------------------------------------------------------
    if valor_nominal <= 0:
        raise ValueError("El valor nominal debe ser mayor a 0")
    if tna_descuento < 0:
        raise ValueError("La TNA de descuento no puede ser negativa")
    if tna_arancel < 0:
        raise ValueError("El arancel no puede ser negativo")
    if comision_pct < 0:
        raise ValueError("La comisión no puede ser negativa")
    if tipo_cambio_bna <= 0:
        raise ValueError("El tipo de cambio BNA debe ser mayor a 0")
    if fecha_vencimiento < fecha_operacion:
        raise ValueError("La fecha de vencimiento no puede ser anterior a la operación")
    if plazo_operacion not in ("T+0", "T+1"):
        raise ValueError("plazo_operacion debe ser 'T+0' o 'T+1'")

    # ----------------------------------------------------------
    # Fechas
    # ----------------------------------------------------------
    fecha_acreditacion = (
        fecha_operacion
        if plazo_operacion == "T+0"
        else sumar_dias_habiles(fecha_operacion, 1)
    )

    fecha_vencimiento = siguiente_habil(fecha_vencimiento)
    fecha_cobro = sumar_dias_habiles(fecha_vencimiento, 1)   # clearing T+1

    plazo = (fecha_cobro - fecha_acreditacion).days
    if plazo <= 0:
        raise ValueError("El plazo financiero debe ser mayor a 0")

    # ----------------------------------------------------------
    # Cálculos en USD
    # ----------------------------------------------------------
    tasa_periodo  = 1 - 1 / (1 + (tna_descuento / 100) * plazo / DIAS_ANIO)
    descuento     = valor_nominal * tasa_periodo
    valor_descontado = valor_nominal - descuento

    arancel   = valor_nominal * (tna_arancel / 100) * plazo / DIAS_ANIO
    comision  = valor_nominal * (comision_pct / 100)
    iva_usd   = (arancel + comision) * IVA_PCT
    iibb_usd  = valor_descontado * IIBB_PCT

    neto_usd = valor_nominal - descuento - arancel - comision - iva_usd - iibb_usd

    # ----------------------------------------------------------
    # Derechos de mercado — se calculan sobre valor descontado
    # (en USD) y se cobran en ARS al tipo de cambio BNA
    # ----------------------------------------------------------
    derechos_usd     = calcular_derechos_mercado(valor_descontado, plazo)
    derechos_ars     = derechos_usd * tipo_cambio_bna
    iva_derechos_ars = derechos_ars * IVA_PCT

    # ----------------------------------------------------------
    # Resultado
    # ----------------------------------------------------------
    return {
        # Fechas y plazo
        "fecha_operacion":    fecha_operacion,
        "fecha_acreditacion": fecha_acreditacion,
        "fecha_vencimiento":  fecha_vencimiento,
        "fecha_cobro":        fecha_cobro,
        "plazo_dias":         plazo,
        # USD
        "valor_nominal_usd":   round(valor_nominal,    2),
        "tna_descuento":       round(tna_descuento,    4),
        "descuento_usd":       round(descuento,        2),
        "valor_descontado_usd": round(valor_descontado, 2),
        "arancel_usd":         round(arancel,          2),
        "comision_usd":        round(comision,         2),
        "iva_usd":             round(iva_usd,          2),
        "iibb_usd":            round(iibb_usd,         2),
        "neto_usd":            round(neto_usd,         2),
        # ARS
        "tipo_cambio_bna":     round(tipo_cambio_bna,  2),
        "derechos_mercado_ars": round(derechos_ars,    2),
        "iva_derechos_ars":    round(iva_derechos_ars, 2),
    }
