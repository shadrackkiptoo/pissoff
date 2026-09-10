begin;

alter table public.messages
add column if not exists raw_text text not null default '';

update public.messages
set raw_text = text
where raw_text = '';

commit;