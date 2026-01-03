import logging
import math
from uuid import UUID
from opentelemetry import trace
from core.result import Result
from domain.database.project.interface import ProjectDatabase
from domain.database.project.model import Address, Coordinates, Project

from database.session import BaseDatabase
from project_database.model import (
    Project as ProjectDB,
)

logger = logging.getLogger(__name__)


class _PostgreDB(BaseDatabase[ProjectDB]):
    def __init__(
        self,
    ):
        super().__init__(ProjectDB)


class PostgresDBProjectDatbase(ProjectDatabase):
    _db: _PostgreDB
    tracer: trace.Tracer

    def __init__(self) -> None:
        super().__init__()
        self._db = _PostgreDB()
        self.tracer = trace.get_tracer("ProjectMongoDatabase")

    async def create(self, obj: Project) -> Result[str]:
        return await self._db.create(pydantic_to_orm(obj))

    async def update(self, obj: Project) -> Result[None]:
        return await self._db.update(pydantic_to_orm(obj))

    async def delete(self, id: str) -> Result[None]:
        return await self._db.delete(id=id)

    async def get(self, id: str) -> Result[Project | None]:
        result = await self._db.get(id=id)
        if result.is_error():
            return result.propagate_exception()
        obj = result.get_ok()
        if obj:
            return Result.Ok(orm_to_pydantic(obj))

        return Result.Ok(None)

    async def get_all(self) -> Result[list[Project]]:
        result = await self._db.get_all()
        if result.is_error():
            return result.propagate_exception()
        objs = result.get_ok()
        return Result.Ok([orm_to_pydantic(obj) for obj in objs])

    async def fetch_by_name(self, name: str) -> Result[Project | None]:
        with self.tracer.start_as_current_span("fetch-by-name"):
            query = {"name": name}
            result = await self._db.run_query(query)
            if result.is_error():
                return result.propagate_exception()
            objs = result.get_ok()
            return Result.Ok(orm_to_pydantic(objs[0]) if objs else None)

    async def fetch_by_year(self, year: int) -> Result[list[Project]]:
        with self.tracer.start_as_current_span("fetch-by-year"):
            query = {"year": year}
            result = await self._db.run_query(query)
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok([orm_to_pydantic(obj) for obj in result.get_ok()])

    async def fetch_by_country(self, country: str) -> Result[list[Project]]:
        with self.tracer.start_as_current_span("fetch-by-country"):
            query = {"address__country": country}
            result = await self._db.run_query(query)
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok([orm_to_pydantic(obj) for obj in result.get_ok()])

    async def fetch_by_state(self, state: str) -> Result[list[Project]]:
        with self.tracer.start_as_current_span("fetch-by-state"):
            query = {"address__state": state}
            result = await self._db.run_query(query)
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok([orm_to_pydantic(obj) for obj in result.get_ok()])

    async def fetch_by_coordinates(
        self, coordinates: Coordinates, radius_in_meter: float
    ) -> Result[list[Project]]:
        # Convert meter to radians (earth radius approx 6371000m)
        with self.tracer.start_as_current_span("fetch-by-coordinates"):
            try:
                projects = await self._db.get_all()
                if projects.is_error():
                    return projects.propagate_exception()

                matches: list[ProjectDB] = []
                for obj in projects.get_ok():
                    # Skip if coordinates are missing
                    dist = haversine(
                        lat1=coordinates.lat,
                        lon1=coordinates.long,
                        lat2=obj.address__lat,
                        lon2=obj.address__long,
                    )

                    if dist <= radius_in_meter:
                        matches.append(obj)

                return Result.Ok([orm_to_pydantic(p) for p in matches])
            except Exception as e:
                logger.error(e, exc_info=True)
                return Result.Err(e)

    async def search_by_name(self, name: str) -> Result[list[Project]]:
        with self.tracer.start_as_current_span("search-by-name"):
            query = {"name__icontains": name}
            result = await self._db.run_query(query)
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok([orm_to_pydantic(obj) for obj in result.get_ok()])

    async def search_by_country(self, country: str) -> Result[list[Project]]:
        with self.tracer.start_as_current_span("search-by-country"):
            query = {"address__country__icontains": country}
            result = await self._db.run_query(query)
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok([orm_to_pydantic(obj) for obj in result.get_ok()])

    async def search_by_state(self, state: str) -> Result[list[Project]]:
        with self.tracer.start_as_current_span("search-by-state"):
            query = {"address__state__icontains": state}
            result = await self._db.run_query(query)
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok([orm_to_pydantic(obj) for obj in result.get_ok()])


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points (in meters)
    on the Earth specified in decimal degrees.
    """
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def pydantic_to_orm(p: Project) -> ProjectDB:
    """
    Maps Pydantic Project → ORM Project (Tortoise model)
    """
    orm = ProjectDB(
        version=p.version,
        name=p.name,
        year=p.year,
    )
    try:
        id = UUID(p.id)
        orm.id = id
    except Exception:
        ...

    if p.address is not None:
        orm.address__country = p.address.country
        orm.address__state = p.address.state
        orm.address__county = p.address.county
        orm.address__city = p.address.city
        orm.address__street = p.address.street or ""
        orm.address__zip_code = p.address.zip_code
        orm.address__lat = p.address.coordinates.lat
        orm.address__long = p.address.coordinates.long
    else:
        orm.address__country = ""
        orm.address__state = ""
        orm.address__county = ""
        orm.address__city = ""
        orm.address__street = ""
        orm.address__zip_code = ""
        orm.address__lat = 0.0
        orm.address__long = 0.0

    return orm


def orm_to_pydantic(orm: ProjectDB) -> Project:
    """
    Maps ORM Project → Pydantic Project
    """
    if orm.address__country != "":
        address = Address(
            country=orm.address__country,
            state=orm.address__state,
            county=orm.address__county,
            city=orm.address__city,
            street=orm.address__street,
            zip_code=orm.address__zip_code,
            coordinates=Coordinates(
                lat=orm.address__lat or 0.0,
                long=orm.address__long or 0.0,
            ),
        )
    else:
        address = None

    return Project(
        id=str(orm.id),
        version=orm.version,
        name=orm.name,
        year=orm.year,
        address=address,
    )
