# 🤖 AI Code Review Assistant

> **Production-grade AI-powered code review platform with GitHub integration, RAG architecture, and real-time PR feedback**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.121%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/react-19.1-61dafb.svg)](https://reactjs.org/)
[![OpenAI](https://img.shields.io/badge/openai-GPT--4-412991.svg)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📋 Table of Contents
- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Demo](#-demo)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Security](#-security)
- [Performance](#-performance)
- [Contributing](#-contributing)
- [Roadmap](#-roadmap)
- [License](#-license)

## 🎯 Overview

**AI Code Review Assistant** is a full-stack enterprise application that automates code review processes using GPT-4, reducing manual review time by up to 70%. The platform integrates seamlessly with GitHub repositories, providing intelligent suggestions, security vulnerability detection, and automated PR feedback.

### 🎥 [Live Demo](https://your-demo-link.com) | 📖 [Documentation](docs/)

### Problem Statement
Manual code reviews are time-consuming, inconsistent, and often miss critical issues. Development teams need an intelligent, scalable solution that maintains code quality while accelerating the development cycle.

### Solution
An AI-powered assistant that analyzes code in real-time, provides actionable feedback, and integrates directly into existing GitHub workflows—reducing review bottlenecks and improving code quality metrics.

## ✨ Key Features

### 🔐 **Enterprise-Grade Authentication**
- OAuth 2.0 integration with GitHub
- JWT-based session management with HttpOnly cookies
- Secure token storage and automatic refresh
- Rate limiting and CORS protection

### 🧠 **Intelligent Code Analysis**
- **GPT-4 powered** code review with context-aware suggestions
- **RAG (Retrieval-Augmented Generation)** for enhanced accuracy
- Support for **Java** and **JavaScript** with extensible architecture
- Automatic code chunking for large files (handles files up to 200KB)
- Concurrent chunk processing for optimized performance

### 🔄 **Seamless GitHub Integration**
- Browse and select repositories directly from the UI
- Real-time file tree navigation with breadcrumb support
- Direct PR comment publishing with markdown formatting
- Automatic repository sync and webhook support (planned)

### 🎨 **Modern User Interface**
- Responsive React 19 frontend with Chakra UI
- Single-page application with smooth transitions
- Real-time loading states and error handling
- Pagination for large repository lists
- Export review results to text files

### 📊 **Production-Ready Backend**
- Asynchronous FastAPI for high concurrency
- Structured error handling and logging
- Request/response validation with Pydantic
- Rate limiting (30 requests/min per IP)
- Comprehensive API documentation (Swagger/OpenAPI)

## 🏗️ Architecture

For a detailed explanation of the system architecture, component responsibilities, and dataflow, see the [Architecture Documentation](docs/ARCHITECTURE.md).

**High-level overview:**

```
┌─────────────────┐      HTTPS/WSS     ┌──────────────────┐
│   React SPA     │◄────────────────────┤   FastAPI        │
│   (Frontend)    │                     │   (Backend)      │
└─────────────────┘                     └──────────────────┘
        │                                        │
        │                                        │
        ▼                                        ▼
┌─────────────────┐                     ┌──────────────────┐
│  Chakra UI      │                     │  GitHub API      │
│  Vite Dev       │                     │  OAuth 2.0       │
└─────────────────┘                     └──────────────────┘
                                                │
                                                ▼
                                        ┌──────────────────┐
                                        │  OpenAI GPT-4    │
                                        │  API             │
                                        └──────────────────┘
```

### Key Components
- **Frontend**: React 19 + Chakra UI ([App.jsx](code-review-frontend/src/App.jsx))
- **Backend**: FastAPI ([main.py](code-review-backend/app/main.py))
- **GitHub Integration**: [github_client.py](code-review-backend/app/services/github_client.py)
- **AI Review**: [llm_service.py](code-review-backend/app/services/llm_service.py)
- **PR Publishing**: [pr_publisher.py](code-review-backend/app/services/pr_publisher.py)

## 🛠️ Tech Stack

### **Frontend**
| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19.1.1 | UI Framework |
| **Chakra UI** | 2.10.9 | Component Library |
| **Vite** | 7.1.7 | Build Tool & Dev Server |
| **React Icons** | 5.5.0 | Icon Library |
| **Emotion** | 11.14 | CSS-in-JS |

### **Backend**
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.121.0 | REST API Framework |
| **Python** | 3.11+ | Programming Language |
| **OpenAI** | 1.0+ | GPT-4 Integration |
| **python-jose** | 3.3.0 | JWT Authentication |
| **httpx** | - | Async HTTP Client |
| **Pydantic** | 2.12.4 | Data Validation |
| **Uvicorn** | 0.38.0 | ASGI Server |

### **Infrastructure & DevOps**
- **Version Control:** Git & GitHub
- **Environment:** Docker (planned)
- **CI/CD:** GitHub Actions (planned)
- **Monitoring:** Logging with Python `logging` module

## 📸 Demo

### 1. **GitHub Authentication**
![Login Screen](docs/screenshots/login.png)
*Secure OAuth 2.0 login with GitHub*

### 2. **Repository Selection**
![Repository List](docs/screenshots/repo-list.png)
*Browse and search through your repositories*

### 3. **File Browser**
![File Browser](docs/screenshots/file-browser.png)
*Navigate repository structure and select files*

### 4. **AI Review Results**
![Review Results](docs/screenshots/review-results.png)
*Detailed AI-generated suggestions with code snippets*

### 5. **PR Integration**
![PR Comments](docs/screenshots/pr-comments.png)
*Publish review directly to GitHub Pull Requests*

## 🚀 Installation

For detailed installation and deployment instructions, see the [Deployment Guide](docs/DEPLOYMENT.md).

### Quick Start

### Prerequisites
- **Node.js** 18+ and npm/yarn
- **Python** 3.11+
- **GitHub OAuth App** ([Create one](https://github.com/settings/developers))
- **OpenAI API Key** ([Get one](https://platform.openai.com/api-keys))

### 1️⃣ Clone Repository
```bash
git clone https://github.com/yourusername/ai-code-review-assistant.git
cd ai-code-review-assistant
```

### 2️⃣ Backend Setup
```bash
cd code-review-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3️⃣ Frontend Setup
```bash
cd code-review-frontend

# Install dependencies
npm install
```

## ⚙️ Configuration

### Backend Environment Variables
Create `.env` in project root:
```env
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# JWT Configuration
JWT_SECRET=your_super_secret_jwt_key_change_in_production
JWT_EXPIRE_MINUTES=60

# Environment
ENV=development  # production for HTTPS cookies
```

### GitHub OAuth Setup
1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create **New OAuth App**
3. Set **Authorization callback URL:** `http://localhost:8000/api/auth/github/callback`
4. Copy **Client ID** and **Client Secret** to `.env`

For production deployment configuration, see [DEPLOYMENT.md](docs/DEPLOYMENT.md).

## 💻 Usage

### Start Backend
```bash
cd code-review-backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Backend runs at: **http://localhost:8000**

### Start Frontend
```bash
cd code-review-frontend
npm run dev
```
Frontend runs at: **http://localhost:5173**

### Workflow
1. **Navigate to** http://localhost:5173
2. **Click** "Sign in with GitHub"
3. **Authorize** the application
4. **Select** a repository from your list
5. **Browse** files and select `.java` or `.js` files
6. **Click** "Review Selected Files"
7. **View** AI-generated suggestions
8. **Export** results or **Publish** to PR

## 📚 API Documentation

For complete API documentation including all endpoints, request/response formats, and authentication flows, see [API.md](docs/API.md).

### Quick Reference

#### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/auth/github/login` | Initiate GitHub OAuth |
| `GET` | `/api/auth/github/callback` | OAuth callback handler |
| `POST` | `/api/auth/github/logout` | Clear session cookie |

#### Repository Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/repos/list` | List user repositories |
| `GET` | `/api/repos/{owner}/{repo}/contents` | Browse repo files |

#### Review Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/reviews/start` | Start code review |
| `POST` | `/api/reviews/publish` | Publish to PR |

**Interactive API Docs:** http://localhost:8000/docs (Swagger UI when running locally)

## 🔒 Security

### Implemented Security Measures
✅ **OAuth 2.0** with GitHub for secure authentication  
✅ **JWT tokens** stored in HttpOnly cookies (XSS protection)  
✅ **CORS** configured for specific frontend origin  
✅ **Rate limiting** (30 req/min per IP)  
✅ **Input validation** with Pydantic models  
✅ **Secrets** stored in environment variables  
✅ **HTTPS** enforced in production (env-based)  

### Security Best Practices
- Never commit `.env` files
- Rotate JWT secrets regularly
- Use HTTPS in production
- Implement CSRF protection for state-changing operations
- Add request signing for webhook events (planned)

For deployment security checklist, see [DEPLOYMENT.md](docs/DEPLOYMENT.md#security-checklist-before-production).

## ⚡ Performance

### Optimizations Implemented
- **Asynchronous I/O** with `asyncio` and `httpx`
- **Code chunking** to handle large files efficiently
- **Concurrent chunk processing** (up to 50 chunks/file)
- **Request rate limiting** to prevent API abuse
- **Lazy loading** in frontend with pagination
- **Memoization** for repeated API calls (planned)

### Performance Metrics
| Metric | Value |
|--------|-------|
| **Average review time** | 5-15s per file |
| **Max file size** | 200 KB |
| **Concurrent reviews** | 10+ files |
| **API rate limit** | 30 req/min |

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guidelines](docs/CONTRIBUTING.md) before submitting pull requests.

### Quick Start for Contributors
1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

### Development Guidelines
- Follow PEP 8 (Python) and ESLint rules (JavaScript)
- Write unit tests for new features
- Update documentation for API changes
- Add comments for complex logic

For detailed coding standards and PR checklist, see [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## 🗺️ Roadmap

### ✅ Completed
- [x] GitHub OAuth integration
- [x] Repository browsing
- [x] AI code review with GPT-4
- [x] PR comment publishing
- [x] Export review results
- [x] Rate limiting and security

### 🚧 In Progress
- [ ] TypeScript support
- [ ] Python file support
- [ ] Code snippet highlighting in results

### 📅 Planned Features
- [ ] **Multi-language support** (Python, Go, Rust, C++)
- [ ] **Webhook integration** for automatic PR reviews
- [ ] **Custom review rules** and templates
- [ ] **Team collaboration** features
- [ ] **Diff-based reviews** (only review changed lines)
- [ ] **Integration with CI/CD** pipelines
- [ ] **Analytics dashboard** (review metrics, time saved)
- [ ] **Self-hosted LLM support** (Llama, Mistral)
- [ ] **Docker containerization**
- [ ] **Unit test generation** from code review
- [ ] **Security vulnerability scanning** (CVE detection)

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 API
- **FastAPI** community for excellent documentation
- **GitHub** for OAuth and REST API
- **Chakra UI** for beautiful React components

## 📞 Contact

**Your Name** - [@yourtwitter](https://twitter.com/yourtwitter) - your.email@example.com

**Project Link:** [https://github.com/yourusername/ai-code-review-assistant](https://github.com/yourusername/ai-code-review-assistant)

---

## 📖 Additional Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System design, component responsibilities, and dataflow
- **[API Reference](docs/API.md)** - Complete endpoint documentation and examples
- **[Contributing](docs/CONTRIBUTING.md)** - Guidelines for contributors
- **[Deployment](docs/DEPLOYMENT.md)** - Local development and production deployment

---

### ⭐ If you find this project useful, please consider giving it a star on GitHub!

**Made with ❤️ by [Your Name]**