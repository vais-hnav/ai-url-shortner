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

## Important production note

If you use a free hosted Postgres provider or a free Render database, check its retention and expiry rules before treating it as production data storage.
