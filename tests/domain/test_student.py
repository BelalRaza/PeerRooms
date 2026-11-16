import pytest

from tests.helpers import student
from peerrooms.domain.exceptions import ValidationError
from peerrooms.domain.interest import Interest
from peerrooms.domain.student import Student


@pytest.mark.parametrize(("name", "email", "department", "year", "count"), [
    (" ", "addy@college.edu", "CS", 2, 1),
    ("Addy", "invalid", "CS", 2, 1),
    ("Addy", " a @ b ", "CS", 2, 1),
    ("Addy", "addy@college.edu", " ", 2, 1),
    ("Addy", "addy@college.edu", "CS", 0, 1),
    ("Addy", "addy@college.edu", "CS", 2, 0),
    ("Addy", "addy@college.edu", "CS", 2, 11),
])
def test_student_validation(name: str, email: str, department: str, year: int, count: int) -> None:
    with pytest.raises(ValidationError):
        Student("id", name, email, department, year, frozenset(Interest.of(str(i)) for i in range(count)))


def test_interest_normalization_and_updates() -> None:
    addy = student("Addy", "AI", " ai", "ai")
    assert addy.interests == {Interest.of("ai")}
    assert Interest.of("AI ") == Interest("ai")
    addy.add_interest(Interest.of("Python"))
    assert addy.common_interests(student("Tania", "python")) == {Interest.of("python")}
    addy.remove_interest(Interest.of("ai"))
    with pytest.raises(ValidationError):
        addy.remove_interest(Interest.of("python"))
    assert addy.interests == {Interest.of("python")}
    with pytest.raises(ValidationError):
        Interest.of(" ")


def test_self_block_is_rejected() -> None:
    addy = student("Addy")
    with pytest.raises(ValidationError):
        addy.block(addy.id)
