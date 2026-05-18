# AI URL Shortner

AI URL Shortner is a production-style URL shortener and link intelligence platform built with FastAPI, PostgreSQL, SQLAlchemy, Alembic, and a modern browser UI. It started as a clean URL shortener and evolved into a fuller product with analytics, AI enrichment, user accounts, optional guest usage, email verification, Google sign-in, and deployment-ready infrastructure.

The project is intentionally structured to teach backend architecture step by step while still producing a real, usable application. It is not just a tutorial toy or a single-file demo. The codebase separates routes, services, schemas, models, database access, AI orchestration, and frontend pages so each layer has a clear responsibility.

## What This Project Does

At its core, the app takes a long URL and turns it into a short one.

Example:

```text
https://very-long-url.com/article/123
```

becomes:

```text
https://urls.rf.gd/abc123x
```

When someone opens the short link, the app looks up the original destination in the database and issues a permanent redirect while also recording click data.

Around that core flow, the app adds:

- AI-generated summaries and tags for links
- click tracking and traffic analytics
- owner-only URL management
- guest creation without login
- optional accounts
- email verification
- Google OAuth sign-in
- production-style frontend pages
- deployment support for Render and Docker
- CI setup

## Current Status

This repository already includes:

- working URL shortening
- permanent redirects
- click event tracking
- user-owned URLs
- guest usage for anonymous shortening
- analytics overviews and per-link analytics
- daily analytics series for charting
- AI URL summarization and tagging
- persisted AI insight history
- branded QR code generation
- email/password auth with verification
- Google sign-in
- frontend UI for auth, create, analytics, dashboard, and link details
- Docker and Render deployment configuration
- Alembic migrations
- GitHub Actions CI

## Feature Overview

### URL Shortening

- Create short links from long URLs
- Use auto-generated 7-character Base62-style codes
- Support custom aliases
- Validate and reject reserved aliases
- Prevent duplicate alias collisions
- Rate limit creation to reduce abuse

### Redirects and Tracking

- `301 Moved Permanently` redirects for short links
- Track every redirect as a click event
- Capture:
  - referrer
  - user agent
  - IP address
  - timestamp
- Support both `/{short_code}` and legacy `/r/{short_code}` redirect paths

### Analytics

- total clicks per link
- recent click list
- top referrers
- device breakdown
- daily click series
- owner analytics overview
- time-window and timezone-aware reporting
- search, pagination, and filtering for owned URLs

### AI Features

- fetch page text before summarizing
- AI summary and tag generation for links
- fallback extractive summary if Gemini is unavailable
- AI insight persistence per URL
- link detail pages with AI context
- safe URL fetching with localhost blocking for AI fetches
- YouTube-friendly content extraction using oEmbed

### QR Branding

- generate branded QR codes for short links
- serve QR assets as downloadable SVG
- support multiple visual themes
- support glow, soft, poster, and minimal effects
- allow custom label text on the QR asset
- keep QR generation backend-owned so the asset points to the real short URL

### Authentication and Accounts

- optional email/password account creation
- email verification
- resend verification email flow
- Google sign-in/sign-up
- JWT authentication
- guest mode for quick usage without sign-in
- owner-only analytics and delete permissions

### Frontend

- dedicated auth page
- create page
- analytics page
- dashboard page
- URL details page
- branded QR studio on each URL detail page
- shared UI helpers and styles
- responsive dark theme
- production-style drawer interaction for auth

### Infrastructure

- PostgreSQL database
- async SQLAlchemy access
- Alembic migrations
- Dockerfile
- docker-compose
- Render deployment config
- Makefile automation
- GitHub Actions CI

## Architecture Overview

The app uses a layered structure:

```text
HTTP request
  -> route handler
  -> service function
  -> database query / AI fetch
  -> response schema
  -> JSON or redirect
```

### Why this structure exists

This separation keeps the app maintainable as it grows:

- routes handle HTTP concerns
- services handle business logic
- schemas define request and response shapes
- models define the database tables
- `db/database.py` handles session and engine setup
- `core/config.py` handles environment-driven configuration
- `web/` contains the browser-facing app

## Request Lifecycle

### Shorten URL flow

