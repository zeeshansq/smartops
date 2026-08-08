<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=6366f1&height=200&section=header&text=SmartOps&fontSize=80&fontColor=ffffff&fontAlignY=38&desc=Enterprise%20B2B%20SaaS%20Architecture%20Engine&descAlignY=58&descColor=a5b4fc" />

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2_LTS-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Redis](https://img.shields.io/badge/Redis-7.x-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![DRF](https://img.shields.io/badge/Django_REST-3.15-ff1709?style=for-the-badge&logo=django&logoColor=white)](https://django-rest-framework.org)
[![JWT](https://img.shields.io/badge/SimpleJWT-5.3-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)](https://django-rest-framework-simplejwt.readthedocs.io)
[![Live Site](https://img.shields.io/badge/Live-smartops.nschool.pk-6366f1?style=for-the-badge&logo=google-chrome&logoColor=white)](https://smartops.nschool.pk/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<br/>

> **SmartOps** is a production-grade, full-stack B2B SaaS platform boilerplate. Built to demonstrate and solve the most demanding infrastructure challenges in modern software businesses — from iron-clad data isolation between clients, to AI-powered automation running silently in the background, to a beautiful administrative command center.

<br/>

[🚀 Live Site: smartops.nschool.pk](https://smartops.nschool.pk/) · [🔑 Demo Accounts](#-live-demo--test-credentials) · [🏗️ Architecture](#-system-architecture) · [🎯 Features](#-core-features) · [📚 Production Docs](#-production--deployment-documentation)

</div>

---

## 📖 Table of Contents

| # | Section | Description |
|---|---------|-------------|
| 1 | [💡 What is SmartOps?](#-what-is-smartops) | Plain-English explanation for non-tech & enterprise clients |
| 2 | [🔑 Live Demo & Test Credentials](#-live-demo--test-credentials) | Standard test accounts & seeder usage |
| 3 | [🎯 Core Features](#-core-features) | Full feature catalogue |
| 4 | [🧩 The Problem We Solve](#-the-problem-we-solve) | Why this architecture matters |
| 5 | [🏗️ System Architecture](#-system-architecture) | How all pieces connect |
| 6 | [📋 Workflow Scenarios](#-workflow-scenarios) | Step-by-step real-world flows |
| 7 | [🛠️ Technology Stack](#%EF%B8%8F-technology-stack) | Every tool, explained |
| 8 | [🚀 Quick Start](#-quick-start) | Installation in 5 minutes |
| 9 | [📚 Production & Deployment Documentation](#-production--deployment-documentation) | VPS guides, testing suite & co-existence architecture |
| 10 | [🛡️ Security & Compliance](#%EF%B8%8F-security--compliance) | Production-grade hardening |
| 11 | [📦 Boilerplate Value](#-boilerplate-value--future-projects) | How to reuse this foundation |
| 12 | [🗺️ Development Roadmap](#%EF%B8%8F-development-roadmap) | What's built, what's next |
| 13 | [🐙 GitHub & Developer Setup Guide](#-github--developer-setup-guide) | GitHub repo creation & git push instructions |

---

## 💡 What is SmartOps?

<details open>
<summary><strong>🎓 Read this if you're not a technical person</strong></summary>
<br/>

Imagine you run a software company that sells a tool to many different businesses — say, Acme Corp, TechGlobal, and FinanceHub. Each of those businesses is your **client**, and they all use the same software. But here's the challenge:

- ❌ **Acme Corp cannot see TechGlobal's data.** Ever.
- ❌ **If one client triggers a slow AI task, it should NOT freeze the entire system for everyone else.**
- ❌ **Client employees cannot accidentally access areas meant for your internal admin team.**

SmartOps solves all of these problems from day one. It is a **pre-built software foundation** — think of it like a professionally designed, load-bearing frame for a skyscraper. You don't start building a skyscraper by digging a trench yourself; you use engineered steel frames. SmartOps is that frame for software businesses.

**With SmartOps as your starting point, a development team can skip 3–6 months of foundational setup and go straight to building the features that make your product unique.**

</details>

<details>
<summary><strong>👨‍💻 Technical Summary</strong></summary>
<br/>

SmartOps is an opinionated, production-ready Django monorepo implementing:

- **Multi-Tenancy via Request Isolation** — Custom `TenantMiddleware` resolves workspace context from `X-Workspace-ID` headers on every request, preventing cross-tenant data leakage at the ORM level.
- **Event-Driven Async Architecture** — Celery distributed task queue backed by Redis broker offloads all heavy computation (LLM calls, report generation) outside the HTTP request lifecycle.
- **Dual Auth Layer** — Human users authenticate via stateless SimpleJWT tokens; machine integrations use PBKDF2-hashed API keys scoped to specific workspaces.
- **Role-Based Access Control (RBAC)** — `Owner → Admin → Member` permission hierarchy enforced at middleware and view levels.
- **Zero-Setup Admin Intelligence** — `django-unfold` powered admin console with live KPI dashboard callbacks.
- **Bare-Metal Multi-App Co-existence** — Configured to safely run on shared VPS infrastructure alongside existing services via namespaced systemd units, isolated PostgreSQL database `smartops`, and Redis DB Index 1.

</details>

---

## 🔑 Live Demo & Test Credentials

- **Live Platform URL**: [https://smartops.nschool.pk/](https://smartops.nschool.pk/)
- **Live Client Dashboard**: [https://smartops.nschool.pk/dashboard/](https://smartops.nschool.pk/dashboard/)
- **Live Admin Console**: [https://smartops.nschool.pk/admin/](https://smartops.nschool.pk/admin/)

### 👤 Standard Test Accounts

| Account Role | Email Address | Password | Access Portal |
|--------------|---------------|----------|---------------|
| **Platform Superadmin** | `admin@smartops.com` | `AdminPass123!` | Admin Console (`/admin/`) & Client Dashboard (`/dashboard/`) |
| **Staff Member (Engineering)** | `alice.chen@smartops.com` | `AdminPass123!` | Admin Console (`/admin/`) |
| **Staff Member (Operations)** | `marcus.rivera@smartops.com` | `AdminPass123!` | Admin Console (`/admin/`) |
| **Client Tenant User** | *(any generated user)* | `Password123!` | Client Web Dashboard (`/dashboard/`) |

### ⚡ 1-Command Data Generation

To generate fresh test data and a downloadable credential guide locally:

```bash
python manage.py seed_data --clean
```

> 📄 Running this command automatically creates `TEST_CREDENTIALS.txt` in your project root, listing all 40+ generated accounts and workspace URLs for easy reference. You can also view or download this list directly from the live landing page at `/dashboard/demo-credentials/`.

---

## 🎯 Core Features

<table>
<tr>
<td width="50%" valign="top">

### 🔐 Authentication & Access
- Custom `UUID`-based `User` model (email-first)
- Stateless **JWT access + refresh tokens**
- Programmatic **PBKDF2-hashed API Keys** per workspace
- Email verification flag
- Login IP tracking
- Role-based permission levels

</td>
<td width="50%" valign="top">

### 🏢 Multi-Tenant Workspaces
- Unlimited isolated **Organizations** (tenants)
- Per-request workspace resolution via `X-Workspace-ID`
- `Owner / Admin / Member` role hierarchy
- Active/inactive workspace status
- Workspace-scoped API key management

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🤖 AI & Async Processing
- **Celery + Redis** distributed task queue
- Instant `202 Accepted` response with `task_id`
- Multi-LLM support: GPT-4o, Claude 3.5, Gemini, Mistral
- Full **AIRequestLog** with token counting & cost tracking
- Error handling with retry logic and dead-letter queue

</td>
<td width="50%" valign="top">

### 📊 Analytics & Administration
- `django-unfold` powered admin console
- Live **KPI dashboard** callbacks (Users, Workspaces, Tokens)
- Full AI request log viewer with tenant filtering
- Seed command with 500+ realistic data records
- Client-facing **web dashboard** with Tailwind + Alpine.js

</td>
</tr>
</table>

---

## 🧩 The Problem We Solve

Every B2B SaaS company faces the same four infrastructure nightmares when building their platform. SmartOps engineers all four solutions from day one.

```
THE PROBLEM                             THE SMARTOPS SOLUTION
═══════════════════════════════════     ═══════════════════════════════════════════
❌ Cross-tenant data leaks in a     →   ✅ TenantMiddleware validates X-Workspace-ID
   shared database can expose           on every request. All ORM queries are
   Client A's data to Client B          auto-scoped to request.tenant.

❌ Calling AI APIs synchronously    →   ✅ Celery task queue offloads all LLM calls.
   blocks your server and causes         The API responds in <50ms with a task_id.
   HTTP timeouts                         Workers process tasks in the background.

❌ Sequential integer primary keys  →   ✅ All models use UUIDv4 primary keys.
   (/api/orgs/1/, /api/orgs/2/)          /api/orgs/9f3a-... is cryptographically
   let attackers enumerate records       unpredictable and un-enumerable.

❌ Mixed auth creates vulnerabilities→  ✅ Client users: JWT tokens.
   when admins and API scripts use       API scripts: PBKDF2-hashed API keys.
   the same login path                   Admin staff: separate /admin/ portal.
```

---

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                              │
│  Web Dashboard (Tailwind+Alpine)  ◄────►  REST API (Postman/cURL)   │
└──────────────────────────┬──────────────────────────┬──────────────┘
                           │ HTTP Request              │ API Key / JWT
┌──────────────────────────▼──────────────────────────▼──────────────┐
│                      DJANGO APPLICATION LAYER                       │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Auth Middleware │  │ TenantMiddleware  │  │   DRF ViewSets   │  │
│  │  (SimpleJWT)    │  │ (X-Workspace-ID)  │  │  (Rate Throttled)│  │
│  └────────┬────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           └────────────────────┼────────────────────── │            │
│                                ▼                        │            │
│                    ┌───────────────────┐               │            │
│                    │   Business Logic   │◄──────────────┘            │
│                    │  (Tenant-Scoped)   │                            │
│                    └─────────┬─────────┘                            │
└──────────────────────────────┼──────────────────────────────────────┘
                               │ Task dispatch
          ┌────────────────────┼─────────────────────────┐
          │                    ▼                          │
          │     ┌──────────────────────────┐             │
          │     │     REDIS BROKER         │             │
          │     │  (Task Queue + Results)  │             │
          │     └──────────┬───────────────┘             │
          │                ▼                              │
          │     ┌──────────────────────────┐             │
          │     │   CELERY WORKERS          │             │
          │     │  LLM API Calls            │             │
          │     │  Report Generation        │             │
          │     │  Email Dispatching        │             │
          │     └──────────┬───────────────┘             │
          │                ▼                              │
          │     ┌──────────────────────────┐             │
          │     │  POSTGRESQL DATABASE      │             │
          │     │  AIRequestLog             │             │
          │     │  (Token Usage + Costs)    │             │
          │     └──────────┬───────────────┘             │
          └─────────────────────────────────────────────-┘
```

---

## 📋 Workflow Scenarios

### 🔑 Scenario 1: A New Client Signs Up

```bash
POST /api/v1/auth/token/
{
  "email": "admin@smartops.com",
  "password": "AdminPass123!"
}
```

```bash
POST /api/v1/workspaces/
Authorization: Bearer <access_token>

{
  "name": "Acme Corp"
}
```

> ✅ User is automatically assigned the **Owner** role for the workspace. All data is isolated to this workspace.

---

### 🤖 Scenario 2: Triggering an AI Task (Async)

```bash
POST /api/v1/ai/generate/
Authorization: Bearer <access_token>
X-Workspace-ID: 9f3a4b22-1c8d-4e6f-b2a1-0d5e7f9c3b41

{
  "prompt": "Summarize the Q3 financial report.",
  "model": "gpt-4o"
}

# Instant Response (202 Accepted)
{
  "task_id": "c7d2e891-ff34-4b12-9c01-d8e4a5f6b7c2",
  "status": "pending"
}
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | Python 3.11 + Django 5.2 LTS | Core logic, security routing, ORM |
| **API Layer** | DRF 3.15 + SimpleJWT 5.3 | RESTful endpoints, JWT tokens, rate throttling |
| **Database** | PostgreSQL 15+ | Relational data, JSONB support |
| **Task Queue** | Celery 5.4 + Redis 7.x | Asynchronous background AI processing |
| **Admin UI** | django-unfold 0.34 | Tailwind-powered admin console with KPI cards |
| **Client Frontend** | Tailwind CSS + Alpine.js | Reactive web dashboard UI |
| **Production Server** | Nginx + Gunicorn (UvicornWorker) | High-performance ASGI web server on Linux VPS |

---

## 🚀 Quick Start

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/smartops.git
cd smartops

# 2. Setup virtual environment & dependencies
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env

# 4. Apply migrations & seed test data
python manage.py migrate
python manage.py seed_data --clean

# 5. Start development server
python manage.py runserver

# 6. Start Celery worker (in separate terminal)
celery -A config worker --pool=solo --loglevel=info
```

Open `http://127.0.0.1:8000/` to view the application!

---

## 📚 Production & Deployment Documentation

Comprehensive technical documentation is stored in the [`docs/`](file:///c:/smartops/docs/) directory:

- 🧪 **[Testing Guide (`docs/01_TESTING_GUIDE.md`)](file:///c:/smartops/docs/01_TESTING_GUIDE.md)** — Complete 29-unit test suite breakdown, DRF API cURL smoke-tests, and GitHub Actions CI/CD setup.
- 🚀 **[Production Deployment Guide (`docs/02_PRODUCTION_DEPLOYMENT.md`)](file:///c:/smartops/docs/02_PRODUCTION_DEPLOYMENT.md)** — Complete Linux VPS deployment guide, Nginx server block configuration for `smartops.nschool.pk`, systemd unit files, Let's Encrypt TLS setup, and multi-app co-existence matrix.

---

## 🛡️ Security & Compliance

- **PBKDF2 API Key Hashing** — Plaintext keys are never stored.
- **Strict Rate Throttling** — Prevents brute-force attacks on auth endpoints.
- **Tenant Middleware Isolation** — Auto-scopes database queries to `request.tenant`.
- **UUID Primary Keys** — Prevents ID enumeration scanning.
- **Separated Login Flows** — `/admin/login/` (staff) is separated from `/dashboard/login/` (clients).
- **HSTS & Secure Cookies** — Automated HTTPS redirection, SameSite Lax, and HttpOnly cookies enabled in production (`IS_PRODUCTION=True`).

---

## 📦 Boilerplate Value & Future Projects

Using SmartOps as a foundation saves **9–14 weeks of core architecture setup** on new software projects. Ideal for LegalTech, FinTech, HealthTech, EdTech, and enterprise SaaS applications.

---

## 🗺️ Development Roadmap

```
Phase 1   ████████████████████   COMPLETED   (Multi-Tenancy & Models)
Phase 2   ████████████████████   COMPLETED   (REST API & API Keys)
Phase 3   ████████████████████   COMPLETED   (Celery + Redis Async LLM Engine)
Phase 4   ████████████████████   COMPLETED   (django-unfold Admin & Client UI)
Phase 5   ████████████████████   COMPLETED   (Cloud VPS Deployment, Co-existence & Docs)
```

---

## 🐙 GitHub & Developer Setup Guide

Follow these exact steps to create a GitHub repository and link your SmartOps codebase.

### Step 1 — Create a GitHub Account
If you don't already have one, sign up at [github.com](https://github.com).

### Step 2 — Create a New Repository on GitHub
1. Click the **`+`** icon in the top-right corner of GitHub → select **"New repository"**.
2. Set **Repository Name**: `smartops`
3. Add **Description**: `Production-grade B2B SaaS multi-tenant boilerplate — Django, Celery, Redis, AI Services`
4. Select **Public** *(recommended for client showcase)* or **Private**.
5. ⚠️ **Do NOT check** "Add a README file", "Add .gitignore", or "Choose a license" — your local repository already has these files!
6. Click **"Create repository"**.

### Step 3 — Configure Local Git Identity
Open PowerShell/Terminal inside your project folder:

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

### Step 4 — Initialize Git & Push Code

```bash
# 1. Initialize local repository
git init

# 2. Check status (verify .env, db.sqlite3, and TEST_CREDENTIALS.txt are ignored)
git status

# 3. Stage all project files
git add .

# 4. Commit project files
git commit -m "feat: initial commit for SmartOps enterprise SaaS boilerplate"

# 5. Link local repository to GitHub remote
# (Replace YOUR_USERNAME with your actual GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/smartops.git

# 6. Rename branch to main
git branch -M main

# 7. Push codebase to GitHub
git push -u origin main
```

### Step 5 — Verify Repository Topics
On your GitHub repository page:
1. Click the ⚙️ gear icon next to **About**.
2. Add relevant topics:
   ```
   django python saas multi-tenant celery redis rest-api jwt boilerplate enterprise-saas b2b
   ```

---

## 👨‍💻 Author

<div align="center">

**Zeeshan Shabbir Qureshi**  
*Principal Python/Django Systems Architect*

</div>

---

## 📄 License

```
MIT License
Copyright (c) 2024 Zeeshan Shabbir Qureshi
```

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=6366f1&height=100&section=footer" />
</div>