"use strict";

const byId = (id) => document.getElementById(id);
const storageKey = "peerrooms.studentId";
const state = {
  student: null, session: 0, page: null, roomId: null, pageRead: 0, inboxRead: 0,
  pageTimer: null, inboxTimer: null, filters: {},
};
const roomTypes = { QUICK_CHAT: "Quick chat", DISCUSSION: "Discussion", PANEL: "Panel" };
const roomDefaults = { QUICK_CHAT: 4, DISCUSSION: 6, PANEL: 12 };
const timeFormat = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });
const scoreFormat = new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const revisions = new WeakMap();
let toastTimer;

class RequestError extends Error {}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(label, action, id, style = "outline compact", name) {
  const node = element("button", "button " + style, label);
  node.type = "button";
  Object.assign(node.dataset, { action, id });
  if (name) node.dataset.name = name;
  return node;
}

function toast(message, isError = false) {
  const box = byId("toast");
  box.textContent = message;
  box.classList.toggle("error", isError);
  box.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { box.hidden = true; }, 4400);
}

async function api(method, path, body) {
  const session = state.session;
  const actor = sessionStorage.getItem(storageKey);
  const headers = { Accept: "application/json" };
  if (actor) headers["X-Student-Id"] = actor;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let result;
  try {
    result = await fetch(path, { method, headers, body: JSON.stringify(body) });
  } catch {
    if (session === state.session) toast("Could not reach PeerRooms. Try again in a moment.", true);
    throw new RequestError();
  }
  const payload = result.status === 204 ? null : await result.json().catch(() => null);
  if (session !== state.session) throw new RequestError();
  if (!result.ok) {
    if (result.status === 401 || (actor && method === "GET" && payload?.error === "StudentNotFoundError")) {
      signOut();
    }
    const detail = payload?.detail;
    toast(payload?.message || (Array.isArray(detail) ? detail[0]?.msg : detail)
      || "Request failed (" + result.status + ").", true);
    throw new RequestError();
  }
  return payload;
}

async function run(task, control) {
  if (control?.getAttribute("aria-busy") === "true") return;
  control?.setAttribute("aria-busy", "true");
  try {
    await task();
  } catch (error) {
    if (!(error instanceof RequestError)) throw error;
  } finally {
    control?.removeAttribute("aria-busy");
  }
}

const chipEditors = new Map();
for (const field of document.querySelectorAll("[data-chips]")) {
  const input = field.querySelector("input");
  const editor = { input, list: field.querySelector(".chips"), values: [] };
  chipEditors.set(field.dataset.chips, editor);
  input.addEventListener("keydown", (event) => {
    if (event.isComposing || !["Enter", ","].includes(event.key) || !input.value.trim()) return;
    event.preventDefault();
    commitChips(field.dataset.chips);
  });
}

function setChips(key, values) {
  const editor = chipEditors.get(key);
  editor.values = [...new Set(values.map((value) => value.trim().toLowerCase()).filter(Boolean))];
  editor.input.value = "";
  editor.list.replaceChildren(...editor.values.map((value) => {
    const chip = element("button", "chip", value + " ×");
    chip.type = "button";
    chip.setAttribute("aria-label", "Remove " + value);
    chip.addEventListener("click", () => {
      const draft = editor.input.value;
      setChips(key, editor.values.filter((item) => item !== value));
      editor.input.value = draft;
      editor.input.focus();
    });
    return chip;
  }));
}

function commitChips(key) {
  const editor = chipEditors.get(key);
  setChips(key, [...editor.values, ...editor.input.value.split(",")]);
  return editor.values;
}

function showAuth(mode) {
  byId("auth-screen").hidden = false;
  for (const tab of document.querySelectorAll("[data-auth-mode]")) {
    tab.setAttribute("aria-pressed", String(tab.dataset.authMode === mode));
  }
  byId("sign-in-form").hidden = mode !== "sign-in";
  byId("register-form").hidden = mode !== "register";
}

