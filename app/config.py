import os

SECRET_KEY = os.urandom(24).hex()
JWT_SECRET_KEY = os.urandom(24).hex()
SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
UPLOAD_FOLDER = 'uploads'
TIMEZONE = 'Asia/Ho_Chi_Minh'  # Đây là múi giờ UTC+7
