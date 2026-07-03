import random
from dataclasses import dataclass

from faker import Faker

from ..nacha.checksum import make_routing_number

fake = Faker()


def random_routing(rng: random.Random) -> str:
    prefix = "".join(str(rng.randint(0, 9)) for _ in range(8))
    return make_routing_number(prefix)


@dataclass
class Profile:
    name: str
    account_number: str
    individual_id: str
    routing: str
    account_type: str  # "checking" or "savings"


@dataclass
class CompanyProfile:
    name: str
    company_id: str


def generate_profiles(count: int, rng: random.Random) -> list[Profile]:
    return [
        Profile(
            name=fake.name().upper()[:22],
            account_number=str(rng.randint(10**9, 10**12 - 1)),
            individual_id=f"EMP{i:05d}",
            routing=random_routing(rng),
            account_type=rng.choice(["checking", "savings"]),
        )
        for i in range(count)
    ]


def generate_company_profile(rng: random.Random) -> CompanyProfile:
    return CompanyProfile(
        name=fake.company().upper()[:16],
        company_id="1" + str(rng.randint(10**8, 10**9 - 1)),
    )