function signOut() {
  state.session += 1;
  state.student = state.page = state.roomId = null;
  clearInterval(state.pageTimer);
  clearInterval(state.inboxTimer);
  state.inboxRead += 1;
  sessionStorage.removeItem(storageKey);
  byId("app-screen").hidden = true;
  byId("account").hidden = true;
  byId("toast").hidden = true;
  setInboxOpen(false);
  showAuth("sign-in");
}

function signIn(student) {
  state.session += 1;
  state.student = student;
  sessionStorage.setItem(storageKey, student.id);
  byId("account-name").textContent = student.name;
  byId("account").hidden = byId("app-screen").hidden = false;
  byId("auth-screen").hidden = true;
  byId("unread-count").hidden = true;
  for (const id of [
    "inbox-list", "room-list", "recommended-list", "peer-list",
    "incoming-list", "outgoing-list", "connection-list",
  ]) {
    byId(id).replaceChildren();
    revisions.delete(byId(id));
  }
  byId("room-filters").reset();
  byId("create-room-form").reset();
  setChips("room", []);
  setCreateOpen(false);
  updateCapacityHint();
  byId("strategy").value = "weighted";
  state.filters = {};
  renderProfile(student);
  navigate("rooms");
  clearInterval(state.inboxTimer);
  run(refreshNotifications);
  state.inboxTimer = setInterval(() => run(refreshNotifications), 3000);
}

function navigate(page, roomId = null) {
  clearInterval(state.pageTimer);
  state.page = page;
  state.roomId = roomId;
  state.pageRead += 1;
  for (const section of document.querySelectorAll(".page")) section.hidden = section.id !== page;
  for (const nav of document.querySelectorAll(".nav-link")) {
    const current = nav.dataset.page === (page === "room-detail" ? "rooms" : page);
    if (current) nav.setAttribute("aria-current", "page");
    else nav.removeAttribute("aria-current");
  }
  if (page === "room-detail") {
    byId("room-body").hidden = true;
    byId("room-loading").hidden = false;
    byId("message-form").reset();
    revisions.delete(byId("message-list"));
  }
  const interval = { rooms: 3000, "room-detail": 2000, network: 3000 }[page];
  run(refreshPage);
  if (interval) state.pageTimer = setInterval(() => run(refreshPage), interval);
}

async function refreshPage() {
  const page = state.page;
  const roomId = state.roomId;
  const request = ++state.pageRead;
  const current = () => state.pageRead === request && state.page === page;
  switch (page) {
    case "rooms": {
      const params = new URLSearchParams(state.filters);
      const [rooms, recommended] = await Promise.all([
        api("GET", "/api/rooms?" + params), api("GET", "/api/rooms/recommended"),
      ]);
      if (current()) {
        renderList("room-list", rooms, roomCard, "No rooms match these filters.");
        renderList("recommended-list", recommended, roomCard, "No rooms to recommend yet.");
      }
      break;
    }
    case "room-detail": {
      const room = await api("GET", roomPath(roomId));
      if (current()) renderRoom(room);
      break;
    }
    case "discover": {
      const peers = await api("GET", "/api/discover/peers?strategy=" + byId("strategy").value);
      if (current()) renderList("peer-list", peers, peerCard, "No matching peers yet.");
      break;
    }
    case "network": {
      const [requests, connections] = await Promise.all([
        api("GET", "/api/connections/requests"), api("GET", "/api/connections"),
      ]);
      if (current()) renderNetwork(requests, connections);
      break;
    }
    case "profile":
      renderProfile(state.student);
      break;
  }
}

function renderList(id, items, drawItem, emptyText) {
  const container = byId(id);
  const revision = JSON.stringify(items);
  if (revisions.get(container) === revision) return;
  revisions.set(container, revision);
  const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 38;
  container.replaceChildren(...(items.length ? items.map(drawItem) : [element("p", "empty", emptyText)]));
  if (id === "message-list" && nearBottom) container.scrollTop = container.scrollHeight;
}

