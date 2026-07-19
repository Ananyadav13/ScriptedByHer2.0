# Open-Source Attribution

Every third-party library, framework, and tool used, per the submission checklist.
Format: Name — Version — License — Role — Source.

Each entry describes what the library actually does **in this codebase**. Transitive
dependencies are listed separately and marked as such: they are pinned for reproducible
builds but are not imported by our code.

## Backend (Python)

| Name | Version | License | Role in build | Source |
|---|---|---|---|---|
| FastAPI | 0.115.6 | MIT | Web framework — REST routes + the SSE trace endpoint | https://github.com/fastapi/fastapi |
| Uvicorn | 0.34.0 | BSD-3-Clause | ASGI server | https://github.com/encode/uvicorn |
| SQLAlchemy | 2.0.36 | MIT | ORM / SQLite access (`app/models.py`) | https://github.com/sqlalchemy/sqlalchemy |
| Pydantic | 2.13.4 | MIT | Request/response DTOs and the agents' structured outputs (`Verdict`, `ClusterResult`, `FixDraft`, `FingerprintRead`) | https://github.com/pydantic/pydantic |
| pydantic-settings | 2.7.1 | MIT | Env/config loading (`app/config.py`) | https://github.com/pydantic/pydantic-settings |
| google-genai | 2.11.0 | Apache-2.0 | Gemini SDK — Agent 1's function-calling loop, the vision reads, Agent 2's clustering | https://github.com/googleapis/python-genai |
| python-dotenv | 1.0.1 | BSD-3-Clause | `.env` loading behind pydantic-settings | https://github.com/theskumar/python-dotenv |
| opencv-python-headless | 4.11.0.86 | Apache-2.0 | Keyframe extraction + JPEG resizing in `app/agents/vision.py` | https://github.com/opencv/opencv-python |
| pytest | 8.3.4 | MIT | Test suite (120 tests) | https://github.com/pytest-dev/pytest |

### Transitive (pinned for reproducibility, not imported by our code)

| Name | Version | License | Pulled in by | Source |
|---|---|---|---|---|
| NumPy | 2.2.1 | BSD-3-Clause | opencv-python-headless (OpenCV returns `ndarray` frames) | https://github.com/numpy/numpy |
| httpx | 0.28.1 | BSD-3-Clause | google-genai; also backs Starlette's `TestClient` in the suite | https://github.com/encode/httpx |

## Frontend (Node)

| Name | Version | License | Role in build | Source |
|---|---|---|---|---|
| Next.js | 16.2.10 | MIT | React framework (App Router, SSR, standalone build output) | https://github.com/vercel/next.js |
| React | 19.2.4 | MIT | UI library | https://github.com/facebook/react |
| React DOM | 19.2.4 | MIT | DOM renderer | https://github.com/facebook/react |
| Tailwind CSS | 4.x | MIT | Styling (via `@tailwindcss/postcss`) | https://github.com/tailwindlabs/tailwindcss |
| TypeScript | 5.x | Apache-2.0 | Types | https://github.com/microsoft/TypeScript |
| ESLint | 9.x | MIT | Linting (`eslint-config-next`) | https://github.com/eslint/eslint |

No third-party component library is used — every component in
`frontend/src/components/` is hand-written for this project.

## Models

- **Gemini (Google)** — `gemini-3-flash-preview` — used at runtime for Agent 1's
  tool-calling loop and structured verdict, the quality-attribute vision reads, and
  Agent 2's review clustering and fix drafting. Commercial API, not open-source;
  listed here for transparency.
