class NachaFormatError(Exception):
    """Base exception for NACHA format errors."""


class FieldLengthError(NachaFormatError):
    """A field value does not fit its fixed-width slot."""


class RecordParseError(NachaFormatError):
    """A line could not be parsed into a known, well-formed record."""