function chips(values) {
  return values.map((value) => element("span", "chip", value));
}

function badge(label) {
  return element("span", "badge " + label.toLowerCase(), label);
}

function roomMeta(room) {
  const meta = element("div", "room-meta");
  meta.append(
    badge(room.status),
    element("span", "seats", room.seated_count + "/" + room.capacity + " seats"),
  );
  return meta;
}

function roomCard(room) {
  const card = element("article", "surface room-card");
  const tags = element("div", "chips");
  tags.append(...chips(room.tags));
  const actions = element("div", "actions");
  const needsSeat = !room.viewer_role && !room.viewer_waitlist_position && room.status !== "CLOSED";
  if (needsSeat) actions.append(button("Join", "join", room.id, "primary compact"));
  actions.append(button("View room", "view-room", room.id));
  card.append(roomMeta(room), element("h3", "", room.topic), element("p", "muted", roomTypes[room.room_type]), tags);
  if (room.viewer_waitlist_position) {
    card.append(element("p", "muted", "Waitlisted #" + room.viewer_waitlist_position));
  } else if (room.viewer_role) {
    card.append(element("p", "muted", room.viewer_role === "HOST" ? "You’re the host" : "You have a seat"));
  }
  card.append(actions);
  return card;
}

function renderRoom(room) {
  byId("room-loading").hidden = true;
  byId("room-body").hidden = false;
  byId("room-title").textContent = room.topic;
  byId("room-prompt").textContent = room.prompt;
  byId("room-meta").replaceChildren(roomMeta(room));
  byId("room-tags-view").replaceChildren(...chips(room.tags));

  const seated = Boolean(room.viewer_role);
  const waitlisted = Boolean(room.viewer_waitlist_position);
  const host = room.viewer_role === "HOST";
  const closed = room.status === "CLOSED";
  let position = "";
  const controls = [];
  if (closed) {
    position = "This room is closed.";
  } else if (seated || waitlisted) {
    position = seated ? (host ? "You’re hosting this room." : "You have a seat.")
      : "Waitlisted #" + room.viewer_waitlist_position;
    controls.push({ label: seated ? "Leave room" : "Leave waitlist", action: "leave" });
    if (host) controls.push({ label: "Close room", action: "close", style: "danger compact" });
  } else {
    controls.push({ label: "Join room", action: "join", style: "primary compact" });
  }
  byId("room-position").textContent = position;
  renderList("room-actions", controls.map((control) => ({ ...control, id: room.id })),
    (control) => button(control.label, control.action, control.id, control.style), "");
  byId("room-actions").hidden = !controls.length;

  renderList("member-list", room.members.map((member) => ({ ...member, canRemove: host && member.role !== "HOST" })),
    (member) => {
      const row = element("div", "list-row");
      const who = element("div", "who");
      who.append(element("strong", "", member.name));
      if (member.role === "HOST") who.append(badge("HOST"));
      row.append(who);
      if (member.canRemove) row.append(button("Remove", "remove", member.student_id, "danger compact"));
      return row;
    }, "No seated members.");
  renderList("waitlist", room.waitlist,
    (item) => element("p", "list-row", "Position #" + item.position + (item.is_you ? " · You" : "")),
    "No students are waiting.");

  const textarea = byId("message-content");
  textarea.disabled = byId("message-form").querySelector("button").disabled = !seated;
  byId("message-help").textContent = seated ? "Up to 1,000 characters."
    : (closed ? "This discussion has ended." : "Take a seat to send messages.");
  renderList("message-list", room.messages, messageRow, "No messages yet.");
}

function messageRow(message) {
  const line = element("article", "message");
  const byline = element("div", "byline");
  byline.append(element("strong", "", message.sender_name), time(message.sent_at));
  line.append(byline, element("p", "", message.content));
  return line;
}

function time(timestamp) {
  const node = element("time", "", timeFormat.format(new Date(timestamp)));
  node.dateTime = timestamp;
  return node;
}

