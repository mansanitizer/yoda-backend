import os
import sys
from pathlib import Path

from flask import Flask, Response, render_template

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.session_manager import SessionManager
from app.routes.api import create_api_blueprint
from app.scripts import shadow_boxing_analyzer, two_player_analyzer
from app.storage.db import init_db


def create_app() -> Flask:
    init_db()
    flask_app = Flask(__name__)
    session_manager = SessionManager()
    flask_app.register_blueprint(create_api_blueprint(session_manager))

    @flask_app.get("/")
    def index() -> str:
        return render_template("index.html")

    @flask_app.get("/two_player")
    def two_player() -> str:
        return render_template("two_player.html")

    @flask_app.get("/shadow_boxing")
    def shadow_boxing() -> str:
        return render_template("shadow_boxing.html")

    @flask_app.get("/video_feed_two_player")
    def video_feed_two_player() -> Response:
        return Response(
            two_player_analyzer.generate_frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @flask_app.get("/video_feed_shadow_boxing")
    def video_feed_shadow_boxing() -> Response:
        return Response(
            shadow_boxing_analyzer.generate_frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    return flask_app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