1. A user submits a long URL.
2. The request hits `POST /urls`.
3. The route checks rate limits.
4. The service creates a short code or custom alias.
5. The URL is stored in PostgreSQL.
6. The service tries AI enrichment.
7. The API returns the short URL, AI summary, tags, and click count fields.

### Redirect flow

1. A visitor opens `/{short_code}`.
2. The app looks up the short URL in the database.
3. A click event is recorded.
4. The visitor is redirected to the original URL with `301`.

### Analytics flow

1. The frontend asks for a URL or dashboard analytics endpoint.
2. The route verifies ownership when needed.
3. The service aggregates click events.
4. The API returns counts, charts, referrers, device breakdown, and trends.

### AI flow

1. The app fetches the destination page content.
2. The AI service cleans and extracts useful text.
3. Gemini is used when configured and available.
4. If Gemini fails or is unavailable, the app falls back to extractive summarization.
5. The summary and tags are stored as an `AIInsight`.

## Repository Structure

```text
ai-url-shortener/
├── app/
│   ├── core/              # config, security, rate limiting
│   ├── db/                # database engine/session setup
│   ├── models/            # SQLAlchemy models
│   ├── routes/            # FastAPI routes
│   ├── schemas/           # Pydantic request/response schemas
│   ├── services/          # business logic and AI logic
│   ├── web/               # browser UI pages, JS, CSS
│   └── main.py            # app entrypoint
├── alembic/               # migrations and Alembic env
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── render.yaml
├── AUTH_SETUP.md
├── DEPLOY_RENDER.md
└── README.md
```

## Data Model

### `users`

Stores user accounts.

Fields include:

- `id`
- `email`
- `password_hash`
- `is_verified`
- `verified_at`
- `verification_sent_at`
- `google_sub`
- `created_at`

### `shortened_urls`

Stores every shortened link.

Fields include:

- `id`
- `user_id`
- `original_url`
- `short_code`
- `created_at`

### `click_events`

Stores every tracked redirect.

Fields include:

- `id`
- `url_id`
- `referrer`
- `user_agent`
- `ip_address`
- `created_at`

### `ai_insights`

Stores AI summaries and tags.

Fields include:

- `id`
- `user_id`
- `url_id`
- `original_url`
- `summary`
- `tags`
- `created_at`

## API Endpoints

### Health and app

- `GET /` -> redirects to the auth page
- `GET /health` -> health check
- `GET /favicon.ico` -> empty response

### URL endpoints

- `POST /urls` -> create a short URL
- `GET /urls/mine` -> list URLs owned by the signed-in user
- `GET /urls/analytics/overview` -> user analytics overview
- `GET /urls/{short_code}/details` -> link detail page data
- `GET /urls/{short_code}/qr.svg` -> branded QR SVG for the short link
- `DELETE /urls/{short_code}` -> delete a user-owned link
- `GET /urls/{short_code}` -> permanent redirect + tracking
- `GET /urls/r/{short_code}` -> legacy redirect path
- `GET /urls/{short_code}/analytics` -> link analytics overview
- `GET /urls/{short_code}/analytics/daily` -> daily series for charts

### Auth endpoints

- `GET /auth/status` -> tells the frontend which auth options are enabled
- `POST /auth/register` -> create account
- `POST /auth/login` -> email/password login
- `GET /auth/me` -> current user
- `POST /auth/verify` -> verify email token
- `GET /auth/verify-email` -> email link handler
- `POST /auth/verify/resend` -> resend verification email
- `GET /auth/google/login` -> Google OAuth start
- `GET /auth/google/callback` -> Google OAuth callback

### AI endpoints

- `POST /ai/summarize` -> summarize a URL and extract tags

## Frontend Pages

The app serves a browser UI from `app/web/`.

- `auth.html` and `auth.js`
  - login, register, guest access, Google sign-in, resend verification
- `index.html`
  - main landing/workspace page after sign-in or guest entry
- `create.html` and `create.js`
  - create a short link
- `dashboard.js`
  - user dashboard data handling
- `analytics.html` and `analytics.js`
  - analytics overview and charting
- `url-details.html` and `url-details.js`
  - per-link analytics, AI insight view, and branded QR studio
- `styles.css`
  - complete visual system
