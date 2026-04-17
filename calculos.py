from datetime import date

from cgb_utils import (
    calcular_derechos_mercado,
    siguiente_habil,
    sumar_dias_habiles,
)


def calcular_cft_tea_cartera(detalle: list[dict]) -> float:
    """
    CFT TEA de la cartera (solo flujos en USD).

    Resuelve por bisección:
      sum(neto_i) = sum(nominal_i / (1 + TEA)^(plazo_i / 365))

    Retorna el TEA como porcentaje, ej: 45.23
    """
    if not detalle:
        raise ValueError("No hay pagarés para calcular el CFT")

    flujos = [
        (p["neto_usd"], p["valor_nominal_usd"], p["plazo_dias"])
        for p in detalle
    ]

    suma_netos = sum(neto for neto, _, _ in flujos)

    def f(r):
        return (
            sum(nominal / (1 + r) ** (plazo / 365) for _, nominal, plazo in flujos)
            - suma_netos
        )

    lo, hi = 1e-6, 100.0          # 0,0001 % … 10 000 % TEA
    if f(lo) < 0:
        raise ValueError("No se puede calcular el CFT: el neto supera al nominal")

    for _ in range(200):           # bisección — converge en ~50 iteraciones
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
        if (hi - lo) < 1e-10:
            break

    return round((lo + hi) / 2 * 100, 2)   # retorna como %


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def calcular_neto_pagare(
    valor_nominal: float,        # USD
    fecha_operacion: date,
    fecha_vencimiento: date,
    plazo_operacion: str,        # "T+0" o "T+1"
    tna_descuento: float,        # %
    tna_arancel: float,          # %
    comision_pct: float,         # %
    tipo_cambio_bna: float,      # ARS/USD — vendedor BNA del día hábil anterior
) -> dict:
    """
    Calcula el neto de un pagaré Hard Dólar.

    Monedas:
      USD : valor nominal, descuento, valor descontado, arancel, comisión, neto
      ARS : IVA (sobre arancel + comisión), derechos de mercado, IVA sobre
            derechos, IIBB (convertidos desde USD usando tipo_cambio_bna)
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
    fecha_cobro = sumar_dias_habiles(fecha_vencimiento, 2)   # clearing T+2

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

    neto_usd = valor_nominal - descuento - arancel - comision

    # ----------------------------------------------------------
    # Cargos en ARS (convertidos desde USD al tipo de cambio BNA)
    # ----------------------------------------------------------
    iva_ars            = (arancel + comision) * IVA_PCT * tipo_cambio_bna
    derechos_usd       = calcular_derechos_mercado(valor_descontado, plazo)
    derechos_ars       = derechos_usd * tipo_cambio_bna
    iva_derechos_ars   = derechos_ars * IVA_PCT
    iibb_ars           = valor_descontado * IIBB_PCT * tipo_cambio_bna

    # ----------------------------------------------------------
    # Resultado
    # ----------------------------------------------------------
    return {
        # Fechas y plazo
        "fecha_operacion":   fecha_operacion,
        "fecha_acreditacion": fecha_acreditacion,
        "fecha_vencimiento":  fecha_vencimiento,
        "fecha_cobro":        fecha_cobro,
        "plazo_dias":         plazo,
        # USD
        "valor_nominal_usd":    round(valor_nominal,     2),
        "tna_descuento":        round(tna_descuento,     4),
        "descuento_usd":        round(descuento,         2),
        "valor_descontado_usd": round(valor_descontado,  2),
        "arancel_usd":          round(arancel,           2),
        "comision_usd":         round(comision,          2),
        "neto_usd":             round(neto_usd,          2),
        # ARS
        "tipo_cambio_bna":      round(tipo_cambio_bna,   2),
        "iva_ars":              round(iva_ars,            2),
        "derechos_mercado_ars": round(derechos_ars,       2),
        "iva_derechos_ars":     round(iva_derechos_ars,   2),
        "iibb_ars":             round(iibb_ars,           2),
    }
