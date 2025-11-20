class InvalidDateError(Exception):
    """Custom exception for invalid date operations."""
    def __init__(self, message: str = "The date provided is invalid."):
        self.message = message
        super().__init__(self.message)
    