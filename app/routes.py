from flask import request, jsonify, send_from_directory, session, url_for
import jwt
import datetime
import os, sys
from werkzeug.utils import secure_filename
from googletrans import Translator, LANGUAGES
from gtts import gTTS
import moviepy.editor as mp
from .models import *
from . import db
from .utils import *
from .serializers import *
from marshmallow import ValidationError

def init_app(app):
    # @app.after_request
    # def after_request(response):
    #     response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4443')
    #     response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    #     response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    #     response.headers.add('Access-Control-Allow-Credentials', 'true')
    #     return response

    @app.route('/')
    def index():
        return "API is running!"

    @app.route('/register', methods=['POST'])
    def register():
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

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
        print(f"{jwt_token.get("token")}")

        return jsonify(response_data), 200

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        session.pop('user_id', None)
        return jsonify({"message": "Logged out successfully"}), 200

    @app.route('/user', methods=['GET'])
    @login_required
    def get_user():
        user_id = getattr(request, 'user_id', None)  # Assumes user ID is stored in the session
        if not user_id:
            return jsonify({"error": "User ID not found in session"}), 401
        print(f"{user_id}")
        user = User.query.get_or_404(user_id)
        user_schema = UserSchema()
        return jsonify(user_schema.dump(user))

    @app.route('/projects/<int:project_id>', methods=['GET','DELETE'])
    @login_required
    def project_details(project_id):
        if request.method == 'GET':
            return get_project_details(project_id)
        elif request.method == 'DELETE':
            return delete_project(project_id)
    def get_project_details(project_id):
        try:
            user_id = getattr(request, 'user_id', None)  # Get user_id from session
            project = Project.query.filter_by(id=project_id, user_id=user_id).first()
            
            if not project:
                return jsonify({'error': 'Project not found'}), 404

            project_schema = ProjectDetailsSchema()
            project_data = project_schema.dump(project)
            
            return jsonify(project_data), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    def delete_project(project_id):
            try:
                if not project_id:
                    return jsonify({'error': 'No project ID provided'}), 400

                user_id = getattr(request, 'user_id', None)  # Get user_id from session
                project = Project.query.filter_by(id=project_id, user_id=user_id).first()

                if not project:
                    return jsonify({'error': 'Project not found or you do not have permission to delete it'}), 404

                db.session.delete(project)
                db.session.commit()

                return jsonify({'message': 'Project deleted successfully'}), 200
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    @app.route('/projects', methods=['GET','POST'])
    @login_required
    def projects():
        if request.method == 'GET':
            return get_projects()
        elif request.method == 'POST':
            return create_project()
    def get_projects():
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('page_size', 10, type=int)
            title = request.args.get('title', None)
            
            user_id = getattr(request, 'user_id', None)  # Get user_id from session
            query = Project.query.order_by(Project.id.desc())
            query = query.filter_by(user_id=user_id)
            if title:
                title_filter = f"%{title}%"  # Create a pattern for partial match
                query = query.filter(Project.title.ilike(title_filter))  # Use ilike for case-insensitive match

            pagination = StandardPagesPagination(query, page, per_page)
            
            project_schema = ProjectSchema(many=True)
            paginated_data = pagination.to_dict(project_schema)

            return jsonify(paginated_data), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    def create_project():
        try:
            data = request.get_json()
            project_create_schema = ProjectCreateSchema()
            project_data = project_create_schema.load(data)

            user_id = getattr(request, 'user_id', None)  # Get user_id from session
            new_project = Project(
                title=project_data['title'],
                description=project_data['description'],
                user_id=user_id
            )
            db.session.add(new_project)
            db.session.commit()
            project_schema = ProjectSchema()
            return jsonify(project_schema.dump(new_project)), 201
        except ValidationError as err:
            return jsonify({'errors': err.messages}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/contents', methods=['GET','POST'])
    @login_required
    def contents():
        if request.method == 'GET':
            return get_contents()
        elif request.method == 'POST':
            return create_contents()
    def get_contents():
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('page_size', 10, type=int)
            
            query = Content.query

            project_id = request.args.get('project_id', type=int)  # Lấy project_id từ query parameters
            if project_id is not None:
                query = query.filter_by(project_id=project_id)  # Lọc theo project_id
            
            pagination = StandardPagesPagination(query, page, per_page)
            contents_schema = ContentSchema(many=True)
            paginated_data = pagination.to_dict(contents_schema)

            return jsonify(paginated_data), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    def create_contents():
        try:
            data = request.get_json()
            content_schema = ContentCreateSchema()
            content_data = content_schema.load(data)
            new_content = Content(
                text=content_data['text'],
                language=content_data['language'],
                text_translate=content_data['text_translate'],
                project_id=content_data['project_id']
            )
            db.session.add(new_content)
            db.session.commit()
            return jsonify(content_schema.dump(new_content)), 201
        except ValidationError as err:
            return jsonify({'errors': err.messages}), 400
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            lineno = exc_tb.tb_lineno
            file_path = exc_tb.tb_frame.f_code.co_filename
            file_name = os.path.basename(file_path)
            message = f"[{file_name}_{lineno}] {str(e)}"
            return jsonify({'error': str(message)}), 500

    @app.route('/images', methods=['GET', 'POST'])
    @login_required
    def images():
        if request.method == 'GET':
            return get_images()
        elif request.method == 'POST':
            return create_image()

    def get_images():
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            project_id = request.args.get('project_id', type=int)
            
            query = Image.query
            
            if project_id is not None:
                query = query.filter_by(project_id=project_id)
            
            pagination = StandardPagesPagination(query, page, per_page)
            
            images_schema = ImageSchema(many=True)
            paginated_data = pagination.to_dict(images_schema)
            
            return jsonify({'images': paginated_data}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    def create_image():
        try:
            files = request.files.getlist('files')  # Lấy danh sách tệp tin từ form
            if not files:
                return jsonify({'error': 'No files provided'}), 400

            project_id = request.form.get('project_id')
            if not project_id:
                return jsonify({'error': 'project_id is required'}), 400

            image_paths = []
            for file in files:
                if file.filename == '':
                    continue  # Bỏ qua tệp không có tên

                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_paths.append(file_path)

                # Tạo đối tượng Image cho mỗi tệp tin
                new_image = Image(
                    file_path=file_path,
                    project_id=int(project_id)  # Chuyển đổi project_id thành số nguyên
                )
                db.session.add(new_image)
            
            db.session.commit()

            # Trả về kết quả
            image_schema = ImageSchema(many=True)
            return jsonify({'images': image_schema.dump(Image.query.filter(Image.file_path.in_(image_paths)).all())}), 201
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            lineno = exc_tb.tb_lineno
            file_path = exc_tb.tb_frame.f_code.co_filename
            file_name = os.path.basename(file_path)
            message = f"[{file_name}_{lineno}] {str(e)}"
            return jsonify({'error': str(message)}), 500

    @app.route('/upload_images', methods=['POST'])
    @login_required
    def upload_images():
        if 'images' not in request.files:
            return jsonify({'error': 'No images uploaded'}), 400

        files = request.files.getlist('images')
        project_id = request.form.get('project_id')

        if not project_id:
            return jsonify({'error': 'Missing project_id field'}), 400

        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        for file in files:
            if file and allowed_file(file.filename):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
                file.save(file_path)
                new_image = Image(project_id=project_id, file_path=file_path)
                db.session.add(new_image)

        db.session.commit()
        return jsonify({'message': 'Images uploaded successfully'}), 200

    @app.route('/add_text', methods=['POST'])
    @login_required
    def add_text():
        data = request.get_json()
        texts = data.get('texts')
        project_id = data.get('project_id')

        if not project_id:
            return jsonify({'error': 'Missing project_id field'}), 400
        if not texts:
            return jsonify({'error': 'No texts provided'}), 400

        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        for text in texts:
            if text.strip():
                content = Content.query.filter_by(project_id=project_id, text=text.strip()).first()
                if content:
                    return jsonify({'error': 'Duplicate text entry'}), 400
                new_text = Content(
                    project_id=project_id,
                    text=text.strip(),
                    language='',
                    text_translate='',
                )
                db.session.add(new_text)

        db.session.commit()
        return jsonify({'message': 'Texts added successfully'}), 200

    @app.route('/language', methods=['GET'])
    @login_required
    def language_list():
        lis_code=[]
        for code, language in LANGUAGES.items():
            lis_code.append({'code': code, 'language': language})
        return jsonify(lis_code)

    @app.route('/translate', methods=['POST'])
    @login_required
    def translate_text():
        data = request.get_json()
        text = data.get('text')
        from_lang = data.get('from')
        target_lang = data.get('lang')
        project_id = data.get('project_id')

        if not text or not target_lang or not project_id:
            return jsonify({'error': 'Missing text, lang, or project_id field'}), 400

        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        translator = Translator()
        if from_lang:
            translated = translator.translate(text, src=from_lang, dest=target_lang)
        else:
            translated = translator.translate(text, dest=target_lang)

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
        return jsonify({'translated_text': translated.text})

    @app.route('/text_to_speech', methods=['POST'])
    @login_required
    def text_to_speech():
        data = request.get_json()
       
