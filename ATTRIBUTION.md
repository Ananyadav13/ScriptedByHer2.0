# Open-Source Attribution

Every third-party library, framework, and tool used, per the submission checklist.
Format: Name — Version — License — Role — Source.

## Backend (Python)

| Name | Version | License | Role in build | Source |
|---|---|---|---|---|
| FastAPI | 0.115.6 | MIT | Web framework / REST + SSE | https://github.com/fastapi/fastapi |
| Uvicorn | 0.34.0 | BSD-3-Clause | ASGI server | https://github.com/encode/uvicorn |
| SQLAlchemy | 2.0.36 | MIT | ORM / SQLite access | https://github.com/sqlalchemy/sqlalchemy |
| Pydantic | 2.10.4 | MIT | Schemas / structured outputs | https://github.com/pydantic/pydantic |
| pydantic-settings | 2.7.1 | MIT | Env/config loading | https://github.com/pydantic/pydantic-settings |
| google-genai | 2.11.0 | Apache-2.0 | Gemini API SDK (agent loop, vision, clustering) | https://github.com/googleapis/python-genai |
| python-dotenv | 1.0.1 | BSD-3-Clause | .env loading | https://github.com/theskumar/python-dotenv |
| Faker | 33.1.0 | MIT | Synthetic seed data | https://github.com/joke2k/faker |
| Pillow | 11.1.0 | MIT-CMU | Image handling (perceptual hash) | https://github.com/python-pillow/Pillow |
| ImageHash | 4.3.1 | BSD-2-Clause | Perceptual image-match check | https://github.com/JohannesBuchner/imagehash |
| NumPy | 2.2.1 | BSD-3-Clause | Review-burst statistics | https://github.com/numpy/numpy |
| httpx | 0.28.1 | BSD-3-Clause | HTTP client (transitive/tests) | https://github.com/encode/httpx |

_opencv-python-headless added in Phase 3 (video keyframe extraction) — will be recorded then._

## Frontend (Node)

| Name | Version | License | Role in build | Source |
|---|---|---|---|---|
| Next.js | 16.2.10 | MIT | React framework (App Router, SSR) | https://github.com/vercel/next.js |
| React | 19.x | MIT | UI library | https://github.com/facebook/react |
| Tailwind CSS | 4.x | MIT | Styling | https://github.com/tailwindlabs/tailwindcss |
| TypeScript | 5.x | Apache-2.0 | Types | https://github.com/microsoft/TypeScript |

_shadcn/ui components added in Phase 5 — will be recorded then._

## Models

- **Gemini (Google)** — `gemini-3-flash-preview` — used at runtime for the agent orchestration, vision review analysis, and review clustering. Commercial API, not open-source; listed for transparency.
