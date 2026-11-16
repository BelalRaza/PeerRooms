from tests.helpers import NOW
from peerrooms.domain.connection import Connection
from peerrooms.infrastructure.in_memory_repositories import InMemoryConnectionRepository


def test_unordered_connection_pairs_replace_and_filter() -> None:
    repo = InMemoryConnectionRepository()
    repo.save(Connection("first", frozenset({"A", "B"}), NOW))
    repo.save(Connection("replacement", frozenset({"B", "A"}), NOW))
    assert repo.are_connected("A", "B") and repo.are_connected("B", "A")
    assert [link.id for link in repo.connections_of("A")] == ["replacement"]
    assert not repo.are_connected("A", "C") and not repo.connections_of("C")
