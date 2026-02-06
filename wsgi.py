# wsgi.py - WSGI Entry Point für Production (Gunicorn/uWSGI)
"""WSGI Entry Point für Production-Deployments."""

from app import app

if __name__ == "__main__":
    app.run()
