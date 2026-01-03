from tortoise import fields
from database.session import DatabaseBaseModel


class Facts(DatabaseBaseModel):
    hash = fields.CharField(max_length=255, index=True)
    facts = fields.JSONField[list[str]]()
