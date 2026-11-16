from peerrooms.app.facade import PeerRoomsApp
from peerrooms.domain.enums import RoomType


def seed(app: PeerRoomsApp) -> None:
    students = {
        name: app.register(name, f"{name.lower()}@college.edu", department, year, interests)
        for name, department, year, interests in (
            ("Aman", "Computer Science", 3, ["python", "ai", "startups", "football"]),
            ("Riya", "Design", 2, ["ai", "startups", "design"]),
            ("Kabir", "Engineering", 3, ["football"]),
            ("Neha", "Liberal Arts", 2, ["music", "art"]),
            ("Dev", "Computer Science", 2, ["python", "ai"]),
            ("Isha", "Design", 3, ["design", "startups"]),
        )
    }
    aman, kabir = students["Aman"].id, students["Kabir"].id
    for topic, tag in (("Campus football", "football"), ("Student clubs", "campus")):
        room = app.create_room(
            aman, RoomType.QUICK_CHAT, topic, "What would you like to try this term?", [tag],
        )
        app.join_room(kabir, room.id)
        app.close_room(aman, room.id)
