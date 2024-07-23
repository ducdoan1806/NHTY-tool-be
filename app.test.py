import jwt
import datetime
from flask import Flask, request, jsonify, send_from_directory, session, url_for
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
from googletrans import LANGUAGES
from gtts.lang import tts_langs
app = Flask(__name__)
CORS(app)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.secret_key = 'your_secret_key'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('projects', lazy=True))

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10), nullable=False)
    text_translate = db.Column(db.Text, nullable=False)  # Ensure this line is present
    language_translate = db.Column(db.String(10), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship('Project', backref=db.backref('contents', lazy=True))

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Function to validate email
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Function to validate password
def is_valid_password(password):
    return len(password) >= 6  # Add more criteria as needed

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Decorator to require authentication
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'jwt_token' not in session:
            return jsonify({"error": "Unauthorized access"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Function to generate JWT token
def generate_jwt_token(user_id):
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),  # Token expiration time (1 day)
            'iat': datetime.datetime.utcnow(),  # Issued at time
            'sub': user_id  # Subject (user_id or any identifier)
        }
        jwt_token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256').decode('utf-8')
        print(jwt_token)
        return jwt_token
    except Exception as e:
        return str(e)

@app.route('/')
def index():
    return 'API is running!'

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "No JSON data received"}), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"success": False, "error": "Missing data fields"}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "error": "Invalid email format"}), 400
    if not is_valid_password(password):
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "Email already registered"}), 400

    new_user = User(name=name, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "message": "User registered successfully", "user": {
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email
    }}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email, password=password).first()

    if not user:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

    # Generate JWT token
    jwt_token = generate_jwt_token(user.id)
    if not jwt_token:
        return jsonify({"success": False, "error": "Failed to generate JWT token"}), 500

    # Store user ID and token in session
    session['user_id'] = user.id
    session['jwt_token'] = jwt_token

    # Prepare the response JSON object
    response_data = {
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        },
        "jwt_token": jwt_token
    }

    return jsonify(response_data), 200

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    session.pop('user_id', None)
    session.pop('jwt_token', None)
    return jsonify({"success": True, "message": "Logged out successfully"}), 200

