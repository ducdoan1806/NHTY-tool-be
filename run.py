import os
from app import create_app

config_path = os.path.join(os.path.dirname(__file__), 'app/config.py')
app = create_app(config_path)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=81818)
