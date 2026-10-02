create table users(
  id integer primary key,
  email text not null unique,
  name text not null,
  password_hash text not null,
  role text not null check(role in ('client','operator','admin')),
  active integer not null default 1
);
create table episodes(
  episode_id text primary key,
  robot_id text not null,
  task_name text not null,
  recorded_at text not null,           -- ISO 8601, naive UTC
  duration_seconds integer not null check(duration_seconds > 0),
  operator_name text,
  quality text not null check(quality in ('good','usable','bad'))
);
create index ix_ep_rec  on episodes(recorded_at, robot_id);
create index ix_ep_task on episodes(task_name, quality);
create table requests(
  id integer primary key,
  client_id integer not null references users(id),
  task_name text not null,
  episodes_requested integer not null check(episodes_requested > 0),
  deadline text not null,
  notes text not null default '',
  status text not null check(status in ('submitted','in_progress','delivered','accepted','rejected')),
  created_at text not null
);
create index ix_req_client on requests(client_id);
create table status_history(
  id integer primary key,
  request_id integer not null references requests(id),
  from_status text,
  to_status text not null,
  user_id integer not null references users(id),
  at text not null
);
-- PK on episode_id = "an episode is assigned to at most one request", enforced by the DB
create table assignments(
  episode_id text primary key references episodes(episode_id),
  request_id integer not null references requests(id)
);
create index ix_asg_req on assignments(request_id);
