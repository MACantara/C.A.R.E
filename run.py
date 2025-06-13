import os
from app import create_app, socketio

# Get configuration from environment variable
config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config_name)

if __name__ == "__main__":
    # Use SocketIO run for WebSocket support
    socketio.run(app, debug=app.config.get("DEBUG", True), host="0.0.0.0", port=5000)