function peerCard(peer) {
  const { student, score, common_interests: matches } = peer;
  const card = element("article", "surface peer-card");
  const tags = element("div", "chips");
  tags.append(...chips(matches));
  const actions = element("div", "actions");
  actions.append(button("Connect", "connect", student.id, "primary compact"),
    button("Block", "block", student.id, "quiet compact", student.name));
  card.append(
    element("h3", "", student.name),
    element("p", "muted", student.department + " · Year " + student.year),
    element("p", "peer-score", scoreFormat.format(score) + " similarity"),
    tags, actions,
  );
  return card;
}

function renderNetwork(requests, connections) {
  renderList("incoming-list", requests.incoming, (item) => requestRow(item, true), "No incoming requests.");
  renderList("outgoing-list", requests.outgoing, (item) => requestRow(item, false), "No sent requests.");
  renderList("connection-list", connections, (student) => {
    const row = element("div", "list-row");
    row.append(element("strong", "", student.name), element("span", "muted", student.department),
      button("Block", "block", student.id, "quiet compact", student.name));
    return row;
  }, "You have no connections yet.");
}

function requestRow(item, incoming) {
  const row = element("article", "list-row");
  const name = incoming ? item.sender_name : item.receiver_name;
  const other = incoming ? item.sender_id : item.receiver_id;
  const actions = element("div", "actions");
  if (incoming) {
    actions.append(button("Accept", "accept", item.id, "primary compact"), button("Reject", "reject", item.id));
  } else {
    actions.append(button("Cancel request", "cancel", item.id));
  }
  actions.append(button("Block", "block", other, "quiet compact", name));
  row.append(element("strong", "", name), actions);
  return row;
}

function renderProfile(student) {
  byId("profile-name").textContent = student.name;
  byId("profile-meta").textContent = [student.email, student.department, "Year " + student.year].join(" · ");
  setChips("profile", student.interests);
}

async function refreshNotifications() {
  const request = ++state.inboxRead;
  const items = await api("GET", "/api/notifications");
  if (request !== state.inboxRead) return;
  const count = items.filter((item) => !item.is_read).length;
  byId("unread-count").textContent = String(count);
  byId("unread-count").hidden = count === 0;
  byId("notification-button").setAttribute("aria-label",
    count ? "Notifications (" + count + " unread)" : "Notifications");
  renderList("inbox-list", items, (item) => {
    const row = element("article", item.is_read ? "inbox-item" : "inbox-item unread");
    row.append(element("p", "", item.text));
    if (!item.is_read) row.append(button("Mark read", "read", item.id));
    row.append(time(item.created_at));
    return row;
  }, "You have no notifications yet.");
}

function setInboxOpen(open) {
  byId("notification-panel").hidden = !open;
  byId("notification-button").setAttribute("aria-expanded", String(open));
}

function setCreateOpen(open) {
  byId("create-room-panel").hidden = !open;
  byId("create-room-toggle").setAttribute("aria-expanded", String(open));
  if (open) byId("room-topic").focus();
}

function updateCapacityHint() {
  const type = byId("room-type");
  const option = type.selectedOptions[0];
  const capacity = roomDefaults[type.value];
  byId("room-capacity").placeholder = String(capacity);
  byId("capacity-hint").textContent = option.textContent + " allows " + option.dataset.range + " seats. Default " + capacity + ".";
}

const roomPath = (id) => "/api/rooms/" + encodeURIComponent(id);

