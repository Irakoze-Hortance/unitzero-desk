import sqlite3

from ..errors import DomainError
from . import importer
from .request_service import get_request


def list_episodes(c, task_name, quality, unassigned, limit, offset):
    where, args = ["1=1"], []
    if task_name:
        where.append("e.task_name=?"); args.append(" ".join(task_name.lower().split()))
    if quality:
        where.append("e.quality=?"); args.append(quality)
    if unassigned:
        where.append("a.request_id is null")
    rows = c.execute(f"select e.*, a.request_id from episodes e left join assignments a using(episode_id) "
                     f"where {' and '.join(where)} order by e.episode_id limit ? offset ?", (*args, limit, offset))
    return [dict(r) for r in rows]


def assign(c, u, rid, episode_ids):
    r = get_request(c, u, rid)
    if r["status"] in ("delivered", "accepted"):
        raise DomainError(409, f"cannot assign episodes to a {r['status']} request")
    ids = list(dict.fromkeys(episode_ids))  # de-dupe, keep order
    for eid in ids:
        ep = c.execute("select quality from episodes where episode_id=?", (eid,)).fetchone()
        if not ep:
            raise DomainError(404, f"unknown episode {eid}")
        if ep["quality"] == "bad":
            raise DomainError(422, f"{eid} is 'bad' quality and cannot be assigned")
        try:
            c.execute("insert into assignments(episode_id,request_id) values(?,?)", (eid, rid))
        except sqlite3.IntegrityError:
            raise DomainError(409, f"{eid} is already assigned")
    c.commit()  # all-or-nothing: any raise above discards the whole batch
    return {"assigned": len(ids)}


def import_episodes(c, data: bytes):
    try:
        return importer.import_csv(c, data.decode("utf-8-sig", errors="replace"))
    except ValueError as e:
        raise DomainError(422, str(e))
