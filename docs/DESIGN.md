# PeerRooms design

PeerRooms brings students together in small, topic-based rooms. A fixed number of seats encourages discussion. A queue keeps admission fair, peer rankings help students find shared interests or room histories, and connection requests turn discoveries into a student network.

The browser phase uses Python 3.11, FastAPI, Uvicorn, Pydantic request and response models, and one HTML/CSS/JavaScript page. Repositories are in memory. Email sign-in supplies a demo identity through `X-Student-Id`. The browser polls Rooms every 3 seconds while open, the active room every 2 seconds, and notifications every 3 seconds. Network also refreshes while its screen is open. One Uvicorn worker owns the data for all tabs.

## Requirements

| ID | Use case | Rule |
| --- | --- | --- |
| FR1 | Register and sign in | Name and department are nonblank, year is positive, email is unique and normalized, and there are 1 to 10 distinct interests. |
| FR2 | Edit interests | Each value is trimmed and lowercase. Replacing interests is atomic. |
| FR3 | Create a room | A room has a topic, discussion prompt, type, and tags. The creator takes the first seat as host. The factory validates capacity. |
| FR4 | Browse and recommend | Browse by normalized tag or status. Active rooms are shown by default. Explicit CLOSED filtering supports viewing history. |
| FR5 | Join | OPEN seats the student, FULL queues them in FIFO order, CLOSED raises a domain error, and duplicate entry is rejected. |
| FR6 | Leave | A queued student can withdraw. A freed seat promotes the first queued student. The longest seated member inherits the host role. The last departure closes the room. |
| FR7 | Discuss | Signed-in students can read the last 50 messages. Only seated members can post. The content must contain 1 to 1,000 characters and some non-whitespace text. |
| FR8 | Moderate | Only the host can remove a seated member or close the room. Removing a seated member can promote someone. |
| FR9 | Discover | Return deterministic ranked peers with score and common interests. Exclude self, connections, pending pairs, blocked pairs, and zero scores. |
| FR10 | Manage requests | Sender creates or cancels a request. Receiver accepts or rejects. Pending pairs are unique in both directions. |
| FR11 | View network | Accepting creates one unordered connection for both students. |
| FR12 | Read notifications | Notify the appropriate students on requests, acceptance, seat promotion, member removal, and closure. Joining or queueing also informs the host, and host transfer informs the new host. |
| FR13 | Block a student | Blocking excludes the pair from discovery and prevents sending or accepting requests in either direction. Reject and cancel can resolve a pending request. |

The design goals are replaceable matching and delivery, small repository interfaces, a seat invariant that survives concurrency, injected dependencies for deterministic testing, and named exceptions. The scope covers short text discussions and one in-memory process. Future scope includes durable storage, real authentication, mobile clients, WebSockets, file sharing, moderation and reporting, and multiworker scaling.

## Actors and screen map

A Student manages their profile, rooms, discoveries, requests, network, and notifications. A Host is a seated student with additional moderation permissions in one room. The System admits the next student in line, transfers the host role, closes empty rooms, and sends notifications.

| Screen | Interactions |
| --- | --- |
| Access | Register with interest chips or sign in by email. |
| Header | Student name, notification bell with unread count, inbox and mark-read control, sign out. |
| Rooms | Recommendations, all-room cards, tag and status filters, create form, join and view buttons. |
| Room detail | Prompt, occupancy, host badge, waitlist positions, recent messages, and membership controls. Hosts can remove and close. |
| Discover | Jaccard and Weighted dropdown, scores to two decimals, common interest chips, Connect and Block. |
| Network | Incoming Accept/Reject, outgoing Cancel, accepted connections, and Block controls. |
| Profile | Edit interest chips and save. |

[Use-case diagram](uml/use-cases.png) · [PlantUML source](uml/use-cases.puml)

## Architecture and class design

A click becomes one HTTP request. The synchronous route validates the HTTP shape, reads the student's identity, and calls one method on `PeerRoomsApp`. The facade coordinates access to the use cases and builds frozen views. Services orchestrate domain operations through repository, publisher, clock, and matching contracts. Only the API package imports FastAPI. Lifespan wiring calls `build_app()` once per application instance and loads sample data only for `PEERROOMS_SEED=1`.

