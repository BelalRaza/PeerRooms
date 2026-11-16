from dataclasses import dataclass

from peerrooms.domain.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class Interest:
    """An immutable, normalized interest or room tag."""

    name: str

    def __post_init__(self) -> None:
        name = self.name.strip().lower()
        if not name:
            raise ValidationError("An interest or tag cannot be blank.")
        object.__setattr__(self, "name", name)

    @classmethod
    def of(cls, raw: str) -> "Interest":
        return cls(raw)
