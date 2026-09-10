begin;

alter table public.messages
add column if not exists source_url text not null default '';

create index if not exists messages_source_url_idx
on public.messages (source_url) where source_url <> '';

commit;