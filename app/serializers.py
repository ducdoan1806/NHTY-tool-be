from marshmallow import (
    Schema,
    fields,
    post_load,
    validates,
    ValidationError,
    post_dump,
    pre_dump,
)
from app import db
from app.models import User, Project, Content, Images
import pytz
from datetime import datetime


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    email = fields.Str(required=True)
    password = fields.Str(load_only=True, required=True)
    is_admin = fields.Bool()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_user(self, data, **kwargs):
        return User(**data)


class UserLTESchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    email = fields.Str(required=True)


class UserListSchema(Schema):
    users = fields.List(fields.Nested(UserSchema))


class ProjectSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True)
    description = fields.Str()
    content = fields.Str(required=True)
    lang = fields.Str(required=True)
    user = fields.Nested(UserLTESchema, dump_only=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    class Meta:
        fields = (
            "id",
            "title",
            "description",
            "user",
            "created_at",
            "updated_at",
            "content",
            "lang",
        )


class Image64LTESchema(Schema):
    id = fields.Int(dump_only=True)
    img_data = fields.Str(required=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

class ImageLTESchema(Schema):
    id = fields.Int(dump_only=True)
    file_path = fields.Str(required=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class ContentLTESchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(required=True)
    language = fields.Str(required=True)
    text_translate = fields.Str(required=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

class Project_hisSchema(Schema):
    action = fields.Str(required=True)
    column = fields.Str(required=True)
    comment = fields.Str(required=True)
    data_type = fields.Str(required=True)
    data = fields.Str(required=True)
    old_data = fields.Str(required=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

class ProjectDetailsSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True)
    description = fields.Str()
    user = fields.Nested(UserLTESchema, dump_only=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    images = fields.List(fields.Nested(ImageLTESchema), dump_only=True)
    images64 = fields.List(fields.Nested(Image64LTESchema), dump_only=True)
    History = fields.List(fields.Nested(Project_hisSchema), dump_only=True)
    content = fields.Str(required=True)
    lang = fields.Str(required=True)

    @pre_dump
    def sort_contents(self, project, **kwargs):
        project.images = sorted(project.images, key=lambda x: x.id, reverse=True)
        return project


class ProjectCreateSchema(Schema):
    title = fields.String(
        required=True, validate=lambda x: len(x) > 0 and len(x) <= 100
    )
    description = fields.String(required=True)
    content = fields.String(required=True)
    lang = fields.String(required=True)


class ContentSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(required=True)
    language = fields.Str(required=True)
    text_translate = fields.Str(required=True)
    project_id = fields.Int(required=True)
    project = fields.Nested(ProjectCreateSchema, dump_only=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_content(self, data, **kwargs):
        return Content(**data)

    class Meta:
        fields = (
            "id",
            "project_id",
            "text",
            "language",
            "text_translate",
            "audio64",
            "created_at",
            "updated_at",
        )


class ContentCreateSchema(Schema):
    text = fields.Str(required=True)
    language = fields.Str(required=True)
    text_translate = fields.Str(required=True)
    project_id = fields.Int(required=True)


class ImageSchema(Schema):
    id = fields.Int(dump_only=True)
    file_path = fields.Str(required=True)
    project_id = fields.Int(required=True)
    project = fields.Nested(ProjectSchema, dump_only=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_image(self, data, **kwargs):
        return Images(**data)

    class Meta:
        fields = ("id", "file_path", "project_id", "created_at", "updated_at")


class ImageCreateSchema(Schema):
    file_path = fields.Str(required=True)  # Đảm bảo rằng đường dẫn tệp tin là bắt buộc
    project_id = fields.Int(required=True)  # Đảm bảo rằng project_id là bắt buộc
