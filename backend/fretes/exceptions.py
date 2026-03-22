class FretesError(Exception):
    default_message = "Não foi possível calcular o frete."

    def __init__(self, message=None, code="fretes_error", status_code=400, extra=None):
        self.message = message or self.default_message
        self.code = code
        self.status_code = status_code
        self.extra = extra or {}
        super().__init__(self.message)


class FretesValidationError(FretesError):
    default_message = "Os dados informados são inválidos."

    def __init__(self, message=None, extra=None):
        super().__init__(message=message or self.default_message, code="validation_error", status_code=400, extra=extra)


class GeocodingError(FretesError):
    def __init__(self, target="origem", message=None):
        default_message = (
            "Não foi possível localizar a cidade de origem."
            if target == "origem"
            else "Não foi possível localizar a cidade de destino."
        )
        super().__init__(message=message or default_message, code="geocoding_error", status_code=400)


class RouteCalculationError(FretesError):
    default_message = "Não foi possível calcular a rota entre origem e destino."

    def __init__(self, message=None):
        super().__init__(message=message or self.default_message, code="route_error", status_code=400)


class TollEstimationError(FretesError):
    default_message = "A rota foi encontrada, mas os pedágios não puderam ser estimados."

    def __init__(self, message=None):
        super().__init__(message=message or self.default_message, code="toll_error", status_code=400)


class ProviderConfigurationError(FretesError):
    default_message = "A integração externa de fretes não está configurada corretamente."

    def __init__(self, message=None):
        super().__init__(message=message or self.default_message, code="provider_configuration_error", status_code=500)