[Layer diagram](uml/architecture.png) · [Domain classes](uml/domain.png) · [Services and ports](uml/services.png)

| Class or interface | Responsibility |
| --- | --- |
| `Student`, `Interest` | Student is the profile entity. Interest is a frozen, hashable value object, shared by student profiles and room tags. |
| `Room`, `RoomState` | Room owns the occupants, queue, history and chat. OpenState, FullState and ClosedState implement the state-specific operations. |
| `Membership`, `Message` | Membership records a role and join time for one student in one room. The room owns its messages. |
| `ConnectionRequest`, `Connection` | The request checks actor and transition. An accepted connection is an unordered pair of two distinct IDs. |
| `Notification`, `JoinOutcome`, `LeaveResult` | The inbox item owns read status. Outcome types carry the results of joining or leaving for the service and facade. |
| `StudentService`, `RoomService`, `ConnectionService` | Coordinate profile changes, room operations, and network transitions. |
| `DiscoveryService`, `NotificationService` | Rank candidates and recommendations, or translate events into inbox items. |
| Five repository ports | Separate contracts for students, rooms, connection requests, connections, and notifications. Each in-memory adapter keeps detached snapshots. |
| `Clock`, `SystemClock`, `FakeClock` | Supply the time. A fake clock advances by minutes in tests. |
| `EventPublisher`, `EventListener`, `EventBus` | Narrow publishing and handling contracts, with synchronous dispatch by event class. |
| `MatchingStrategy`, `RoomFactory` | Swap peer scoring per request and construct rooms from the capacity registry. |

Composition links `Room` with `Membership` and `Message`. Aggregation links `Interest` with profiles and room tags. Association describes links that store IDs, including both participants of a connection request and the recipient of a notification. Membership is also an association class because the seat relationship carries its own role and time. An aggregate root is the entry point protecting a cluster of state and its invariants.

## Design patterns and SOLID

| Pattern | Implementation |
| --- | --- |
| State | The room delegates join, leave, and close to a state object. |
| Strategy | Discovery scores with a swappable Jaccard or Weighted strategy chosen for that call. |
| Composite | Weighted combines any sequence of matching strategies and itself implements MatchingStrategy. |
| Observer | Services publish immutable events. The inbox listener subscribes at bootstrap. |
| Factory | A room type's capacity range and default come from one registry entry. |
| Repository | Independent storage adapters support each entity family through an ABC. |
| Facade | PeerRoomsApp provides one transport-agnostic entry point with read-only views. |

| Principle | What to demonstrate |
| --- | --- |
| Single Responsibility | Room enforces invariants, RoomService coordinates storage and dispatch, RoomFactory chooses capacity, and NotificationService handles inbox entries. |
| Open/Closed | A strategy, room-type configuration, or external observer can be registered independently of the services. |
| Liskov Substitution | Each RoomState responds with the shared result types and RoomError family. Repositories give callers the same lookup guarantees for each implementation. |
| Interface Segregation | The small repository ports reflect use cases. Publishers receive the `publish()` method. Bus subscription happens at bootstrap. |
| Dependency Inversion | Constructors take ports and policy objects; `build_app()` supplies the concrete dependencies. Fake time and recording listeners exercise services directly. |

A dependency-injected instance gives each running app its own state. The factory suits a room with a short set of construction inputs. Connection-request transitions are a table because each operation needs an actor check and one move to a terminal state. Python uses `ABC` and `@abstractmethod` to enforce abstract contracts. `TYPE_CHECKING` lets the room-state module annotate the Room while keeping the runtime import direction from Room to its states.

## Room lifecycle, promotion, and concurrency

| State | Join | Seated departure or host removal | Host closes |
| --- | --- | --- | --- |
| OPEN | Seat the student. Filling the room enters FULL. | Remove the seat and transfer host if necessary. Close if empty. | Clear active seats and queue, retain history, enter CLOSED. |
| FULL | Append to the queue and return the position. | Promote the first queued student or switch to OPEN if the queue is empty. Transfer host if necessary. | Clear active seats and queue, retain history, enter CLOSED. |
| CLOSED | RoomClosedError | RoomClosedError | RoomClosedError |

