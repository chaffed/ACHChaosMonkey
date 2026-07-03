"""ABA routing-number check-digit algorithm."""


def compute_aba_check_digit(routing_prefix: str) -> str:
    if len(routing_prefix) != 8 or not routing_prefix.isdigit():
        raise ValueError("routing_prefix must be exactly 8 digits")
    d = [int(c) for c in routing_prefix]
    total = 3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + 1 * (d[2] + d[5])
    return str((10 - total % 10) % 10)


def make_routing_number(routing_prefix: str) -> str:
    return routing_prefix + compute_aba_check_digit(routing_prefix)


def is_valid_routing_number(routing9: str) -> bool:
    if len(routing9) != 9 or not routing9.isdigit():
        return False
    prefix, check_digit = routing9[:8], routing9[8]
    return compute_aba_check_digit(prefix) == check_digit
