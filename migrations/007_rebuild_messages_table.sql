begin;

do $$
begin
   if to_regclass('public.messages') is null then
      create table public.messages (
         id bigint primary key,
         text text not null,
         raw_text text not null default '',
         raw_only boolean not null default false,
         device_id text not null default 'unknown',
         device_name text not null default 'Unknown device',
         app_name text not null default 'Unknown app',
         source_url text not null default '',
         time bigint not null,
         is_pasted boolean not null default false,
         is_copied boolean not null default false,
         created_at timestamptz not null default now()
      );
   else
      alter table public.messages
         add column if not exists raw_text text not null default '',
         add column if not exists raw_only boolean not null default false,
         add column if not exists app_name text not null default 'Unknown app',
         add column if not exists source_url text not null default '',
         add column if not exists is_pasted boolean not null default false,
         add column if not exists is_copied boolean not null default false,
         add column if not exists created_at timestamptz not null default now();

      create table public.messages_rebuilt (
         id bigint primary key,
         text text not null,
         raw_text text not null default '',
         raw_only boolean not null default false,
         device_id text not null default 'unknown',
         device_name text not null default 'Unknown device',
         app_name text not null default 'Unknown app',
         source_url text not null default '',
         time bigint not null,
         is_pasted boolean not null default false,
         is_copied boolean not null default false,
         created_at timestamptz not null default now()
      );

      insert into public.messages_rebuilt (
         id, text, raw_text, raw_only, device_id, device_name, app_name,
         source_url, time, is_pasted, is_copied, created_at
      )
      select
         id,
         text,
         coalesce(nullif(raw_text, ''), text),
         false,
         coalesce(device_id, 'unknown'),
         coalesce(device_name, 'Unknown device'),
         coalesce(app_name, 'Unknown app'),
         coalesce(source_url, ''),
         time,
         coalesce(is_pasted, false),
         coalesce(is_copied, false),
         coalesce(created_at, now())
      from public.messages
      where coalesce(raw_only, false) = false;

      drop table public.messages;
      alter table public.messages_rebuilt rename to messages;
   end if;
end
$$;

create index if not exists messages_time_idx
on public.messages (time desc);

create index if not exists messages_source_url_idx
on public.messages (source_url)
where source_url <> '';

create index if not exists messages_copied_idx
on public.messages (is_copied)
where is_copied = true;

commit;
