from app import db
from datetime import datetime


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Add this line
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    projects = db.relationship(
        "Project", backref=db.backref("user", lazy=True), cascade="all, delete-orphan"
    )


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=True)
    lang = db.Column(db.String(100), nullable=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", name="fk_user"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # contents = db.relationship(
    #     "Content",
    #     backref=db.backref("project", lazy=True),
    #     cascade="all, delete-orphan",
    # )
    images = db.relationship(
        "Images", backref=db.backref("project", lazy=True), cascade="all, delete-orphan"
    )
    images64 = db.relationship(
        "Images64", backref=db.backref("project", lazy=True), cascade="all, delete-orphan"
    )
    History = db.relationship(
        "Project_his", backref=db.backref("project", lazy=True), cascade="all, delete-orphan"
    )

    class Meta:
        ordering = ["-id"]


class Project_his(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=True)
    column = db.Column(db.String(100), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    data_type = db.Column(db.String(100), nullable=True)
    data = db.Column(db.Text, nullable=True)
    old_data = db.Column(db.Text, nullable=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("project.id", name="fk_project_image64"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=True)
    lang_from = db.Column(db.String(10), nullable=True)
    language = db.Column(db.String(10), nullable=True)
    text_translate = db.Column(db.Text, nullable=True)
    audio64 = db.Column(db.Text, nullable=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("project.id", name="fk_project"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Images(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(200), nullable=False)
    project_id = db.Column(
        db.Integer, db.ForeignKey("project.id", name="fk_project_image"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

class Images64(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    img_data = db.Column(db.Text, nullable=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("project.id", name="fk_project_image64"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
