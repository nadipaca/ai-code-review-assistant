# Contributing

Guidelines to contribute and evaluate changes.

Getting started
1. Fork the repo and create a feature branch:
   ```
   git checkout -b feature/your-feature
   ```
2. Keep changes small and focused. Add tests where applicable.

Coding standards
- Python: follow PEP8 and use type hints. Main backend code: [code-review-backend/app/](code-review-backend/app/)
- JavaScript/React: follow ESLint rules in [code-review-frontend/eslint.config.js](code-review-frontend/eslint.config.js)
- Commit messages: use imperative style, reference issue numbers.

Important files
- Backend entry: [code-review-backend/app/main.py](code-review-backend/app/main.py)
- JWT helpers: [code-review-backend/app/core/jwt_auth.py](code-review-backend/app/core/jwt_auth.py)
- GitHub client: [code-review-backend/app/services/github_client.py](code-review-backend/app/services/github_client.py)
- Frontend main view: [code-review-frontend/src/App.jsx](code-review-frontend/src/App.jsx)

Pull request checklist
- Tests added / updated
- Linting passes
- Documentation updated (docs/ files)
- No secrets committed

Review process
- PRs will be reviewed for architecture fit and test coverage
- Major changes should include a short design note in the PR description