import re
import jwt
import datetime
import os
from functools import wraps
from .config import *
from flask import Flask, request, jsonify, url_for, send_from_directory, session, request

class StandardPagesPagination:
    def __init__(self, query, page, per_page):
        self.page = page
        self.per_page = per_page
        self.total = query.count()
        self.pages = self.total // self.per_page + (1 if self.total % self.per_page > 0 else 0)
        self.items = query.offset((self.page - 1) * self.per_page).limit(self.per_page).all()
        self.base_url = request.base_url

    def get_page_link(self, page):
        if page < 1 or page > self.pages:
            return None
        return f"{self.base_url}?page={page}&page_size={self.per_page}"

    def to_dict(self, schema):
        items = schema.dump(self.items)
        return {
            'page': self.page,
            'page_size': self.per_page,
            'count': self.total,
            'items': items,
            'next_page': self.get_page_link(self.page + 1) if self.page < self.pages else None,
            'previous_page': self.get_page_link(self.page - 1) if self.page > 1 else None
        }
        
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_valid_password(password):
    return len(password) >= 6

def generate_jwt_token(user_id):
    try:
        # Set expiration time
        expires_delta = datetime.timedelta(days=7)  # Default to 1 day
        expiration = datetime.datetime.utcnow() + expires_delta
        payload = {
            "sub": user_id,
            "exp": expiration,  # Add expiration time
        }
        jwt_token = jwt.encode(payload,JWT_SECRET_KEY, algorithm="HS256")
        return {
            "token":jwt_token,
            "exp": payload["exp"]
        }
    except Exception as e:
        return str(e)  # Ensure this is a string

def decode_jwt_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        compressed_payload = payload.get("data")
        decompressed_payload = zlib.decompress(compressed_payload.encode('latin1'))
        return decompressed_payload.decode()
    except Exception as e:
        return str(e)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "jwt_token" not in session:
            return jsonify({"error": "Unauthorized access"}), 401
        return f(*args, **kwargs)
    return decorated_function
