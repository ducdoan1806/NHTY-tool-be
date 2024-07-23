import jwt
import datetime
from flask import Flask, request, jsonify, url_for, send_from_directory, session
from werkzeug.utils import secure_filename
from googletrans import Translator
from gtts import gTTS
import moviepy.editor as mp
import os
import re
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from functools import wraps
from flask_cors import CORS
from flask import request

secret_key = os.urandom(24).hex()
jwt_secret_key = os.urandom(24).hex()
app = Flask(__name__)
CORS(app)
# Configure the SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.secret_key = secret_key
app.config["SECRET_KEY"] = secret_key
app.config["JWT_SECRET_KEY"] = jwt_secret_key

# Initialize the database and migration
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Define User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


# Define Project model
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("projects", lazy=True))


# Define Content model
class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10), nullable=False)
    text_translate = db.Column(db.Text, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    project = db.relationship("Project", backref=db.backref("contents", lazy=True))


# Define Image model
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    project = db.relationship("Project", backref=db.backref("images", lazy=True))


# Ensure the upload folder exists
if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])


# Function to validate email
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)


# Function to validate password
def is_valid_password(password):
    return len(password) >= 6  # Add more criteria as needed


# Function to check allowed file extensions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Decorator to require authentication
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "jwt_token" not in session:
            return jsonify({"error": "Unauthorized access"}), 401
        return f(*args, **kwargs)

    return decorated_function


# Function to generate JWT token
def generate_jwt_token(user_id):
    try:
        payload = {
            "exp": datetime.datetime.utcnow()
            + datetime.timedelta(days=1),  # Token expiration time (1 day)
            "iat": datetime.datetime.utcnow(),  # Issued at time
            "sub": user_id,  # Subject (user_id or any identifier)
        }
        jwt_token = jwt.encode(payload, app.config["JWT_SECRET_KEY"], algorithm="HS256")
        return jwt_token
    except Exception as e:
        return str(e)


@app.route("/")
def index():
    return "API is running!"


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()  # Lấy dữ liệu JSON từ yêu cầu

    if not data:  # Kiểm tra nếu không có dữ liệu
        return jsonify({"error": "No JSON data received"}), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "Missing data fields"}), 400

    if not is_valid_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    if not is_valid_password(password):
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    new_user = User(name=name, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    user = User.query.filter_by(email=email, password=password).first()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    # Generate JWT token
    jwt_token = generate_jwt_token(user.id)

    if not jwt_token:
        return jsonify({"error": "Failed to generate JWT token"}), 500

    # Store user ID and token in session (optional, depending on your use case)
    session["user_id"] = user.id
    session["jwt_token"] = jwt_token  # Store token as string in session

    # Prepare the response JSON object
    response_data = {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            # Add more fields as needed
        },
        "jwt_token": jwt_token,  # Return token as string
    }

    return jsonify({"jwt_token": response_data}), 200


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out successfully"}), 200


