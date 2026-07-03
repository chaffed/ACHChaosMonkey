import pytest

from achchaosmonkey.nacha.checksum import compute_aba_check_digit, is_valid_routing_number, make_routing_number

# Real-world-shaped routing numbers with known-correct check digits.
KNOWN_VALID_ROUTING_NUMBERS = [
    "021000021",  # JPMorgan Chase NY
    "011401533",  # Bank of America MA
    "091000019",  # Wells Fargo (Minneapolis Fed)
]


@pytest.mark.parametrize("routing9", KNOWN_VALID_ROUTING_NUMBERS)
def test_known_valid_routing_numbers_pass(routing9):
    assert is_valid_routing_number(routing9)


@pytest.mark.parametrize("routing9", KNOWN_VALID_ROUTING_NUMBERS)
def test_corrupted_check_digit_fails(routing9):
    prefix = routing9[:8]
    correct = routing9[8]
    for wrong_digit in "0123456789":
        if wrong_digit == correct:
            continue
        assert not is_valid_routing_number(prefix + wrong_digit)


def test_make_routing_number_round_trips():
    for routing9 in KNOWN_VALID_ROUTING_NUMBERS:
        assert make_routing_number(routing9[:8]) == routing9


def test_compute_check_digit_requires_eight_digits():
    with pytest.raises(ValueError):
        compute_aba_check_digit("1234567")


def test_invalid_routing_number_wrong_length():
    assert not is_valid_routing_number("12345")


def test_invalid_routing_number_non_digit():
    assert not is_valid_routing_number("02100002X")
