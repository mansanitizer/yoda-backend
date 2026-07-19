import os
import sys
from pathlib import Path

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.session_manager import SessionManager
from app.routes.api import create_api_blueprint
from app.storage.db import init_db


def create_app() -> Flask:
    init_db()
    flask_app = Flask(__name__)
    session_manager = SessionManager()
    flask_app.register_blueprint(create_api_blueprint(session_manager))
    return flask_app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
