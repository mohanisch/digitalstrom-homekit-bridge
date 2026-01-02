import random
from collections.abc import Generator

from fnvhash import fnv1a_32

INVALID_AIDS = (0, 1)

AID_MIN = 2
AID_MAX = 18446744073709551615


def _generate_aids(entity_id: str) -> Generator[int, None, None]:
    """Generate accessory aid."""
    yield fnv1a_32(entity_id.encode("utf-8"))

    for _ in range(5):
        yield random.randrange(AID_MIN, AID_MAX)


class AccessoryAidStorage:
    def __init__(self) -> None:
        """Create a new entity map store."""
        self.allocations = {}
        self.allocated_aids = set()
        self._entry = "entry"
        self.store = None
        self._entity_registry = None

    def get_or_allocate_aid(self, entity_id: str):
        if entity_id and entity_id in self.allocations:
            return self.allocations[entity_id]

        for aid in _generate_aids(entity_id):
            if aid in INVALID_AIDS:
                continue
            if aid not in self.allocated_aids:
                storage_key = entity_id
                self.allocations[storage_key] = aid
                self.allocated_aids.add(aid)
                return aid
        raise ValueError(
            f"Unable to generate unique aid allocation for {entity_id}"
        )
