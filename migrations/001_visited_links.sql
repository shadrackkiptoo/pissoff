begin;

create table if not exists public.visited_links (
    id bigint generated always as identity primary key,
    device_id text not null,
    device_name text not null default 'Unknown device',
    browser text not null default 'Unknown browser',
    url text not null,
    visited_at bigint not null,
    created_at timestamptz not null default now()
);

create unique index if not exists visited_links_unique_idx
    on public.visited_links (device_id, browser, url, visited_at);

create index if not exists visited_links_device_time_idx
    on public.visited_links (device_id, visited_at desc);

create index if not exists visited_links_url_idx
    on public.visited_links (url);

commit;
