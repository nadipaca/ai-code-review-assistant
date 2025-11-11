# API Reference

This document maps high-level frontend actions to backend endpoints and points to implementation files.

Authentication
- GET /api/auth/github/login — redirect to GitHub OAuth ([implementation](code-review-backend/app/api/auth.py))
- GET /api/auth/github/callback — OAuth callback and cookie set ([implementation](code-review-backend/app/api/auth.py))
- POST /api/auth/github/logout — clear session cookie ([implementation](code-review-backend/app/api/auth.py))

Profile
- GET /api/profile — returns minimal profile from JWT cookie ([implementation](code-review-backend/app/api/profile.py))

Repositories
- GET /api/repos/list — list user repositories (requires cookie JWT)  
  Called by frontend: [`getRepos`](code-review-frontend/src/services/api.js)  
  Backend implementation: [code-review-backend/app/api/repositories.py](code-review-backend/app/api/repositories.py)
- GET /api/repos/{owner}/{repo}/contents?path=... — list files in a repo path ([implementation](code-review-backend/app/api/repositories.py))

Reviews
- POST /api/reviews/start — start review for files (body: { files: [{ owner, repo, path }] })  
  Frontend call: [`startReview`](code-review-frontend/src/services/api.js)  
  Backend implementation: [code-review-backend/app/api/reviews.py](code-review-backend/app/api/reviews.py)
- POST /api/reviews/publish — publish suggestions to PR (body: owner, repo, pull_number, suggestions)  
  Frontend call: [`publishReviewToPR`](code-review-frontend/src/services/api.js)  
  Backend implementation: [code-review-backend/app/api/reviews.py](code-review-backend/app/api/reviews.py) and [code-review-backend/app/services/pr_publisher.py](code-review-backend/app/services/pr_publisher.py)

Protected Test
- GET /api/protected — bearer-JWT protected endpoint for diagnostics ([implementation](code-review-backend/app/api/protected.py))

Error handling
- Backend returns structured HTTP errors (401 for auth, 429 rate limit defined in [main.py](code-review-backend/app/main.py), 502 for upstream GitHub errors).
- Frontend `api.js` propagates status and message for UI handling.

Authentication flow (quick)
- Frontend redirects user to `GET /api/auth/github/login` → webhook callback sets HttpOnly cookie `access_token` and stores GitHub token in server session store (`sessions` in [auth.py](code-review-backend/app/api/auth.py)).