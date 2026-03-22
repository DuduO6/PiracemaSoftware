from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANTIZER = Decimal("0.01")
RATE_QUANTIZER = Decimal("0.0001")


def to_decimal(value):
    return Decimal(str(value))


def round_money(value):
    return to_decimal(value).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)


def round_rate(value):
    return to_decimal(value).quantize(RATE_QUANTIZER, rounding=ROUND_HALF_UP)


def decimal_to_float(value):
    return float(round_money(value))