- `common.js`
  - shared UI helpers, API helpers, token storage, toasts

## How Short Code Generation Works

If the user does not provide a custom alias:

- the app generates a random 7-character string
- the alphabet is Base62-like: letters and digits
- it retries up to 10 times to avoid collisions

If the user provides a custom alias:

- the alias is normalized
- length is checked
- allowed characters are enforced
- reserved aliases are blocked
- duplicates are rejected

## Analytics Notes

The analytics layer is built to support:

- total clicks
- recent clicks
- top referrers
- device distribution
- daily click trends
- time-zone-aware charts
- owner dashboard summaries

These analytics are available both:

- per link
- at the user overview level

## AI Notes

The AI layer is intentionally practical rather than experimental.

### Primary path

- Gemini is the primary AI provider when configured
- the primary model is `gemini-2.5-flash`
- the app validates the configured model against the API key's available models

### Fallback path

If Gemini is unavailable or fails:

- the app falls back to a local extractive summarizer
- it still returns a summary and tags
- the app does not fail URL creation just because AI enrichment failed

### URL fetching safety

The AI fetch layer:

- only allows `http` and `https`
- blocks localhost and loopback hosts
- refuses non-HTML content
- handles YouTube specially using oEmbed

## QR Branding Notes

The QR branding layer generates SVG assets directly from the app. This matters because the QR code should always point to the current public short URL and should not depend on an external QR generator service.

The QR endpoint is:

```text
GET /urls/{short_code}/qr.svg
```

It supports query options:

```text
theme=ember|lime|violet|mono
effect=glow|soft|poster|minimal
label=<optional display label>
```

Example:

```text
/urls/demo123/qr.svg?theme=ember&effect=glow&label=Launch%20Campaign
```

The frontend exposes this through the URL details page. Users can preview the QR code, switch themes, switch effects, edit the visible label, download the SVG, or copy the QR asset link.

## Authentication Notes

The auth system supports:

- email/password registration
- email verification
- resend verification
- Google OAuth
- JWT session tokens
- optional guest browsing

Email/password accounts are created unverified and cannot log in until verified.

Google sign-in accounts are marked verified automatically after Google confirms a verified email address.

## Environment Variables

The app reads configuration from environment variables and `.env` locally.

### Required or strongly recommended

```env
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>/<db>?sslmode=require
JWT_SECRET_KEY=<strong-secret>
PUBLIC_BASE_URL=https://urls.rf.gd
DEBUG=false
```

### JWT

```env
JWT_ACCESS_TOKEN_EXP_MINUTES=60
EMAIL_VERIFICATION_TOKEN_EXP_HOURS=24
```

### Google OAuth

```env
GOOGLE_CLIENT_ID=<google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<google-oauth-client-secret>
```

### Mail

```env
MAIL_FROM=<verified-sender-email>
MAIL_FROM_NAME=AI URL Shortner
MAIL_SERVER=smtp.resend.com
MAIL_PORT=587
MAIL_USERNAME=resend
MAIL_PASSWORD=<resend-api-key>
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
```

### AI

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=<gemini-api-key>
GEMINI_PRIMARY_MODEL=gemini-2.5-flash
AI_REQUEST_TIMEOUT_SECONDS=20
```

## Local Setup

### Prerequisites

- Python 3.10 or 3.11
- PostgreSQL or Docker
- a virtual environment
- optional: Google Cloud OAuth credentials
- optional: Resend SMTP credentials
- optional: Gemini API key

### 1. Clone the repo

```bash
git clone https://github.com/vais-hnav/ai-url-shortner.git
cd ai-url-shortener
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -e .
```

### 4. Create `.env`

Start from `.env.example` and fill your local values.

### 5. Run PostgreSQL

If you use Docker:

```bash
docker compose up -d postgres
```

### 6. Run migrations

```bash
alembic upgrade head
```

### 7. Start the app

```bash
uvicorn app.main:app --reload
```

### 8. Open the app

- Auth page: `http://127.0.0.1:8000/web/auth.html`
- Main page: `http://127.0.0.1:8000/web/index.html`
- API docs: `http://127.0.0.1:8000/docs`

## Docker Setup

### Start the stack

```bash
docker compose up --build
```

### Stop the stack