async function performAction(control) {
  const { action, id, name } = control.dataset;
  const room = state.roomId;
  const path = roomPath(id);
  switch (action) {
    case "view-room":
      navigate("room-detail", id);
      return;
    case "join": {
      const outcome = await api("POST", path + "/join");
      toast(outcome.result === "JOINED" ? "You have a seat." : "Waitlisted #" + outcome.position);
      navigate("room-detail", id);
      return;
    }
    case "leave":
      await api("POST", path + "/leave");
      toast("You left the room.");
      break;
    case "close":
      if (!window.confirm("Close this room and end the discussion?")) return;
      await api("POST", path + "/close");
      toast("Room closed.");
      break;
    case "remove":
      await api("DELETE", roomPath(room) + "/members/" + encodeURIComponent(id));
      toast("Member removed.");
      break;
    case "connect":
      await api("POST", "/api/connections/requests", { receiver_id: id });
      toast("Connection request sent.");
      break;
    case "accept":
    case "reject":
    case "cancel":
      await api("POST", "/api/connections/requests/" + encodeURIComponent(id) + "/" + action);
      toast({ accept: "Connection accepted.", reject: "Request rejected.", cancel: "Request cancelled." }[action]);
      break;
    case "block":
      if (!window.confirm("Block " + name + "?")) return;
      await api("POST", "/api/students/me/blocks/" + encodeURIComponent(id));
      toast(name + " was blocked.");
      break;
    case "read":
      await api("POST", "/api/notifications/" + encodeURIComponent(id) + "/read");
      await refreshNotifications();
      return;
  }
  await refreshPage();
}

function onSubmit(id, handler) {
  byId(id).addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    run(() => handler(values, form), form);
  });
}

onSubmit("sign-in-form", async ({ email }, form) => {
  signIn(await api("POST", "/api/sessions", { email }));
  form.reset();
});
onSubmit("register-form", async (values, form) => {
  values.year = Number(values.year);
  values.interests = commitChips("register");
  signIn(await api("POST", "/api/students", values));
  form.reset();
  setChips("register", []);
});
onSubmit("create-room-form", async (values, form) => {
  values.capacity = values.capacity ? Number(values.capacity) : null;
  values.tags = commitChips("room");
  const room = await api("POST", "/api/rooms", values);
  form.reset();
  setChips("room", []);
  setCreateOpen(false);
  updateCapacityHint();
  navigate("room-detail", room.id);
});
onSubmit("room-filters", async (values) => {
  state.filters = Object.fromEntries(Object.entries(values).filter(([, value]) => value.trim()));
  await refreshPage();
});
onSubmit("interest-form", async () => {
  state.student = await api("PUT", "/api/students/me/interests", { interests: commitChips("profile") });
  renderProfile(state.student);
  toast("Interests saved.");
});
onSubmit("message-form", async ({ content }, form) => {
  if (!content || byId("message-content").disabled) return;
  const room = state.roomId;
  await api("POST", roomPath(room) + "/messages", { content });
  if (state.roomId === room && byId("message-content").value === content) form.reset();
  await refreshPage();
});

byId("room-type").addEventListener("change", updateCapacityHint);
byId("strategy").addEventListener("change", () => run(refreshPage));
byId("sign-out").addEventListener("click", signOut);
byId("create-room-toggle").addEventListener("click", () => setCreateOpen(byId("create-room-panel").hidden));
byId("create-room-cancel").addEventListener("click", () => {
  setCreateOpen(false);
  byId("create-room-toggle").focus();
});
byId("notification-button").addEventListener("click", () => {
  const open = byId("notification-panel").hidden;
  setInboxOpen(open);
  if (open) run(refreshNotifications);
});
document.addEventListener("click", (event) => {
  if (!byId("account").contains(event.target)) setInboxOpen(false);
  const control = event.target.closest("button");
  if (!control) return;
  if (control.dataset.page) navigate(control.dataset.page);
  if (control.dataset.authMode) showAuth(control.dataset.authMode);
  if (control.dataset.action) run(() => performAction(control), control);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !byId("notification-panel").hidden) {
    setInboxOpen(false);
    byId("notification-button").focus();
  }
});

if (sessionStorage.getItem(storageKey)) {
  run(async () => {
    try { signIn(await api("GET", "/api/students/me")); }
    finally { if (!state.student) showAuth("sign-in"); }
  });
} else {
  showAuth("sign-in");
}
