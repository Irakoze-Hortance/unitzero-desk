from ..errors import DomainError
from ..models.domain import STATUSES


def report(c, from_, to):
    if from_ > to:
        raise DomainError(422, "'from' must be <= 'to'")
    p = {"a": from_.isoformat(), "b": to.isoformat()}
    ep_range = "recorded_at >= :a and recorded_at < date(:b,'+1 day')"
    req_range = "created_at >= :a and created_at < date(:b,'+1 day')"
    per_day = c.execute(f"select substr(recorded_at,1,10) as day, robot_id, count(*) as episodes from episodes "
                        f"where {ep_range} group by 1,2 order by 1,2", p)
    by_status = dict(c.execute(f"select status, count(*) from requests where {req_range} group by status", p).fetchall())
    # median in SQL via window functions (Postgres: percentile_cont(0.5) within group)
    median = c.execute(f"""
        with d as (select (julianday(min(h.at)) - julianday(r.created_at)) * 86400 as secs
                   from requests r join status_history h on h.request_id=r.id and h.to_status='delivered'
                   where r.{req_range} group by r.id),
             o as (select secs, row_number() over (order by secs) rn, count(*) over () n from d)
        select avg(secs) from o where rn in ((n+1)/2, (n+2)/2)""", p).fetchone()[0]
    top = c.execute(f"select task_name, count(*) as good_episodes from episodes where quality='good' and {ep_range} "
                    f"group by task_name order by 2 desc, 1 limit 5", p)
    return {"episodes_per_day_per_robot": [dict(r) for r in per_day],
            "requests_by_status": {s: by_status.get(s, 0) for s in STATUSES},
            "median_seconds_submitted_to_delivered": median,
            "top_tasks_by_good_episodes": [dict(r) for r in top]}
