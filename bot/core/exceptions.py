class WindowNotFoundError(Exception):
    pass


class LicenseAuthenticationError(Exception):
    pass


class GameStateException(Exception):
    pass


class StoppedException(Exception):
    pass


class PausedException(Exception):
    pass


class ExportContentsException(Exception):
    pass
