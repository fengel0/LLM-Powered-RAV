from typing import runtime_checkable
from core.result import Result

from domain.database import BaseDatabase
from domain.database.project.model import Coordinates, Project


class ProjectDatabase(BaseDatabase[Project]):

    """
    Project database interface.
    Original designed for Projekts of the museum in weimar
    but is more or less obenden for project/dataset handling for rag evaluation
    """


    async def fetch_by_name(self, name: str) -> Result[Project | None]: ...

    async def fetch_by_year(self, year: int) -> Result[list[Project]]: ...

    async def fetch_by_country(self, country: str) -> Result[list[Project]]: ...

    async def fetch_by_state(self, state: str) -> Result[list[Project]]: ...

    async def fetch_by_coordinates(
        self, coordinates: Coordinates, radius_in_meter: float
    ) -> Result[list[Project]]: ...

    async def search_by_name(self, name: str) -> Result[list[Project]]: ...

    async def search_by_country(self, country: str) -> Result[list[Project]]: ...

    async def search_by_state(self, state: str) -> Result[list[Project]]: ...
