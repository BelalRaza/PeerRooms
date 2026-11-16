import pytest

from tests.helpers import student
from peerrooms.domain.exceptions import StudentNotFoundError
from peerrooms.domain.interest import Interest
from peerrooms.infrastructure.in_memory_repositories import InMemoryStudentRepository


def test_student_save_lookup_and_snapshot() -> None:
    repo = InMemoryStudentRepository()
    addy = student("Addy")
    repo.save(addy)
    addy.add_interest(Interest.of("design"))
    assert repo.find_by_email(" ADDY@COLLEGE.EDU ").interests == {Interest.of("ai")}
    repo.save(addy)
    assert len(repo.all()) == 1 and repo.get(addy.id).interests == addy.interests
    with pytest.raises(StudentNotFoundError):
        repo.get("missing")
    with pytest.raises(StudentNotFoundError):
        repo.find_by_email("missing@college.edu")
