begin;

alter table public.devices
add column if not exists joined_at bigint;

alter table public.devices
alter column joined_at set default (extract(epoch from now()) * 1000)::bigint;

update public.devices d
set joined_at = coalesce(
    (select min(m.time) from public.messages m where m.device_id = d.device_id),
    d.started_at,
    (extract(epoch from now()) * 1000)::bigint
)
where d.joined_at is null;

alter table public.devices
alter column joined_at set not null;

create index if not exists devices_joined_at_idx
on public.devices (joined_at asc);

commit;
