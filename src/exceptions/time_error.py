class InvalidTimeError(Exception):
    """Custom exception for invalid time operations."""
    def __init__(self, message: str = "The time provided is invalid."):
        self.message = message
        super().__init__(self.message)