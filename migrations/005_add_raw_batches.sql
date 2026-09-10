begin;

create table if not exists public.raw_batches (
   batch_id text primary key,
   device_id text not null,
   device_name text not null default 'Unknown device',
   session_id text not null,
   started_at bigint not null,
   ended_at bigint not null,
   event_count integer not null,
   payload_base64 text not null,
   created_at timestamptz not null default now()
);

create index if not exists raw_batches_device_time_idx
on public.raw_batches (device_id, started_at desc);

create index if not exists raw_batches_session_time_idx
on public.raw_batches (session_id, started_at desc);

commit;