from typing import Any, Literal
from tortoise.contrib.postgres.indexes import GinIndex
from database.session import DatabaseBaseModel
from tortoise import fields


FragementTypes = Literal["text", "image", "tabel"]


class PageFragement(DatabaseBaseModel):
    page = fields.ForeignKeyField("models.FilePage", related_name="fragments")  # type: ignore
    fragement_type = fields.CharField(max_length=16)
    storage_filename = fields.CharField(max_length=256)
    fragement_number = fields.IntField()


class FilePage(DatabaseBaseModel):
    file = fields.ForeignKeyField("models.File", related_name="pages")  # type: ignore
    bucket = fields.CharField(max_length=256)
    page_number = fields.IntField()
    metadata__project_id = fields.CharField(max_length=256)
    metadata__project_year = fields.IntField()
    metadata__file_creation = fields.DatetimeField()
    metadata__file_updated = fields.DatetimeField()
    metadata__version = fields.IntField()
    fragments: fields.ReverseRelation["PageFragement"]


class File(DatabaseBaseModel):
    filepath = fields.CharField(max_length=256)
    filename = fields.CharField(max_length=256)
    bucket = fields.CharField(max_length=256)
    metadata_project_id = fields.CharField(max_length=256)
    metadata_project_year = fields.IntField()
    metadata_file_creation = fields.DatetimeField()
    metadata_file_updated = fields.DatetimeField()
    metadata_version = fields.IntField()
    metatdata_other = fields.JSONField[dict[str, str]]()

    pages: fields.ReverseRelation["FilePage"]

    class Meta:
        indexes = [GinIndex(fields=["metatdata_other"])]
