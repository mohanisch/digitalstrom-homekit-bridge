import random

from fnvhash import fnv1a_32

INVALID_AIDS = (0, 1)

AID_MIN = 2
AID_MAX = 18446744073709551615


def get_system_unique_id():
    """Determine the system wide unique_id for an entity."""
    return f"einkackmitdigitaltrom"


def _generate_aids(unique_id: str) -> int:
    """Generate accessory aid."""
    yield fnv1a_32(unique_id.encode("utf-8"))

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

    def get_or_allocate_aid(self, unique_id: str):
        """Allocate (and return) a new aid for an accessory."""
        if unique_id and unique_id in self.allocations:
            return self.allocations[unique_id]

        for aid in _generate_aids(unique_id):
            if aid in INVALID_AIDS:
                continue
            if aid not in self.allocated_aids:
                # Prefer the unique_id over the entitiy_id
                storage_key = unique_id
                self.allocations[storage_key] = aid
                self.allocated_aids.add(aid)
                #self.async_schedule_save()
                return aid
        raise ValueError(
            f"Unable to generate unique aid allocation for {unique_id}"
        )

    def delete_aid(self, storage_key: str):
        """Delete an aid allocation."""
        if storage_key not in self.allocations:
            return

        aid = self.allocations.pop(storage_key)
        self.allocated_aids.discard(aid)
        self.async_schedule_save()
