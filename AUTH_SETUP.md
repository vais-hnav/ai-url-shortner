# Auth Setup

This app supports:

- email/password signup with email verification
- Google sign in / sign up
- guest mode for users who do not want an account yet

## Local development

Use local values while developing auth flows:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_url_shortener
PUBLIC_BASE_URL=http://127.0.0.1:8000
DEBUG=true
JWT_SECRET_KEY=replace-with-a-random-local-secret
```

Start Postgres:

```bash
docker compose up -d postgres
```

Run migrations:

```bash
./venv/bin/alembic upgrade head
```

Start the app:

```bash
./venv/bin/uvicorn app.main:app --reload
```

If email delivery is not configured and `DEBUG=true`, the auth screen will show a debug verification link after signup or resend.

## Google OAuth

Set these environment variables:

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

Create a Google OAuth client of type `Web application` and add these redirect URIs:

- `http://127.0.0.1:8000/auth/google/callback`
- `https://urls.rf.gd/auth/google/callback`

## Email verification delivery

Set these environment variables:

```env
MAIL_FROM=
MAIL_FROM_NAME=AI URL Shortner
MAIL_SERVER=smtp.resend.com
MAIL_PORT=587
MAIL_USERNAME=resend
MAIL_PASSWORD=
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
```

Recommended provider:

- Resend SMTP

For production, set `PUBLIC_BASE_URL` to your live domain so verification links point to the deployed app.