`Room._check_invariants()` verifies unique seats within capacity, exactly one host with active seats, unique queued IDs, no seat/queue overlap, historical participation for seated students, and queues only while full. Closure leaves zero active seats and zero queued students. A host transfer uses the earliest `joined_at`, with seat insertion order for equal times. Promotion records the time the student actually took a seat.

| Step | Action | Seated in order | Queue | State | Events |
| --- | --- | --- | --- | --- | --- |
| 0 | H creates capacity 3 | H (host) | — | OPEN | RoomCreated |
| 1 | S1 joins | H, S1 | — | OPEN | StudentJoined |
| 2 | S2 joins | H, S1, S2 | — | FULL | StudentJoined |
| 3 | S3 joins | H, S1, S2 | S3 | FULL | StudentWaitlisted |
| 4 | S4 joins | H, S1, S2 | S3, S4 | FULL | StudentWaitlisted |
| 5 | S1 leaves | H, S2, S3 | S4 | FULL | StudentLeft, StudentPromoted(S3) |
| 6 | H leaves | S2 (host), S3, S4 | — | FULL | StudentLeft, StudentPromoted(S4), HostChanged(S2) |
| 7 | S3 leaves | S2 (host), S4 | — | OPEN | StudentLeft |
| 8 | S2 leaves | S4 (host) | — | OPEN | StudentLeft, HostChanged(S4) |
| 9 | S4 leaves | — | — | CLOSED | StudentLeft, RoomClosed |

In step 4, withdrawing S3 from the waitlist leaves S4 first in line. The occupied seats, state, and host are determined by the seated members. The next seat departure promotes S4.

Synchronous FastAPI routes can overlap on a thread pool. `RoomService` acquires the lock for one room across its read, change and save. A guard protects creation of the lock entries. Repository reads get detached snapshots. The service releases the room lock before it publishes to observers. One graph lock coordinates registration, blocks, and request transitions including discovery's initial network snapshot. The in-memory instance is process-local, so multiple workers would create separate room histories.

[Room state diagram](uml/room-state.png) · [Join sequence](uml/join.png) · [Leave sequence](uml/leave.png)

## Requests and notifications

A pending request moves to ACCEPTED, REJECTED, or CANCELLED. The receiver is the only actor for acceptance and rejection, and the sender is the only actor for cancellation. Each destination is terminal. A rejected or cancelled pair can open a fresh request. The repository keeps the old request by ID. Accepting saves the status and new edge under the graph lock, then publishes the event. Opening the network shows separate incoming and sent lists.

The event bus dispatches by class. The inbox listener notifies the receiver when a request arrives, the sender when accepted, the host about joining and queueing, the promoted or removed student, and the new host. Explicit closure notifies the other seated students and those who were queued. The notification owner can mark each item read. The `MessagePosted` event is available for another observer.

[Request state diagram](uml/request-state.png) · [Send and accept sequence](uml/connections.png)

## Matching and recommendation algorithms

- Jaccard divides shared interests by total distinct interests. The empty union scores 0.
- SharedRooms intersects the students' room histories, counts at most five rooms and divides by five. The history starts when a student takes a seat and includes closed rooms.
- Weighted assigns 0.7 to Jaccard and 0.3 to SharedRooms. Parts must have finite, nonnegative weights that sum to 1. Discovery filters ineligible pairs first. It then sorts by score descending, common interests descending, name, and email.
- Room recommendations use Jaccard on the student's interests and the room's tags. Eligible rooms are open or full and the student is neither seated nor queued. Equal scores favor OPEN, then the newest rooms. A room can have a score of 0 when it meets the other eligibility rules.

| Peer for Aman | Common / union | Shared rooms | Jaccard | Weighted |
| --- | --- | --- | --- | --- |
| Kabir | 1 / 4 | 3 | 0.25 | 0.355 |
| Riya | 2 / 5 | 1 | 0.40 | 0.340 |
| Neha | 0 / 6 | 0 | 0 | Excluded |

