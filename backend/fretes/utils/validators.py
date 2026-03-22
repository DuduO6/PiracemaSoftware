from .money import to_decimal


def normalize_text(value):
    return " ".join((value or "").strip().split())


def build_location_query(city, state=""):
    city = normalize_text(city)
    state = normalize_text(state).upper()
    if state:
        return f"{city}, {state}, Brasil"
    return f"{city}, Brasil"


def bool_multiplier(is_round_trip):
    return 2 if is_round_trip else 1


def ensure_non_negative(value):
    return max(to_decimal(value), to_decimal("0"))

