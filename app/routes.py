from flask import request, jsonify, redirect, session, url_for, send_file

import os, sys
import io

import base64
from werkzeug.utils import secure_filename
from googletrans import Translator, LANGUAGES
from gtts import gTTS
import uuid
from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    TextClip,
    CompositeVideoClip,
    AudioFileClip,
    concatenate_audioclips,
)
from .models import *
from . import db
from .utils import *
from .serializers import *
from marshmallow import ValidationError
from gtts import gTTS
import json
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Đường dẫn lưu trữ tạm thời
TEMP_DIR = "C:\\Users\\ddoan\\Project\\NHTY-tool-be\\temp"  # folder chứa ảnh và video
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)


def resize_image(image_path, target_size, index, new_uuid):
    try:
        img = Image.open(image_path)
        img.thumbnail(target_size, Image.Resampling.LANCZOS)

        # Tạo một hình ảnh mới với kích thước đích và màu nền đen
        background = Image.new("RGB", target_size, (0, 0, 0))
        img_position = (
            (target_size[0] - img.size[0]) // 2,
            (target_size[1] - img.size[1]) // 2,
        )
        background.paste(img, img_position)

        resized_image_path = os.path.join(
            TEMP_DIR, f"resized_image_{new_uuid}_{index}.jpg"
        )
        background.save(resized_image_path, "JPEG")
        return resized_image_path
    except Exception as e:
        logger.error(f"Error resizing and padding image {image_path}: {e}")
        raise


