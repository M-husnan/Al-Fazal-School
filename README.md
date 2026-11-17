# Al-Fazal Higher Secondary School Management

Responsive staff portal for Al-Fazal Higher Secondary School, G.M Abad, Faisalabad. It uses Django REST Framework, PostgreSQL, JWT, Django Admin, Django Channels/WebSockets, and a responsive React/Vite frontend. Students are records managed by staff and do not have login accounts.

## Included

- Principal and teacher roles, JWT login, scoped teacher access, and Django Admin.
- Classes with one class incharge per teacher; student admissions, photos, profiles, archiving, fee history, quiz history, and attendance summary.
- Monthly fee generation, paid/pending/late state, receipt PDFs, class-wise pending fee posts and in-app teacher notifications.
- Quizzes, paper image/PDF uploads, marks, percentages, monthly class summaries, and PDF reports.
- Campus news, announcements, and events with image/file uploads.
- Staff direct, all-teacher, and class group chats, with text and file/image/PDF/voice messages, timestamps, seen state, online presence, and WebSocket updates.
- Principal and teacher dashboards, attendance, search, responsive mobile layout, and an Urdu RTL navigation switch.
- Optional S3-compatible media storage configuration for persistent production uploads.

## Local setup (Linux/macOS)

Requirements: Python 3.11 or 3.12, Node.js 20+, and Docker (for local PostgreSQL and Redis).

```bash
cd Al-Fazal-School-Management
docker compose up -d
cp .env.example .env
```

Edit `.env` and set a private `DJANGO_SECRET_KEY`. Then install and initialize the backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

In another terminal, install and start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The default `VITE_API_URL` is `http://127.0.0.1:8000/api/`. Keep `REDIS_URL=redis://localhost:6379/0` in `.env` when running the ASGI server; the built-in Django development server is suitable only for local use. To try WebSocket chat locally, start Daphne instead of `runserver`:

```bash
cd backend
. .venv/bin/activate
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Create classes in Django Admin (`/admin/`) and assign a teacher to each class. Use the Principal role or a Django superuser for initial setup. The principal can add teacher logins and admissions from the app. The school name/address are included in report PDFs.

## Render deployment

Deploy the `backend` directory as a Python web service and the `frontend` directory as a Static Site. Set these backend environment variables in Render:

> The included Render Blueprint uses Free plans as a trial configuration. Render Free PostgreSQL expires 30 days after creation and has no backups. Upgrade to a persistent database plan and configure backups before entering real student/fee records; also configure persistent media storage below.

- `DJANGO_SECRET_KEY`: generate a long random value; do not commit it.
- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS`: your backend hostname, such as `your-api.onrender.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS`: `https://your-api.onrender.com,https://your-frontend.onrender.com`
- `CORS_ALLOWED_ORIGINS`: `https://your-frontend.onrender.com`
- `DATABASE_URL`: Render PostgreSQL **Internal Database URL** when the services share a region.
- `REDIS_URL`: Render Key Value internal URL for WebSockets.

Backend build command:

```bash
pip install -r requirements.txt && python manage.py migrate --noinput && python manage.py collectstatic --noinput
```

Backend start command:

```bash
daphne -b 0.0.0.0 -p $PORT config.asgi:application
```

Frontend build command: `npm install && npm run build`; publish directory: `dist`. Set `VITE_API_URL` to `https://your-api.onrender.com/api/` before building the frontend. Configure an HTTPS/WSS origin in production.

### Daily automation

The management command `python manage.py school_daily_jobs` is idempotent. Schedule it once every day in a Render Cron Job (for example, 00:00 UTC = 05:00 Pakistan time). It creates the current month's fees on the first day, fee pending posts/notifications on or after the fifth, and the previous month's quiz posts. If the scheduler is not configured, these jobs will not run automatically. Use the Render cron service's environment to set the same `DATABASE_URL` and required Django environment variables.

### Uploaded files

Render's local filesystem is ephemeral. For student photos, chat attachments, quiz papers, and campus post media to survive deploys/restarts, configure an S3-compatible bucket and set `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL` (if applicable), `AWS_S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY`. Set `AWS_MEDIA_URL` only if your provider has a public custom media base URL. Keep private buckets private and use signed URLs. Without this setup, media is stored on the service filesystem and can be lost when Render replaces the instance.

## Key routes

- `/admin/` — Django Admin
- `/api/auth/token/` and `/api/auth/token/refresh/` — JWT
- `/api/auth/me/`, `/api/dashboard/`
- `/api/classes/`, `/api/teachers/`, `/api/students/`, `/api/fees/`, `/api/quizzes/`, `/api/attendance/`, `/api/posts/`, `/api/chat-rooms/`, `/api/messages/`, `/api/notifications/`
- `/api/reports/fees.pdf`, `/api/reports/quiz.pdf`, `/api/reports/class.pdf`
- `/ws/chat/<room_id>/?token=<short-lived-access-token>` — authenticated staff WebSocket chat; use WSS in production.

## Useful management commands

```bash
python manage.py createsuperuser
python manage.py generate_monthly_fees
python manage.py generate_fee_pending_reports
python manage.py generate_monthly_quiz_reports
python manage.py school_daily_jobs
```

Commands accept optional `--month YYYY-MM` where applicable. Existing fees and automatic posts are not duplicated.