```bash
docker compose down
```

### Health check

```bash
curl http://127.0.0.1:8000/health
```

## Makefile

The repository includes a Makefile to reduce repeated commands.

Common targets include:

- `make setup`
- `make run`
- `make migrate-head`
- `make compose-up`
- `make compose-down`
- `make bootstrap`

## Deployment

### Render

The project is configured for Render with `render.yaml`.

It includes:

- Docker runtime
- health check path
- generated JWT secret
- production public base URL
- production environment variable configuration

The production app is intended to run with:

- `DEBUG=false`
- `PUBLIC_BASE_URL=https://urls.rf.gd`
- a real PostgreSQL database
- real Google OAuth credentials
- a verified sender for email verification
- a Gemini API key for AI enrichment

### Domain notes

The short link generator uses `PUBLIC_BASE_URL` to build the public short URL.

That means the domain you deploy on becomes the base of every generated link.

Example:

```text
PUBLIC_BASE_URL=https://urls.rf.gd
```

Short codes become:

```text
https://urls.rf.gd/abc123x
```

## Security and Production Notes

- do not commit real secrets to the repo
- keep production secrets in Render environment variables
- use a verified email-sending domain
- rotate keys if they were exposed in chat or logs
- rate limiting is in-memory right now and should be moved to Redis for multi-instance scaling
- AI fetches block localhost and loopback targets to reduce SSRF risk
- auth pages use security headers from the FastAPI app middleware

## Project Milestones Completed

### Milestone 1

- core short link engine
- auto-generated short codes
- custom aliases
- permanent redirects
- click tracking

### Milestone 2

- rate limiting
- alias hardening
- reserved alias protection
- duplicate detection
- analytics polish

### Milestone 3

- database-backed analytics
- owner-specific URL lists
- per-link analytics
- daily click series
- traffic overview

### Milestone 4

- production-style frontend
- multi-page UI
- auth screen redesign
- dashboard and analytics pages
- per-link details pages
- branded QR studio
- improved UX and styling

### Milestone 5

- deployment hardening
- Docker support
- Render support
- GitHub Actions CI
- environment and startup automation

### Authentication and Account Milestone

- email/password registration
- email verification
- verification resend flow
- Google OAuth login/signup
- guest mode

### AI Milestone

- URL summarization
- tag generation
- AI insight persistence
- Gemini integration with fallback summarization

### QR Branding Milestone

- backend-generated QR SVG assets
- per-link QR preview
- theme and effect controls
- SVG download support
- copyable QR asset URLs

## Work Done So Far

The project has already gone through these major implementation steps:

- set up the FastAPI application entrypoint
- designed the database layer
- introduced SQLAlchemy models for URLs, clicks, users, and AI insights
- wired Alembic migrations
- built URL creation and redirect logic
- added click analytics aggregation
- added AI summarization over fetched page content
- added user accounts with optional guest access
- added authentication with JWT
- added email verification and Google sign-in
- built a full frontend experience
- added a branded QR studio for short links
- added Docker and Render deployment support
- added a Makefile and CI workflow
- refined the auth drawer interaction on the frontend

## Notes for New Contributors

If you are opening the project fresh:

1. Read `app/main.py` to understand request flow.
2. Read `app/core/config.py` to understand configuration.
3. Read `app/routes/url_routes.py` to see the main product logic.
4. Read `app/services/url_service.py` and `app/services/ai_service.py` to understand business logic.
5. Read `app/routes/auth_routes.py` and `app/services/auth_service.py` for account handling.
6. Open the frontend files in `app/web/` to see the UI and browser-side orchestration.

## Future Roadmap

Planned next steps include:

- moving rate limiting to Redis
- background jobs for AI enrichment
- stronger AI alias generation
- spam/phishing detection
- richer AI analytics insights
- smarter routing by behavior or location
- PNG export and richer QR campaign templates
- natural-language analytics search
- stronger tests around API and frontend behavior
- improved admin and team collaboration features

## Acknowledgments

This project was built as a learning-focused, production-shaped backend and frontend system, with AI used as a product layer rather than as model training infrastructure. The goal is to understand the full stack intentionally: database, request lifecycle, auth, analytics, AI orchestration, deployment, and frontend UX.
