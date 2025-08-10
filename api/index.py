# api/index.py
from plume_tracker import create_app

app = create_app()

# Vercel usará la variable `app` como entrypoint WSGI
