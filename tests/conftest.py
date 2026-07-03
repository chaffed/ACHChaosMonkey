import pytest

from achchaosmonkey.nacha.checksum import make_routing_number
from achchaosmonkey.nacha.records import AchFileRecord, Batch, BatchHeader, EntryDetail, FileHeader

ROUTING = make_routing_number("02100002")


def build_sample_file(num_entries: int = 2) -> AchFileRecord:
    fh = FileHeader(
        immediate_destination=ROUTING,
        immediate_origin="123456789",
        immediate_destination_name="FIRST BANK",
        immediate_origin_name="ACME CORP",
        file_creation_date="260703",
        file_creation_time="0800",
        file_id_modifier="A",
    )
    bh = BatchHeader(
        company_name="ACME CORP",
        company_identification="1123456789",
        sec_code="PPD",
        company_entry_description="PAYROLL",
        effective_entry_date="260704",
        originating_dfi=ROUTING[:8],
        batch_number=1,
    )
    entries = [
        EntryDetail(
            transaction_code="22",
            receiving_dfi_routing=ROUTING,
            dfi_account_number=f"00012345678{i}",
            amount_cents=100000 + i,
            individual_name=f"EMPLOYEE {i}",
            individual_id=f"EMP{i:03d}",
            trace_number=f"{ROUTING[:8]}{i:07d}",
        )
        for i in range(num_entries)
    ]
    batch = Batch(header=bh, entries=entries)
    return AchFileRecord(header=fh, batches=[batch])


@pytest.fixture
def sample_file_record():
    return build_sample_file()