@app.route('/projects', methods=['GET'])
@login_required
def get_projects():
    try:
        user_id = session.get('user_id')
        projects = Project.query.filter_by(user_id=user_id).all()

        projects_list = []
        for project in projects:
            project_data = {
                'id': project.id,
                'title': project.title,
                'description': project.description,
                'user_id': project.user_id
            }
            projects_list.append(project_data)

        return jsonify({"projects": projects_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create_project', methods=['POST'])
@login_required
def create_project():
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    user_id = session.get('user_id')

    if not title:
        return jsonify({"success": False, "error": "Missing title field"}), 400

    new_project = Project(title=title, description=description, user_id=user_id)
    db.session.add(new_project)
    db.session.commit()
    return jsonify({"success": True, "message": "Project created", "project": {
        "id": new_project.id,
        "title": new_project.title,
        "description": new_project.description,
        "user_id": new_project.user_id
    }}), 200

@app.route('/upload_images', methods=['POST'])
@login_required
def upload_images():
    if 'images' not in request.files:
        return jsonify({"success": False, "error": "No file part in the request"}), 400

    files = request.files.getlist('images')
    project_id = request.form.get('project_id')

    if not project_id:
        return jsonify({"success": False, "error": "Missing project_id field"}), 400

    project = Project.query.get(project_id)
    if not project:
        return jsonify({"success": False, "error": "Project not found"}), 404

    for file in files:
        if file and allowed_file(file.filename):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
            file.save(file_path)
            new_content = Content(
                text=file.filename,
                language='en',  # Assuming default language is English
                text_translate='',  # Placeholder for translation
                language_translate='',  # Placeholder for translation language
                file_path=file_path,
                project_id=project_id
            )
            db.session.add(new_content)

    db.session.commit()
    return jsonify({"success": True, "message": "Images uploaded successfully"}), 200

@app.route('/delete_image', methods=['POST'])
@login_required
def delete_image():
    data = request.get_json()
    image_id = data.get('image_id')

    if not image_id:
        return jsonify({"success": False, "error": "Missing image_id field"}), 400

    image = Content.query.get(image_id)
    if not image:
        return jsonify({"success": False, "error": "Image not found"}), 404

    db.session.delete(image)
    db.session.commit()

    if os.path.exists(image.file_path):
        os.remove(image.file_path)

    return jsonify({"success": True, "message": "Image deleted successfully"}), 200

@app.route('/get_images/<project_id>', methods=['GET'])
@login_required
def get_images(project_id):
    images = Content.query.filter_by(project_id=project_id).all()
    image_list = [{"id": img.id, "file_path": img.file_path} for img in images]
    return jsonify({"success": True, "images": image_list}), 200

@app.route('/add_text', methods=['POST'])
@login_required
def add_text():
    data = request.get_json()
    texts = data.get('texts')
    language = data.get('language', 'en')  # Assuming default language is English
    project_id = data.get('project_id')
    
    if not project_id:
        return jsonify({"success": False, "error": "Missing project_id field"}), 400
    if not texts or not isinstance(texts, list):
        return jsonify({"success": False, "error": "No texts provided or texts should be a list"}), 400

    project = Project.query.get(project_id)
    if not project:
        return jsonify({"success": False, "error": "Project not found"}), 404

    text_translations = data.get('text_translations', [])
    if len(text_translations) != len(texts):
        return jsonify({"success": False, "error": "Number of text translations does not match the number of texts"}), 400

    for i, text in enumerate(texts):
        if text.strip():
            text_translate = text_translations[i] if text_translations else ''  # Use provided translation or empty string
            existing_content = Content.query.filter_by(text=text.strip(), project_id=project_id).first()
            if existing_content:
                existing_content.text_translate = text_translate
            else:
                new_content = Content(
                    text=text.strip(),
                    language=language,
                    text_translate=text_translate,
                    language_translate='',  # Placeholder for translation language
                    file_path='',  # No file path for text entries
                    project_id=project_id
                )
                db.session.add(new_content)

    db.session.commit()
    return jsonify({"success": True, "message": "Texts added/updated successfully"}), 200


@app.route('/translate', methods=['POST'])
@login_required
def translate_text():
    data = request.get_json()
    text = data.get('text')
    language_translate = data.get('language_translate')
    project_id = data.get('project_id')

    if not text or not language_translate or not project_id:
        return jsonify({"success": False, "error": "Missing text, lang, or project_id field"}), 400

    project = Project.query.get(project_id)
    if not project:
        return jsonify({"success": False, "error": "Project not found"}), 404

    translator = Translator()
    translated = translator.translate(text, dest=language_translate)

    new_content = Content(
        text=text,
        language='en',  # Assuming default language is English
        text_translate=translated.text,
        language_translate=language_translate,
        file_path='',  # No file path for translated entries
        project_id=project_id
    )
    db.session.add(new_content)
    db.session.commit()

    return jsonify({"success": True, "translated_text": translated.text}), 200

@app.route('/text_to_speech', methods=['POST'])
@login_required
def text_to_speech():
    data = request.get_json()
    project_id = data.get('project_id')
    speaker = data.get('speaker')
    
    if not project_id:
        return jsonify({"success": False, "error": "Missing project_id field"}), 400
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"success": False, "error": "Project not found"}), 404
    
    texts = [content.text for content in project.contents if content.text.strip()]
    lang = project.language  # Assuming project has a language field
    
    if not texts:
        return jsonify({"success": False, "error": "No text provided in the project"}), 400
    
    try:
        audio_urls = []
        for text in texts:
            if speaker:
                if speaker.lower() not in tts_langs():
                    return jsonify({"success": False, "error": "Invalid speaker choice"}), 400
                tts = gTTS(text, lang=lang, tld=speaker.lower())
            else:
                tts = gTTS(text, lang=lang)
            
            filename = secure_filename(f"{text}.mp3")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            tts.save(filepath)
            audio_urls.append(url_for('serve_static', filename=filename, _external=True))
        
        return jsonify({"success": True, "audio_urls": audio_urls}), 200
    
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to generate audio: {str(e)}"}), 500
    

@app.route('/combine_audio', methods=['POST'])
@login_required
def combine_audio():
    data = request.get_json()
    audio_files = data.get('audio_files')
    project_id = data.get('project_id')

    if not audio_files or not isinstance(audio_files, list) or not project_id:
        return jsonify({"error": "Missing audio_files or project_id field or audio_files should be a list"}), 400

    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    audio_clips = []
    for file_name in audio_files:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        if os.path.exists(file_path):
            audio_clips.append(mp.AudioFileClip(file_path))
        else:
            return jsonify({"error": f"Audio file {file_name} not found"}), 404

    combined = mp.concatenate_audioclips(audio_clips)
    combined_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f"combined_{project_id}.mp3"))
    combined.write_audiofile(combined_path)

    return jsonify({
        "message": "Audio combined successfully",
        "combined_path": url_for('serve_static', filename=secure_filename(f"combined_{project_id}.mp3"), _external=True)
    }), 200

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port= 12345)