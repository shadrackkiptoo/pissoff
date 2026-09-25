begin;

alter table public.devices
    add column if not exists local_ip text not null default '';

commit;