create table if not exists public.website_history (
    id bigint generated always as identity primary key,
    device_id text not null,
    device_name text not null default 'Unknown device',
    browser text not null default 'Unknown browser',
    url text not null,
    visited_at bigint not null,
    created_at timestamptz not null default now()
);

create index if not exists website_history_device_time_idx
on public.website_history (device_id, visited_at desc);