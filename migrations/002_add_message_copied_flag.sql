begin;

alter table public.messages
add column if not exists is_copied boolean not null default false;

create index if not exists messages_copied_idx
on public.messages (is_copied)
where is_copied = true;

commit;
