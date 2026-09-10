alter table public.messages
add column if not exists screenshot_base64 text not null default '';