import os
from app import create_app

config_path = os.path.join(os.path.dirname(__file__), 'app/config.py')
app = create_app(config_path)