Riya leads Kabir when the interest weight exceeds `0.4 / 0.55`, about 0.7273. The optional seed creates two closed history rooms for Aman and Kabir. The [browser story](../README.md#guided-browser-story) creates the third.

| Room type | Default | Allowed |
| --- | --- | --- |
| QUICK_CHAT | 4 | 2–4 |
| DISCUSSION | 6 | 4–8 |
| PANEL | 12 | 8–20 |

## HTTP contract

All paths below start with `/api`. Protected requests carry the signed-in student's `X-Student-Id`. Entry and exit actions return response bodies for use in Swagger and the browser.

| Method and path | Facade method | Status |
| --- | --- | --- |
| POST `/students` | register | 201 |
| POST `/sessions` | sign_in | 200 |
| GET `/students/me` | profile | 200 |
| PUT `/students/me/interests` | update_interests | 200 |
| POST `/students/me/blocks/{other_id}` | block_student | 204 |
| GET `/rooms?tag=&status=` | list_rooms | 200 |
| GET `/rooms/recommended` | recommend_rooms | 200 |
| POST `/rooms` | create_room | 201 |
| GET `/rooms/{room_id}` | room_detail | 200 |
| POST `/rooms/{room_id}/join` | join_room | 200 |
| POST `/rooms/{room_id}/leave` | leave_room | 200 |
| DELETE `/rooms/{room_id}/members/{target_id}` | remove_member | 204 |
| POST `/rooms/{room_id}/close` | close_room | 204 |
| POST `/rooms/{room_id}/messages` | post_message | 201 |
| GET `/discover/peers?strategy=weighted&limit=10` | suggest_peers | 200 |
| POST `/connections/requests` | send_request | 201 |
| POST `/connections/requests/{request_id}/accept` | accept | 200 |
| POST `/connections/requests/{request_id}/reject` | reject | 200 |
| POST `/connections/requests/{request_id}/cancel` | cancel | 200 |
| GET `/connections/requests` | pending_requests | 200 |
| GET `/connections` | network_of | 200 |
| GET `/notifications` | inbox | 200 |
| POST `/notifications/{notification_id}/read` | mark_read | 204 |

The API error handler walks the exception MRO. It returns `{"error":"ExceptionClass","message":"Readable message"}` for known domain failures.

| Failure | HTTP |
| --- | --- |
| ValidationError, including InvalidCapacityError | 400 |
| Missing or blank identity header | 401 |
| PermissionDeniedError, including BlockedError | 403 |
| NotFoundError | 404 |
| ConflictError or RoomError | 409 |
| FastAPI schema validation | 422 |

## Verification matrix

| Plan edge | Coverage |
| --- | --- |
| 1 duplicate email, 15 self-request, 16 connected pair, 17 pending either way, 20 unknown IDs | Student, connection service and API tests. |
| 2 missing or too many interests and invalid profile, 3 normalized interest values | Student unit tests and sign-in/profile HTTP tests. |
| 4 capacity outside allowed range | All type boundaries in the factory tests and 400 in the HTTP tests. |
| 5 duplicate seat/queue, 6 room closed, 7 outsider or queued post, 8 invalid message length, 9 non-host moderation, 10 self-removal | Room unit tests and room HTTP tests. |
| 11 oldest becomes host, 12 queued students get a seat before closure can occur, 13 closure clears queue and notifies | Capacity-three dry run, room service, and notification tests. |
| 14 ten concurrent joins | Barrier starts ten threads. Exactly two join the host; eight receive distinct queue positions. |
| 18 wrong actor, 19 terminal requests | ConnectionRequest transitions and connection API tests. |
| 21 no shared interests or history, 22 blocked pairs | Discovery and connection service tests, plus the HTTP blocking path. |

The Python test suite covers each endpoint, repository adapter, event delivery, seed loading, and matching. The browser was exercised at 1280px and checked for overflow at 390px. The four-tab walkthrough verified session isolation, polling, chat, moderation, discovery, account actions, and the network. Swagger was used to authorize and execute join, leave, and discovery while external requests were blocked.

## Implementation layout and review

`domain/` contains entities, state, events, result objects, enums, and exceptions. `ports/` defines ABC contracts. `infrastructure/` provides dictionaries, clocks, the bus, and ID creation. `factories/` and `strategies/` contain replaceable policies. `services/` coordinates use cases. `app/` wires the services and adapts to frozen views. `api/` adds routing, schemas, and Swagger. `web/` holds the three browser files. `seed.py` is optional startup data. `tests/` and `docs/uml/` contain the verification suite and diagrams.

The UML comparison used class and package diagrams generated from the source with `pyreverse -o mmd -p PeerRooms peerrooms`. The domain diagram includes zero seats for CLOSED, a separate `JoinOutcome` for the result plus position, and optional `host_id` and `responded_at`. The service diagram records the injected clock and read-only room/student lookups needed to label notifications. App-only views and API-only models keep serialization out of the domain. The room service's event order follows the sequence diagrams. The service saves, unlocks, then publishes.

## Presentation and viva

For a 10–12 minute presentation, walk through the problem, scope, requirements, use cases, architecture, domain classes, service dependencies, patterns plus room state, SOLID, the leave sequence, ranking and last-seat concurrency, tests, and future scope. Spend most of the time on the class diagrams, patterns, and SOLID before opening the browser walkthrough and Swagger.

| Viva question | Answer |
| --- | --- |
| Why is Room an aggregate root? | It owns and protects the capacity, role, queue and chat rules. |
| Why use a State class per room state? | Each state implements its own behavior for join, leave and close behind one contract. |
| Why a transition table for requests? | Each action has an actor rule and a single terminal status. |
| How do state classes access room internals? | They are implementation details of the aggregate and use its private operations. |
| Where is Open/Closed visible? | Strategy registry, capacity registry, and event subscriptions provide extension points. |
| What contract must a substitute state obey? | Return the same outcome type or raise a documented RoomError. |
| How does dependency injection help tests? | A fake clock and in-memory ports make temporal rules and dispatch observable. |
| Why build one set of objects at startup? | The composition root gives each app instance isolated dependencies. |
| How do you explain composition and aggregation? | The room owns messages. Interests are independent value objects shared by profiles and rooms. |
| What prevents oversubscription? | One room lock serializes read, mutation and save for the last seat. |
| Why publish after unlocking? | Listener work can run while another request takes the room lock. |
| How do you pick the next host? | The earliest `joined_at` among the remaining seated members, with insertion order as the tiebreaker. |
| Why store IDs for associations? | IDs avoid circular object graphs and can reference stored records. |
| What does Jaccard miss? | It treats a rare interest and a widespread interest as equally informative. |
| What if B already sent A a request? | The pair lookup checks both directions and tells A to accept the incoming request. |
| How would a scheduled room fit? | Add a start time and a RoomState that defines pre-start behavior. |
| What is the role of FastAPI? | It translates HTTP into the same facade calls available to another client. |
| Why email-only sign-in? | The supplied identity is enough to demonstrate multiple students and domain permissions. |
| Why use polling? | The demo needs frequent refreshes and a small HTTP implementation. |
| Why is one worker required? | Dictionaries are process-local. |
| Why separate Pydantic models from views? | Each HTTP shape can evolve independently of the app and domain types. |
| Why is strategy chosen in the request? | A strategy choice belongs to the caller of that request. |
| Why are routes synchronous? | Each route uses synchronous services and runs in the thread pool. |
| How are HTTP errors chosen? | Map the nearest registered base class in the domain exception's MRO. |

Practice drawing the room state diagram and the leave sequence from memory. Replay steps 4–7 of the capacity-three run aloud.

## Future scope

| Extension | Entry point |
| --- | --- |
| PostgreSQL and multiple workers | Repository adapters and a database transaction that locks the room row. |
| College SSO or JWT | Identity dependency and token verification. |
| Real-time browser updates | EventListener for WebSockets, with a message queue if needed. |
| React or mobile client | REST API and OpenAPI schema. |
| Email or push | An added EventListener, with asynchronous delivery if needed. |
| Scheduled rooms | A new RoomState and schedule metadata. |
| Smarter matching | More strategies in the registry, such as interest rarity or department. |
| Reporting, moderation, and file sharing | Dedicated use cases that work with room roles and events. |

The terminal walkthrough is phase two.
