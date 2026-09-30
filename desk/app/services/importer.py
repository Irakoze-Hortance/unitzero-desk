import csv, io
from datetime import datetime, timezone

ROBOTS = {"arm-01", "arm-02", "arm-03", "mobile-01", "humanoid-01"}
QUALITY = {"good", "usable", "bad"}
COLS = ["episode_id", "robot_id", "task_name", "recorded_at", "duration_seconds", "operator_name", "quality"]
# Ambiguous dd/mm vs mm/dd: we assume day-first.
FMTS = ["%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M", "%Y/%m/%d %H:%M:%S", "%d/%m/%Y"]


def parse_date(s):
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo:
            d = d.astimezone(timezone.utc).replace(tzinfo=None)
        return d.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        pass
    for f in FMTS:
        try:
            return datetime.strptime(s, f).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass
    raise ValueError


def import_csv(c, text):
    """Idempotent: existing episode_ids are never touched (first write wins)."""
    rd = csv.DictReader(io.StringIO(text))
    rd.fieldnames = [h.strip().lower() for h in (rd.fieldnames or [])]
    if set(COLS) - set(rd.fieldnames):
        raise ValueError(f"CSV must have columns: {COLS}")
    rep = {"rows": 0, "imported": 0, "skipped": {}, "details": []}
    seen = set()

    def skip(line, reason, eid=None):
        rep["skipped"][reason] = rep["skipped"].get(reason, 0) + 1
        if len(rep["details"]) < 200:
            rep["details"].append({"line": line, "episode_id": eid, "reason": reason})

    for row in rd:
        line = rd.line_num
        rep["rows"] += 1
        if None in row or any(v is None for v in row.values()):
            skip(line, "malformed row (wrong number of columns)")
            continue
        r = {k: v.strip() for k, v in row.items()}
        eid = r["episode_id"].upper()
        missing = next((k for k in COLS if k != "operator_name" and not r[k]), None)
        if missing:
            skip(line, f"missing {missing}", eid or None)
            continue
        robot, quality = r["robot_id"].lower(), r["quality"].lower()
        task = " ".join(r["task_name"].lower().split())
        if robot not in ROBOTS:
            skip(line, f"unknown robot '{r['robot_id']}'", eid); continue
        if quality not in QUALITY:
            skip(line, f"invalid quality '{r['quality']}'", eid); continue
        try:
            when = parse_date(r["recorded_at"])
        except ValueError:
            skip(line, f"invalid recorded_at '{r['recorded_at']}'", eid); continue
        try:
            dur = int(float(r["duration_seconds"]))
            assert dur > 0
        except (ValueError, AssertionError, OverflowError):
            skip(line, f"invalid duration '{r['duration_seconds']}'", eid); continue
        if eid in seen:
            skip(line, "duplicate within file", eid); continue
        seen.add(eid)
        op = " ".join(r["operator_name"].split()).title() or None
        cur = c.execute(
            "insert or ignore into episodes(episode_id,robot_id,task_name,recorded_at,duration_seconds,operator_name,quality)"
            " values(?,?,?,?,?,?,?)", (eid, robot, task, when, dur, op, quality))
        if cur.rowcount:
            rep["imported"] += 1
        else:
            skip(line, "already in database", eid)
    c.commit()
    return rep
