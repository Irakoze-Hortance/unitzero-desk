import pytest
from fastapi.testclient import TestClient

CSV = """episode_id,robot_id,task_name,recorded_at,duration_seconds,operator_name,quality
EP-1,arm-01,Pick Cup,2025-09-01T08:00:00,30,aline,good
EP-2,arm-01,pick cup,2025-09-01 09:00,31,Eric,usable
EP-3,arm-01,pick cup,2025-09-01T10:00:00,32,Eric,bad
EP-1,arm-01,pick cup,2025-09-01T08:00:00,30,Aline,good
EP-4,robot-x,pick cup,2025-09-01T08:00:00,30,Aline,good
EP-5,arm-01,pick cup,not-a-date,30,Aline,good
EP-6,arm-01,pick cup,2025-09-01T08:00:00,,Aline,good
EP-7,arm-01,pick cup
"""


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    from app import db, security
    from app.main import app
    db.migrate()
    c = db.conn()
    for email, role in [("client@t", "client"), ("other@t", "client"), ("op@t", "operator"), ("admin@t", "admin")]:
        c.execute("insert into users(email,name,password_hash,role) values(?,?,?,?)",
                  (email, email, security.hash_pw("password1"), role))
    c.commit(); c.close()
    return TestClient(app)


def auth(api, email):
    t = api.post("/login", json={"email": email, "password": "password1"}).json()["token"]
    return {"Authorization": f"Bearer {t}"}


def mk_request(api, hdr, n=2):
    r = api.post("/requests", headers=hdr, json={"task_name": "Pick Cup", "episodes_requested": n, "deadline": "2026-12-01"})
    return r.json()["id"]


def load(api, op):
    return api.post("/import", headers={**op, "Content-Type": "text/csv"}, content=CSV).json()


def status(api, hdr, rid, s):
    return api.post(f"/requests/{rid}/status", headers=hdr, json={"status": s}).status_code


def test_authorization(api):
    assert api.get("/requests").status_code == 401
    a, b, op = auth(api, "client@t"), auth(api, "other@t"), auth(api, "op@t")
    rid = mk_request(api, a)
    assert api.get(f"/requests/{rid}", headers=b).status_code == 404       # other client's request
    assert api.get("/requests", headers=b).json() == []
    assert api.get("/requests", headers=op).json()[0]["id"] == rid           # staff see all
    assert api.post("/import", headers=a, content=CSV).status_code == 403    # client can't import
    assert api.get("/episodes", headers=a).status_code == 403
    assert status(api, a, rid, "in_progress") == 403                         # client can't do operator steps
    assert api.post("/requests", headers=op, json={"task_name": "x", "episodes_requested": 1, "deadline": "2026-12-01"}).status_code == 403
    assert api.post("/users", headers=op, json={"email": "n@t", "name": "n", "password": "password1", "role": "client"}).status_code == 403


def test_deactivated_user_token_stops_working(api):
    admin, a = auth(api, "admin@t"), auth(api, "client@t")
    assert api.get("/requests", headers=a).status_code == 200
    assert api.patch("/users/1", headers=admin, json={"active": False}).status_code == 200  # client@t is id 1
    assert api.get("/requests", headers=a).status_code == 401


def test_transitions_history_and_rework(api):
    a, op = auth(api, "client@t"), auth(api, "op@t")
    load(api, op)
    rid = mk_request(api, a, n=2)
    assert status(api, op, rid, "delivered") == 409           # can't skip in_progress
    assert status(api, op, rid, "in_progress") == 200
    assert status(api, op, rid, "delivered") == 409           # 0/2 episodes assigned
    assert api.post(f"/requests/{rid}/episodes", headers=op, json={"episode_ids": ["EP-1", "EP-2"]}).status_code == 200
    assert status(api, op, rid, "delivered") == 200
    assert status(api, op, rid, "accepted") == 403            # operator can't accept
    assert status(api, a, rid, "rejected") == 200
    assert status(api, op, rid, "in_progress") == 200         # rework
    assert status(api, op, rid, "delivered") == 200
    assert status(api, a, rid, "accepted") == 200
    assert status(api, op, rid, "in_progress") == 409         # accepted is terminal
    h = api.get(f"/requests/{rid}", headers=a).json()["history"]
    assert [x["to_status"] for x in h] == ["submitted", "in_progress", "delivered", "rejected", "in_progress", "delivered", "accepted"]
    assert all(x["user_id"] and x["at"] for x in h)


def test_assignment_rules(api):
    a, op = auth(api, "client@t"), auth(api, "op@t")
    load(api, op)
    r1, r2 = mk_request(api, a), mk_request(api, a)
    put = lambda rid, ids, h=op: api.post(f"/requests/{rid}/episodes", headers=h, json={"episode_ids": ids}).status_code
    assert put(r1, ["EP-3"]) == 422                 # bad quality
    assert put(r1, ["EP-999"]) == 404
    assert put(r1, ["EP-1"], a) == 403              # client can't assign
    assert put(r1, ["EP-1"]) == 200
    assert put(r2, ["EP-1"]) == 409                 # already on another request
    assert put(r2, ["EP-2", "EP-1"]) == 409         # batch is all-or-nothing...
    assert put(r2, ["EP-2"]) == 200                 # ...so EP-2 was not consumed


def test_import_idempotent_and_reports(api):
    op = auth(api, "op@t")
    first = load(api, op)
    assert first["imported"] == 3 and sum(first["skipped"].values()) == 5
    second = load(api, op)
    assert second["imported"] == 0 and second["skipped"]["already in database"] == 3
    assert len(api.get("/episodes", headers=op).json()) == 3


def test_analytics(api):
    op = auth(api, "op@t")
    load(api, op)
    r = api.get("/analytics?from=2025-09-01&to=2025-09-01", headers=op).json()
    assert r["episodes_per_day_per_robot"] == [{"day": "2025-09-01", "robot_id": "arm-01", "episodes": 3}]
    assert r["top_tasks_by_good_episodes"] == [{"task_name": "pick cup", "good_episodes": 1}]
    assert r["requests_by_status"]["submitted"] == 0


def test_ui_is_served(api):
    r = api.get("/")
    assert r.status_code == 200 and "Dataset Request Desk" in r.text
    assert api.get("/styles.css").status_code == 200 and api.get("/app.js").status_code == 200
    assert api.get("/health").json() == {"status": "ok"}   # API routes still win over the mount