@app.route("/projects", methods=["GET"])
@login_required
def get_projects():
    try:
        # Query all projects from the database
        projects = Project.query.all()

        # Prepare JSON response
        projects_list = []
        for project in projects:
            project_data = {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "user_id": project.user_id,
            }
            projects_list.append(project_data)

        return jsonify({"projects": projects_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/create_project", methods=["POST"])
# @login_required
def create_project():
    data = request.get_json()
    title = data.get("title")
    description = data.get("description")
    user_id = data.get("user_id")

    if not title:
        return jsonify({"error": "Missing title field"}), 400

    new_project = Project(title=title, description=description, user_id=user_id)
    db.session.add(new_project)
    db.session.commit()
    return jsonify({"message": "Project created"}), 200


# Function to check allowed file extensions
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


# API endpoint to upload images
@app.route("/upload_images", methods=["POST"])
@login_required
def upload_images():
    if "images" not in request.files:
        return jsonify({"error": "No images uploaded"}), 400

    files = request.files.getlist("images")
    project_id = request.form.get("project_id")

    if not project_id:
        return jsonify({"error": "Missing project_id field"}), 400

    # Check if the project exists
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    for file in files:
        if file:
            if os.path.isdir(
                file.filename
            ):  # Handle case where a directory is uploaded
                for filename in os.listdir(file.filename):
                    if allowed_file(filename):
                        file_path = os.path.join(
                            app.config["UPLOAD_FOLDER"], secure_filename(filename)
                        )
                        full_path = os.path.join(file.filename, filename)
                        file.save(full_path)
                        new_image = Image(project_id=project_id, file_path=file_path)
                        db.session.add(new_image)
            else:
                if allowed_file(file.filename):
                    file_path = os.path.join(
                        app.config["UPLOAD_FOLDER"], secure_filename(file.filename)
                    )
                    file.save(file_path)
                    new_image = Image(project_id=project_id, file_path=file_path)
                    db.session.add(new_image)

    db.session.commit()
    return jsonify({"message": "Images uploaded successfully"}), 200


@app.route("/add_text", methods=["POST"])
@login_required
def add_text():
    data = request.get_json()
    texts = data.get("texts")
    project_id = data.get("project_id")

    if not project_id:
        return jsonify({"error": "Missing project_id field"}), 400
    if not texts:
        return jsonify({"error": "No texts provided"}), 400

    # Check if the project exists
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    for text in texts:
        if text.strip():
            content = Content.query.filter_by(
                project_id=project_id, text=text.strip()
            ).first()
            if content:
                return jsonify({"error": "Duplicate text entry"}), 400
            new_text = Content(
                project_id=project_id,
                text=text.strip(),
                language="",  # Assuming text is in Vietnamese
                text_translate="",  # Placeholder for translation; should be updated after actual translation
            )
            db.session.add(new_text)

    db.session.commit()
    return jsonify({"message": "Texts added successfully"}), 200


@app.route("/translate", methods=["POST"])
@login_required
def translate_text():
    data = request.get_json()
    text = data.get("text")
    target_lang = data.get("lang")
    project_id = data.get("project_id")

    if not text or not target_lang or not project_id:
        return jsonify({"error": "Missing text, lang, or project_id field"}), 400

    # Check if the project exists
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    translator = Translator()
    translated = translator.translate(text, dest=target_lang)

    # Update or insert the translated text into the Content table
    content = Content.query.filter_by(project_id=project_id, text=text).first()
    if content:
        content.text_translate = translated.text
    else:
        new_content = Content(
            project_id=project_id,
            text=text,
            language=target_lang,
            text_translate=translated.text,
        )
        db.session.add(new_content)

    db.session.commit()
    return jsonify({"translated_text": translated.text})


@app.route("/text_to_speech", methods=["POST"])
@login_required
def text_to_speech():
    data = request.get_json()
    text = data.get("text")
    lang = data.get("lang", "vi")  # Default language is Vietnamese
    if not text:
        return jsonify({"error": "No text provided"}), 400

    tts = gTTS(text, lang=lang)
    filename = secure_filename(f"{text}.mp3")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    tts.save(filepath)
    return jsonify(
        {"file_url": url_for("uploaded_file", filename=filename, _external=True)}
    )


@app.route("/generate_video", methods=["POST"])
@login_required
def generate_video():
    data = request.get_json()
    text = data.get("text")
    tts_en = gTTS(text, lang="en")
    tts_vi = gTTS(text, lang="vi")

    en_filename = secure_filename("voice_en.mp3")
    vi_filename = secure_filename("voice_vi.mp3")
    en_filepath = os.path.join(app.config["UPLOAD_FOLDER"], en_filename)
    vi_filepath = os.path.join(app.config["UPLOAD_FOLDER"], vi_filename)

    tts_en.save(en_filepath)
    tts_vi.save(vi_filepath)

    image_file = request.files.get("image")
    if image_file and allowed_file(image_file.filename):
        image_filename = secure_filename(image_file.filename)
        image_filepath = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
        image_file.save(image_filepath)

        # Create video clips with audio
        image_clip = mp.ImageClip(image_filepath).set_duration(
            10
        )  # Set the duration as needed
        en_audio_clip = mp.AudioFileClip(en_filepath)
        vi_audio_clip = mp.AudioFileClip(vi_filepath)

        en_video = image_clip.set_audio(en_audio_clip)
        vi_video = image_clip.set_audio(vi_audio_clip)

        en_video_filename = secure_filename("video_en.mp4")
        vi_video_filename = secure_filename("video_vi.mp4")
        en_video_filepath = os.path.join(app.config["UPLOAD_FOLDER"], en_video_filename)
        vi_video_filepath = os.path.join(app.config["UPLOAD_FOLDER"], vi_video_filename)

        en_video.write_videofile(en_video_filepath, codec="libx264")
        vi_video.write_videofile(vi_video_filepath, codec="libx264")

        return jsonify(
            {
                "en_video_url": url_for(
                    "uploaded_file", filename=en_video_filename, _external=True
                ),
                "vi_video_url": url_for(
                    "uploaded_file", filename=vi_video_filename, _external=True
                ),
            }
        )

    return jsonify({"error": "No image file provided"}), 400


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=81818)
