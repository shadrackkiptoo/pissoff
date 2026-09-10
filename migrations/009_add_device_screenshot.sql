alter table public.devices
add column if not exists screenshot_base64 text not null default '';

alter table public.devices
add column if not exists screenshot_time bigint;