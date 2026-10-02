class DomainError(Exception):
    """Raised by services; main.py turns it into an HTTP response."""
    def __init__(self, status: int, msg: str):
        self.status, self.msg = status, msg
