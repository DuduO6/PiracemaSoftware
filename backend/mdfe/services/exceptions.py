class MdfeError(Exception):
    def __init__(self, message, *, code="mdfe_error", status_code=400, details=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class MdfeConfigurationError(MdfeError):
    def __init__(self, message, *, code="mdfe_not_configured"):
        super().__init__(message, code=code, status_code=409)


class MdfeCommunicationError(MdfeError):
    def __init__(self, message, *, code="sefaz_unavailable", inconclusive=False):
        super().__init__(message, code=code, status_code=503, details={"inconclusive": inconclusive})
        self.inconclusive = inconclusive


class MdfeRejectionError(MdfeError):
    def __init__(self, message, *, code="sefaz_rejection", sefaz_code=""):
        super().__init__(message, code=code, status_code=422, details={"sefaz_code": sefaz_code})
        self.sefaz_code = sefaz_code
