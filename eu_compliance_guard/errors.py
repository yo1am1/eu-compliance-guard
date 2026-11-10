"""The one shape of a tool error: a fixed code, never free text that could carry private input."""


class CodedError(ValueError):
    """Raised with a fixed, tool-owned code (for example "unknown-id"); the CLI prints only that code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
