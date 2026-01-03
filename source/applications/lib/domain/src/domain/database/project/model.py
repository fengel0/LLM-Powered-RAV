from pydantic import BaseModel


class Coordinates(BaseModel):
    lat: float = 0.0
    long: float = 0.0


class Address(BaseModel):
    country: str  # Land
    state: str  # Bundesland
    county: str  # Landkreis
    city: str  # Ort/Stadt
    street: str | None
    coordinates: Coordinates
    zip_code: str


class Project(BaseModel):
    id: str
    version: int
    name: str
    year: int
    address: Address | None
