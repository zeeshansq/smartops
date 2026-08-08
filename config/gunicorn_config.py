# =============================================================================
# SmartOps — Gunicorn Configuration
# =============================================================================
# Optimized for a GCP e2-micro instance (1 vCPU, 1 GB RAM).
# Django is served via Gunicorn's UvicornWorker to handle async ASGI requests.
#
# Workers = (2 × CPU cores) + 1  →  For 1 vCPU: 3 workers
# On a constrained 1 GB instance we cap at 2 to leave headroom for Celery,
# Postgres, and Redis processes which also reside on the same machine.
# =============================================================================

import multiprocessing

# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------
# Gunicorn listens on a Unix socket — Nginx communicates via this socket.
# Never expose Gunicorn directly on a public port.
bind = "unix:/run/gunicorn/smartops.sock"

# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------
# UvicornWorker enables async support via ASGI (required for Django Channels,
# async views, or WebSocket upgrades in the future).
worker_class = "uvicorn.workers.UvicornWorker"

# 2 workers: balanced for 1 GB RAM. Each Uvicorn worker uses ~80-120 MB RSS.
workers = 2

# Per-worker async coroutine capacity — sensible default for I/O-bound work.
worker_connections = 256

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
# Silence false-positive "worker timeout" kills during long-running AI calls.
timeout = 120           # Hard kill after 120 s (covers AI API round-trips)
graceful_timeout = 30   # Allow in-flight requests to finish during reload
keepalive = 5           # Keep-alive timeout for persistent connections

# ---------------------------------------------------------------------------
# Process Naming
# ---------------------------------------------------------------------------
proc_name = "smartops"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Route both access and error logs to stdout/stderr — systemd captures them.
accesslog  = "-"   # stdout
errorlog   = "-"   # stderr
loglevel   = "warning"  # Only WARNING+ in production; change to "info" for debug

# Include the time taken per request (ms) in the access log.
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)s'

# ---------------------------------------------------------------------------
# Process Management
# ---------------------------------------------------------------------------
# Restart each worker after N requests to combat memory leaks.
max_requests        = 500
max_requests_jitter = 50    # Randomize restart point to avoid thundering herd

# Pre-fork worker model — master forks workers AFTER loading the app.
# This amortizes Django startup cost across all workers.
preload_app = True
