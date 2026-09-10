create table if not exists public.screenshots (
    id bigint generated always as identity primary key,
    device_id text not null,
    captured_at bigint not null,
    storage_path text not null unique,
    created_at timestamptz not null default now()
);

create index if not exists screenshots_device_time_idx
on public.screenshots (device_id, captured_at desc);

insert into storage.buckets (id, name, public)
values ('screenshots', 'screenshots', false)
on conflict (id) do update set public = false;

alter table public.messages
drop column if exists screenshot_base64;

alter table public.devices
drop column if exists screenshot_base64;

alter table public.devices
drop column if exists screenshot_time;