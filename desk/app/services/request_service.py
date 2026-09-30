from datetime import datetime, timezone

from ..errors import DomainError
from ..models.domain import STAFF, TRANSITIONS


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _log(c, rid, frm, to, uid):
    c.execute("insert into status_history(request_id,from_status,to_status,user_id,at) values(?,?,?,?,?)",
              (rid, frm, to, uid, _now()))


def get_request(c, u, rid):
    r = c.execute("select * from requests where id=?", (rid,)).fetchone()
    if not r or (u["role"] == "client" and r["client_id"] != u["id"]):
        raise DomainError(404, "no such request")  # 404, not 403: don't leak existence
    return r


def create(c, u, b):
    cur = c.execute(
        "insert into requests(client_id,task_name,episodes_requested,deadline,notes,status,created_at)"
        " values(?,?,?,?,?,'submitted',?)",
        (u["id"], " ".join(b.task_name.lower().split()), b.episodes_requested, b.deadline.isoformat(), b.notes, _now()))
    _log(c, cur.lastrowid, None, "submitted", u["id"])
    c.commit()
    return {"id": cur.lastrowid, "status": "submitted"}


def list_for(c, u):
    base = ("select r.*, (select count(*) from assignments a where a.request_id=r.id) as assigned from requests r ")
    if u["role"] == "client":
        rows = c.execute(base + "where r.client_id=? order by r.id desc", (u["id"],))
    else:
        rows = c.execute(base + "order by r.id desc")
    return [dict(r) for r in rows]


def detail(c, u, rid):
    r = dict(get_request(c, u, rid))
    r["episodes"] = [x[0] for x in c.execute("select episode_id from assignments where request_id=?", (rid,))]
    r["history"] = [dict(x) for x in c.execute(
        "select from_status,to_status,user_id,at from status_history where request_id=? order by id", (rid,))]
    return r


def change_status(c, u, rid, new):
    r = get_request(c, u, rid)
    owner = TRANSITIONS.get((r["status"], new))
    if not owner:
        raise DomainError(409, f"invalid transition {r['status']} -> {new}")
    if u["role"] not in (("client",) if owner == "client" else STAFF):
        raise DomainError(403, "your role cannot perform this transition")
    if new == "delivered":
        n = c.execute("select count(*) from assignments where request_id=?", (rid,)).fetchone()[0]
        if n < r["episodes_requested"]:
            raise DomainError(409, f"only {n}/{r['episodes_requested']} episodes assigned")
    # compare-and-swap: two concurrent changes can't both win
    if not c.execute("update requests set status=? where id=? and status=?", (new, rid, r["status"])).rowcount:
        raise DomainError(409, "status changed concurrently")
    _log(c, rid, r["status"], new, u["id"])
    c.commit()
    return {"status": new}
