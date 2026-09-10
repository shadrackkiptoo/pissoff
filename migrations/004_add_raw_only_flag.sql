begin;

alter table public.messages
add column if not exists raw_only boolean not null default false;

create index if not exists messages_raw_only_idx
on public.messages (raw_only, time desc);

commit;