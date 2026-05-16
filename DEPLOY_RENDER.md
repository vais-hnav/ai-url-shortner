# Render Deployment Notes

This project is prepared for a hosted deployment on Render with the custom domain:

`https://urls.rf.gd`

## Why this file exists

`render.yaml` lets Render create the web service with the correct runtime, startup command,
dedicated `/health` check, and production environment defaults.

## What Render will do

- Build the app from the repo Dockerfile
- Run Alembic migrations before starting the app
- Start Uvicorn on Render's public port
- Generate a JWT secret for the hosted service
- Build short links using `https://urls.rf.gd`
- Serve the web app at `/` and keep health checks on `/health`

## Environment variables you still need to set in Render

These are intentionally marked `sync: false` in `render.yaml`, which means you set them in the Render dashboard:

- `DATABASE_URL`
- `GEMINI_API_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `MAIL_FROM`
- `MAIL_SERVER`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`

These also matter for auth flows:

- `EMAIL_VERIFICATION_TOKEN_EXP_HOURS`
- `MAIL_PORT`
- `MAIL_STARTTLS`
- `MAIL_SSL_TLS`

## Recommended database choice

For the simplest free setup, use **Neon Postgres**.

Why:

- It gives you a plain Postgres connection string, which fits this app directly.
- It is simpler than Supabase for this project because you only need a database, not a full backend platform.
- It avoids the 30-day expiry limitation of Free Render Postgres.

If Neon gives you a connection string that starts with:

`postgresql://`

change only the scheme for this app to:

`postgresql+asyncpg://`

Keep the rest of the connection string the same, including any SSL parameters.

## Recommended deploy flow

1. Push this repository to GitHub.
2. In Render, create a new Blueprint and point it to this repo.
3. Let Render create the web service from `render.yaml`.
4. In the service settings, set:
   - `DATABASE_URL`
   - `GEMINI_API_KEY`
5. Deploy once and confirm the service opens on its Render URL.
6. Add the custom domain `urls.rf.gd` in the Render dashboard.
7. Update your DNS records at your domain provider using the values Render shows.
8. Verify the domain in Render.

## Auth setup notes

For email verification:

- Use an SMTP-capable provider such as Resend SMTP, SendGrid SMTP, Mailgun SMTP, or Gmail SMTP for testing.
- Set `MAIL_FROM` to the sender address users should see.
- Verification links are generated from `PUBLIC_BASE_URL`, so this must match your real domain.

For Google sign in:

- Create an OAuth client in Google Cloud Console.
- Add your local callback:
  `http://127.0.0.1:8000/auth/google/callback`
- Add your production callback:
  `https://urls.rf.gd/auth/google/callback`
- Add the same production domain to the authorized JavaScript origins if Google asks for it.

## Important production note

If you use a free hosted Postgres provider or a free Render database, check its retention and expiry rules before treating it as production data storage.
