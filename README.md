# PeerRooms

PeerRooms is a Python 3.11 low-level design project for small student discussion rooms, peer discovery, and connection requests. FastAPI serves a one-page browser demo, plus interactive Swagger documentation. Each browser tab can sign in as a different student.

## Start the browser demo

Run these commands from this project directory.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m uvicorn peerrooms.api.main:app --workers 1
```

- [Browser demo](http://127.0.0.1:8000/)
- [Swagger UI](http://127.0.0.1:8000/docs)
- [OpenAPI JSON](http://127.0.0.1:8000/openapi.json)

The default instance starts empty. Register a different college email in each tab. Sign-in uses a registered email, and the tab stores its student ID for the duration of the browser session. Data lives in memory and resets when the server restarts. A single worker gives every tab the same in-memory data.

Start with sample accounts and room history by setting the seed flag.

```bash
PEERROOMS_SEED=1 python -m uvicorn peerrooms.api.main:app --workers 1
```

Sign in as `aman@college.edu`, `riya@college.edu`, `kabir@college.edu`, `neha@college.edu`, `dev@college.edu`, or `isha@college.edu`. [The guided browser story](#guided-browser-story) uses these accounts.

## Show the API in Swagger

1. Expand **POST /api/students** to register, or call **POST /api/sessions** with a registered email. Copy the returned `id`.
2. Select **Authorize** and paste that ID into **Student identity**. Swagger adds the `X-Student-Id` header to the protected actions.
3. Use **Try it out** to list, create, join, and leave rooms or call **GET /api/discover/peers**. Use a second student's ID to see waitlist and permission behavior from their perspective.

Swagger UI 5.35.0 is served locally. Its Apache license and notice are in [the Swagger assets directory](peerrooms/api/swagger/).

## Guided browser story

1. With the seed enabled, open five tabs and sign in as Aman, Riya, Kabir, Dev, and Isha. As Aman, create a **Quick chat** with capacity **3**, tags **ai** and **careers**, and a discussion prompt.
2. Join as Riya and Kabir to fill the room. Join as Dev and Isha to see **Waitlisted #1** and **Waitlisted #2**. Post a message as Kabir and watch it appear in the other tabs.
3. Leave as Riya to promote Dev. Leave as Aman to promote Isha and transfer the host role to Kabir. Check the notification bells and the enabled message boxes.
4. As Aman, open **Discover peers** and switch the strategy. Weighted ranks Dev, Kabir, Riya, Isha with raw scores **0.41**, **0.355**, **0.34**, **0.20**. Jaccard ranks Dev, Riya, Kabir, Isha with scores **0.50**, **0.40**, **0.25**, **0.20**. The browser displays two decimal places.
5. Close the room as Kabir. Dev and Isha receive closure notifications. Use **Discover** to send a request and **Network** to accept it. Use **Profile** to edit interests, then revisit recommendations.
6. In Swagger, select the acting student's ID and repeat a browser action. For a permission test, try closing an active room while authorized as a seated member. Sign out of one browser tab to demonstrate that the other tabs retain their identities.

For the last-seat demonstration, create a room with one open seat and click **Join** from two student tabs at about the same time. One gets the seat and the other joins the queue.

## Verify the project

```bash
python -m pytest -q
python -m pytest --cov=peerrooms --cov-report=term-missing
```

The suite covers domain rules, repository contracts, event delivery, strategies, every HTTP operation, and ten simultaneous joins to one room. Browser verification covered four independent tabs and interactive Swagger, with external requests blocked for the Swagger check.

[Design, requirements, UML, and viva notes](docs/DESIGN.md)

The terminal simulation is scheduled for phase two.
