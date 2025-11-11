# Architecture

This document explains the high-level architecture of the AI Code Review Assistant and links to the main implementation files.

Overview
- Frontend: React + Chakra UI single-page app. Entry: [`code-review-frontend/src/main.jsx`](code-review-frontend/src/main.jsx), UI orchestration: [`code-review-frontend/src/App.jsx`](code-review-frontend/src/App.jsx).
- Backend: FastAPI service. Entry: [`code-review-backend/app/main.py`](code-review-backend/app/main.py).
- Integrations: GitHub REST API client in [`code-review-backend/app/services/github_client.py`](code-review-backend/app/services/github_client.py). LLM integration in [`code-review-backend/app/services/llm_service.py`](code-review-backend/app/services/llm_service.py).
- PR publishing: [`code-review-backend/app/services/pr_publisher.py`](code-review-backend/app/services/pr_publisher.py).
- RAG & chunking helpers: [`code-review-backend/app/services/rag_service.py`](code-review-backend/app/services/rag_service.py).

Component responsibilities
- Frontend
  - Authentication flow triggers GitHub OAuth via [`/api/auth/github/login`](code-review-backend/app/api/auth.py).
  - Repository listing uses [`getRepos`](code-review-frontend/src/services/api.js).
  - File browsing and selection handled by [`code-review-frontend/src/FileBrowser.jsx`](code-review-frontend/src/FileBrowser.jsx).
  - Review flow controls are in [`code-review-frontend/src/components/ReviewPanel.jsx`](code-review-frontend/src/components/ReviewPanel.jsx).
- Backend
  - Auth and session handling: [`code-review-backend/app/api/auth.py`](code-review-backend/app/api/auth.py).
  - JWT creation/verification: [`code-review-backend/app/core/jwt_auth.py`](code-review-backend/app/core/jwt_auth.py).
  - Repo endpoints: [`code-review-backend/app/api/repositories.py`](code-review-backend/app/api/repositories.py).
  - Review orchestration and LLM calls: [`code-review-backend/app/api/reviews.py`](code-review-backend/app/api/reviews.py) → calls [`review_code_chunk`](code-review-backend/app/services/llm_service.py).
  - PR publishing: [`PRPublisher`](code-review-backend/app/services/pr_publisher.py).

Dataflow (summary)
1. User signs in via GitHub OAuth → [`/api/auth/github/callback`](code-review-backend/app/api/auth.py)
2. Frontend calls [`/api/repos/list`](code-review-backend/app/api/repositories.py) via [`getRepos`](code-review-frontend/src/services/api.js)
3. User selects files → frontend posts selected file refs to [`/api/reviews/start`](code-review-backend/app/api/reviews.py)
4. Backend fetches raw file text with [`GitHubClient.get_file_content`](code-review-backend/app/services/github_client.py), chunks via [`rag_service`](code-review-backend/app/services/rag_service.py), calls LLM via [`llm_service.review_code_chunk`](code-review-backend/app/services/llm_service.py), returns structured review
5. Optionally publish aggregated suggestions using [`PRPublisher.publish_review_to_pr`](code-review-backend/app/services/pr_publisher.py)

Useful links
- Frontend app: [code-review-frontend/src/App.jsx](code-review-frontend/src/App.jsx)
- Backend entry: [code-review-backend/app/main.py](code-review-backend/app/main.py)