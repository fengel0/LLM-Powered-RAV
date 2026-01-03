# app/database/models.py
from tortoise import fields
from database.session import (
    DatabaseBaseModel,
)  # your custom base (inherits tortoise.models.Model)


class Project(DatabaseBaseModel):
    version = fields.IntField()
    name = fields.CharField(max_length=255)
    year = fields.IntField()
    address__country = fields.CharField(max_length=64, null=True)  # Land
    address__state = fields.CharField(max_length=64, null=True)  # Bundesland
    address__county = fields.CharField(max_length=64, null=True)  # Landkreis
    address__city = fields.CharField(max_length=64, null=True)  # Ort/Stadt
    address__street = fields.CharField(max_length=128, null=True)
    address__zip_code = fields.CharField(max_length=16, null=True)
    address__lat = fields.FloatField(null=True)
    address__long = fields.FloatField(null=True)
