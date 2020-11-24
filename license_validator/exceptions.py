class LicenseRetrievalError(Exception):
    pass


class LicenseExpirationError(Exception):
    pass


class LicenseServerError(Exception):
    pass


class LicenseConnectionError(Exception):
    pass


class LicenseIntegrityError(Exception):
    pass
