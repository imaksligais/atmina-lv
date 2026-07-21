"""Launch the atmina ops dashboard at http://127.0.0.1:8080.

This script is the only supported entry point — Flask's auto-reloader and
debug mode are off by default. Bind is hard-coded to 127.0.0.1; never expose
this server beyond localhost.
"""
from src.dashboard import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=8080, debug=False)