def init_app(app):
    # @app.after_request
    # def after_request(response):
    #     response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4443')
    #     response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    #     response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    #     response.headers.add('Access-Control-Allow-Credentials', 'true')
    #     return response

    @app.route("/")
    def index():
        return "API is running!"

    @app.route("/register", methods=["POST"])
    def register():
        data = request.get_json()
        if not data:
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
        # Store user ID and token in session
        session["user_id"] = user.id
        session["jwt_token"] = jwt_token
        response_data = {
            "access_token": jwt_token.get("token"),
            "expires_in": jwt_token.get("exp"),
            "id": user.id,
            "name": user.name,
            "email": user.email,
        }
        # response_data.set_cookie('jwt_token', jwt_token, httponly=True, secure=True, samesite='None')

        return jsonify(response_data), 200

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        session.pop("user_id", None)
        return jsonify({"message": "Logged out successfully"}), 200

    @app.route("/user", methods=["GET"])
    @login_required
    def get_user():
        user_id = getattr(
            request, "user_id", None
        )  # Assumes user ID is stored in the session
        if not user_id:
            return jsonify({"error": "User ID not found in session"}), 401

        user = User.query.get_or_404(user_id)
        user_schema = UserSchema()
        return jsonify(user_schema.dump(user))

    @app.route("/projects/<int:project_id>", methods=["GET", "DELETE"])
    @login_required
    def project_details(project_id):
        if request.method == "GET":
            return get_project_details(project_id)
        elif request.method == "DELETE":
            return delete_project(project_id)

    def get_project_details(project_id):
        try:
            user_id = getattr(request, "user_id", None)  # Get user_id from session
            project = Project.query.filter_by(id=project_id, user_id=user_id).first()

            if not project:
                return jsonify({"error": "Project not found"}), 404

            project_schema = ProjectDetailsSchema()
            project_data = project_schema.dump(project)

            return jsonify(project_data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def delete_project(project_id):
        try:
            if not project_id:
                return jsonify({"error": "No project ID provided"}), 400

            user_id = getattr(request, "user_id", None)  # Get user_id from session
            project = Project.query.filter_by(id=project_id, user_id=user_id).first()

            if not project:
                return (
                    jsonify(
                        {
                            "error": "Project not found or you do not have permission to delete it"
                        }
                    ),
                    404,
                )

            db.session.delete(project)
            db.session.commit()

            return jsonify({"message": "Project deleted successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/projects", methods=["GET", "POST"])
    @login_required
    def projects():
        if request.method == "GET":
            return get_projects()
        elif request.method == "POST":
            return create_project()

    def get_projects():
        try:
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("page_size", 10, type=int)
            title = request.args.get("title", None)

            user_id = getattr(request, "user_id", None)  # Get user_id from session
            query = Project.query.order_by(Project.id.desc())
            query = query.filter_by(user_id=user_id)
            if title:
                title_filter = f"%{title}%"  # Create a pattern for partial match
                query = query.filter(
                    Project.title.ilike(title_filter)
                )  # Use ilike for case-insensitive match

            pagination = StandardPagesPagination(query, page, per_page)

            project_schema = ProjectSchema(many=True)
            paginated_data = pagination.to_dict(project_schema)

            return jsonify(paginated_data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def create_project():
        try:
            data = request.get_json()
            project_create_schema = ProjectCreateSchema()
            project_data = project_create_schema.load(data)

            user_id = getattr(request, "user_id", None)  # Get user_id from session
            new_project = Project(
                title=project_data["title"],
                description=project_data["description"],
                user_id=user_id,
            )
            db.session.add(new_project)
            db.session.commit()
            project_schema = ProjectSchema()
            return jsonify(project_schema.dump(new_project)), 201
        except ValidationError as err:
            return jsonify({"errors": err.messages}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/contents", methods=["GET", "POST"])
    @login_required
    def contents():
        if request.method == "GET":
            return get_contents()
        elif request.method == "POST":
            return create_contents()

    def get_contents():
        try:
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("page_size", 10, type=int)

            query = Content.query

            project_id = request.args.get(
                "project_id", type=int
            )  # Lấy project_id từ query parameters
            if project_id is not None:
                query = query.filter_by(project_id=project_id)  # Lọc theo project_id

            pagination = StandardPagesPagination(query, page, per_page)
            contents_schema = ContentSchema(many=True)
            paginated_data = pagination.to_dict(contents_schema)

            return jsonify(paginated_data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def create_contents():
        try:
            data = request.get_json()
            content_schema = ContentCreateSchema()
            content_data = content_schema.load(data)
            new_content = Content(
                text=content_data["text"],
                language=content_data["language"],
                text_translate=content_data["text_translate"],
                project_id=content_data["project_id"],
            )
            db.session.add(new_content)
            db.session.commit()
            return jsonify(content_schema.dump(new_content)), 201
        except ValidationError as err:
            return jsonify({"errors": err.messages}), 400
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            lineno = exc_tb.tb_lineno
            file_path = exc_tb.tb_frame.f_code.co_filename
            file_name = os.path.basename(file_path)
            message = f"[{file_name}_{lineno}] {str(e)}"
            return jsonify({"error": str(message)}), 500

    @app.route("/images", methods=["GET", "POST"])
    @login_required
    def images():
        if request.method == "GET":
            return get_images()
        elif request.method == "POST":
            return create_image()

    def get_images():
        try:
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", 10, type=int)
            project_id = request.args.get("project_id", type=int)

            query = Image.query

            if project_id is not None:
                query = query.filter_by(project_id=project_id)

            pagination = StandardPagesPagination(query, page, per_page)

            images_schema = ImageSchema(many=True)
            paginated_data = pagination.to_dict(images_schema)

            return jsonify({"images": paginated_data}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def create_image():
        try:
            files = request.files.getlist("files")  # Lấy danh sách tệp tin từ form
            if not files:
                return jsonify({"error": "No files provided"}), 400

            project_id = request.form.get("project_id")
            if not project_id:
                return jsonify({"error": "project_id is required"}), 400

            image_paths = []
            for file in files:
                if file.filename == "":
                    continue  # Bỏ qua tệp không có tên

                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)
                image_paths.append(file_path)

                # Tạo đối tượng Image cho mỗi tệp tin
                new_image = Image(
                    file_path=file_path,
                    project_id=int(project_id),  # Chuyển đổi project_id thành số nguyên
                )
                db.session.add(new_image)

            db.session.commit()

            # Trả về kết quả
            image_schema = ImageSchema(many=True)
            return (
                jsonify(
                    {
                        "images": image_schema.dump(
                            Image.query.filter(Image.file_path.in_(image_paths)).all()
                        )
                    }
                ),
                201,
            )
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            lineno = exc_tb.tb_lineno
            file_path = exc_tb.tb_frame.f_code.co_filename
            file_name = os.path.basename(file_path)
            message = f"[{file_name}_{lineno}] {str(e)}"
            return jsonify({"error": str(message)}), 500

    @app.route("/upload_images", methods=["POST"])
    @login_required
    def upload_images():
        if "images" not in request.files:
            return jsonify({"error": "No images uploaded"}), 400

        files = request.files.getlist("images")
        project_id = request.form.get("project_id")

        if not project_id:
            return jsonify({"error": "Missing project_id field"}), 400

        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        for file in files:
            if file and allowed_file(file.filename):
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
                    language="",
                    text_translate="",
                )
                db.session.add(new_text)

        db.session.commit()
        return jsonify({"message": "Texts added successfully"}), 200

    @app.route("/language", methods=["GET"])
    @login_required
    def language_list():
        lis_code = []
        for code, language in LANGUAGES.items():
            lis_code.append({"code": code, "language": language})
        return jsonify(lis_code)

    @app.route("/translate", methods=["POST"])
    @login_required
    def translate_text():
        data = request.get_json()
        text = data.get("text", "")
        from_lang = data.get("from")
        target_lang = data.get("lang")
        project_id = data.get("project_id")

        if not target_lang or not project_id:
            return jsonify({"error": "Missing text, lang, or project_id field"}), 400

        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        translator = Translator()
        if text:
            if from_lang:
                translated = translator.translate(text, src=from_lang, dest=target_lang)
            else:
                translated = translator.translate(text, dest=target_lang)

            return jsonify({"translated_text": translated.text})
        else:
            return jsonify({"translated_text": ""})

    @app.route("/text_to_voice", methods=["POST"])
    def text_to_speech():
        try:
            data = request.get_json()
            text = data.get("text")
            lang = data.get("lang")
            # Create voice to translate text
            if not text:
                return jsonify({"text": "", "voice": ""}), 201
            tts = gTTS(text=text, lang=lang)
            audio_file = io.BytesIO()
            tts.write_to_fp(audio_file)
            audio_file.seek(0)  # Reset file pointer to the beginning
            base64_encoded = base64.b64encode(audio_file.read())
            audio_data = base64_encoded.decode("utf-8")
            return (jsonify({"text": text, "voice": audio_data}), 201)
        except Exception as e:
            return (
                (jsonify({"status": False, "message": str(e)})),
                500,
            )

    @app.route("/project_data", methods=["POST"])
    @login_required
    def project_data():
        project_id = request.form.get("project_id")
        contents = request.form.get("contents")
        files = request.files.getlist("images")
        try:
            contents = json.loads(contents)
            for content in contents:
                new_content = Content(
                    project_id=project_id,
                    text=content["text"],
                    lang_from=content["from"],
                    language=content["lang"],
                    text_translate=content["text_translate"],
                )
                db.session.add(new_content)
        except json.JSONDecodeError:
            return jsonify({"status": "error", "message": "Invalid JSON format"}), 400
        list_img = []
        for file in files:
            if file and allowed_file(file.filename):
                file_path = os.path.join(
                    app.config["UPLOAD_FOLDER"], secure_filename(file.filename)
                )
                file.save(file_path)
                new_image = Image(project_id=project_id, file_path=file_path)
                list_img.append(file_path)
                db.session.add(new_image)
        db.session.commit()
        return jsonify(
            {"project_id": project_id, "contents": contents, "images": list_img}
        )

    @app.route("/create_video", methods=["POST"])
    def create_video():
        try:
            files = request.files.getlist("images")
            texts = request.form.getlist("texts")

            voice_type = request.form.getlist("voice_type")

            if (
                not files
                or not texts
                or not texts
                or len(files) != len(texts) != len(voice_type)
            ):
                return (
                    jsonify(
                        {
                            "status": False,
                            "message": "Please provide the same number of images, texts, and texts",
                        }
                    ),
                    400,
                )

            clips = []
            target_size = (1280, 720)  # Kích thước đích (chiều rộng, chiều cao)
            new_uuid = uuid.uuid4()
            for index, file in enumerate(files):
                image_path = os.path.join(TEMP_DIR, f"image_{new_uuid}_{index}.jpg")
                file.save(image_path)
                text = texts[index]

                # Resize image and pad to maintain aspect ratio
                resized_image_path = resize_image(
                    image_path, target_size, index, new_uuid
                )

                # Generate speech from text
                tts = gTTS(text, lang=voice_type[0])
                audio_path = os.path.join(TEMP_DIR, f"voice_{new_uuid}_{index}.mp3")
                tts.save(audio_path)

                # Create audio clip and get its duration
                audio_clip = AudioFileClip(audio_path)
                audio_duration = audio_clip.duration

                # Create image clip with the same duration as the audio
                image_clip = ImageClip(resized_image_path, duration=audio_duration)

                # # Create text clip with the same duration as the audio
                # text_clip = TextClip(
                #     text,
                #     fontsize=20,
                #     color="white",
                #     size=image_clip.size,
                #     method="caption",
                # )
                # text_clip = text_clip.set_duration(audio_duration)

                # # Position the text at the bottom center
                # text_position = (
                #     "center",
                #     target_size[1] - text_clip.size[1] - 10,
                # )  # 10 là khoảng cách từ dưới lên
                # text_clip = text_clip.set_position(text_position)

                # Combine image and text
                # video = CompositeVideoClip([image_clip, text_clip])
                video = CompositeVideoClip([image_clip])

                # Set audio to video
                video = video.set_audio(audio_clip)

                clips.append(video)

            # Concatenate all clips
            final_video = concatenate_videoclips(clips)

            output_path = os.path.join(TEMP_DIR, f"{new_uuid}.mp4")
            final_video.write_videofile(output_path, fps=24)

            # Clean up temporary audio and image files
            for index in range(len(files)):
                os.remove(os.path.join(TEMP_DIR, f"voice_{new_uuid}_{index}.mp3"))
                os.remove(os.path.join(TEMP_DIR, f"image_{new_uuid}_{index}.jpg"))
                os.remove(
                    os.path.join(TEMP_DIR, f"resized_image_{new_uuid}_{index}.jpg")
                )

            # Return video file for download
            return send_file(output_path, as_attachment=True)

        except Exception as e:
            logger.error(f"Error creating video: {str(e)}")
            return (
                jsonify(
                    {"status": False, "message": f"Error creating video: {str(e)}"}
                ),
                500,
            )
