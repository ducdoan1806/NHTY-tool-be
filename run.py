import os
from app import create_app
from flask_cors import CORS

config_path = os.path.join(os.path.dirname(__file__), "app/config.py")
app = create_app(config_path)

CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:5173"]}},
    supports_credentials=True,
)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=81818)
