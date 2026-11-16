from collections.abc import Iterable
from dataclasses import dataclass, field
import re

from peerrooms.domain.exceptions import ValidationError
from peerrooms.domain.interest import Interest


def normalize_email(raw: str) -> str:
    return raw.strip().lower()


@dataclass(eq=False, slots=True)
class Student:
    """A student profile that owns its interests and blocks (FR1, FR2, FR13)."""

    id: str
    name: str
    email: str
    department: str
    year: int
    interests: frozenset[Interest]
    _blocked_student_ids: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.email = normalize_email(self.email)
        self.department = self.department.strip()
        if not self.name:
            raise ValidationError("Name cannot be blank.")
        if re.fullmatch(r"[^@\s]+@[^@\s]+", self.email) is None:
            raise ValidationError("Enter a valid college email address.")
        if not self.department:
            raise ValidationError("Department cannot be blank.")
        if type(self.year) is not int or self.year < 1:
            raise ValidationError("Year must be a positive integer.")
        self.replace_interests(self.interests)

    def replace_interests(self, interests: Iterable[Interest]) -> None:
        normalized = frozenset(interests)
        if not 1 <= len(normalized) <= 10:
            raise ValidationError("Choose between 1 and 10 distinct interests.")
        self.interests = normalized

    def add_interest(self, interest: Interest) -> None:
        self.replace_interests(self.interests | {interest})

    def remove_interest(self, interest: Interest) -> None:
        self.replace_interests(self.interests - {interest})

    def common_interests(self, other: "Student") -> frozenset[Interest]:
        return self.interests & other.interests

    def block(self, other_id: str) -> None:
        if other_id == self.id:
            raise ValidationError("You cannot block yourself.")
        self._blocked_student_ids.add(other_id)

    def blocks(self, other_id: str) -> bool:
        return other_id in self._blocked_student_ids
