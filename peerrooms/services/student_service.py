from _thread import LockType
from collections.abc import Callable, Iterable

from peerrooms.domain.exceptions import DuplicateEmailError, StudentNotFoundError
from peerrooms.domain.interest import Interest
from peerrooms.domain.student import Student
from peerrooms.ports.repositories import StudentRepository


class StudentService:
    """Coordinate registration, profile edits, and blocking (FR1, FR2, FR13)."""

    def __init__(self, students: StudentRepository, ids: Callable[[], str], writes: LockType) -> None:
        self._students, self._ids, self._writes = students, ids, writes

    def register(
        self, name: str, email: str, department: str, year: int, interests: Iterable[str],
    ) -> Student:
        student = Student(
            self._ids(), name, email, department, year,
            frozenset(Interest.of(value) for value in interests),
        )
        with self._writes:
            try:
                self._students.find_by_email(student.email)
            except StudentNotFoundError:
                self._students.save(student)
            else:
                raise DuplicateEmailError(f"{student.email} is already registered.")
        return student

    def sign_in(self, email: str) -> Student:
        return self._students.find_by_email(email)

    def profile(self, student_id: str) -> Student:
        return self._students.get(student_id)

    def update_interests(self, student_id: str, interests: Iterable[str]) -> Student:
        with self._writes:
            student = self._students.get(student_id)
            student.replace_interests(Interest.of(value) for value in interests)
            self._students.save(student)
        return student

    def block_student(self, student_id: str, other_id: str) -> None:
        with self._writes:
            student = self._students.get(student_id)
            self._students.get(other_id)
            student.block(other_id)
            self._students.save(student)
