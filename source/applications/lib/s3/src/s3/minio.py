from pydantic import BaseModel, Field
from opentelemetry import trace
from core.result import Result
from io import BytesIO
from domain.storage.interface import FileStorage
from domain.storage.model import FileStorageObject, FileStorageObjectMetadata
from minio import Minio, S3Error
import logging

logger = logging.getLogger(__name__)


class MinioFileStorageConfig(BaseModel):
    host: str
    access_key: str | None = Field(description="access key or username")
    secret_key: str | None = Field(description="access key or password")
    sesssion_token: str | None = Field(description="session token for account")
    secure: bool = Field(description="does the connection use TLS?", default=False)


class MinioConnection:
    """
    Manage Minio connections per host (multiton pattern).
    """

    _instances: dict[str, "MinioConnection"] = {}

    def __init__(self, config: "MinioFileStorageConfig"):
        self._client = Minio(
            endpoint=config.host,
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.secure,
            session_token=config.sesssion_token,
        )

    @classmethod
    def init_connection(cls, config: "MinioFileStorageConfig"):
        """Initialize and store connection per host."""
        if config.host not in cls._instances:
            logger.info(f"MinIO added Connection {config.host}")
            cls._instances[config.host] = cls(config)
        else:
            logger.info(f"MinIO Connection {config.host} does already exist")

    @classmethod
    def get_instance(cls, host: str) -> Minio:
        """Retrieve Minio client for a specific host."""
        if host not in cls._instances:
            raise ValueError(
                f"MinioConnection for host '{host}' is not initialized. Call init_connection first."
            )
        return cls._instances[host]._client


class MinioFileStorage(FileStorage):
    """
    Implementation of FileStorage using Minio
    """

    prefix_meta_data: str = "x-amz-meta-"
    __minio: Minio
    __config: MinioFileStorageConfig
    tracer: trace.Tracer

    def __init__(self, minio: Minio):
        self.__minio = minio
        self.tracer = trace.get_tracer("MinioFileStorage")

    def fetch_file(
        self, filename: str, bucket: str
    ) -> Result[FileStorageObject | None]:
        with self.tracer.start_as_current_span("fetch-file"):
            try:
                bucket_name = self._create_valid_bucket_name(bucket)
                if not self.__minio.bucket_exists(bucket_name):
                    return Result.Ok(None)

                obj = self.__minio.get_object(
                    bucket_name=bucket_name, object_name=filename
                )
                content = obj.read()
                metadata = obj.headers

                metadata_obj = FileStorageObjectMetadata(version=0, db_id="")
                metadata_obj_dump = metadata_obj.model_dump()
                for key in metadata_obj_dump.keys():
                    minio_metadata_key = f"{self.prefix_meta_data}{key}"
                    value = metadata.get(minio_metadata_key)
                    if value is None:
                        logger.warning(
                            f"Minio Object {filename} in Bucket: {bucket_name} does not contain metadata {minio_metadata_key}"
                        )
                        continue
                    metadata_obj_dump[key] = value

                metadata_obj = FileStorageObjectMetadata(**metadata_obj_dump)

                size_bytes = len(content)
                size_mb = size_bytes / (1024 * 1024)
                logger.info(f"downloaded file:{filename} with {size_mb} MB")
                # Reconstruct the FileStorageObject
                file = FileStorageObject(
                    filename=filename,
                    content=content,
                    bucket=bucket_name,
                    filetype=metadata.get("Content-Type")
                    or "UNKNOWN",  # Extract file type from metadata
                    metadata=metadata_obj,
                )

                return Result.Ok(file)
            except Exception as e:
                return Result.Err(e)

    def _create_valid_bucket_name(self, bucket: str) -> str:
        valid_bucket_name = (
            bucket.replace(" ", "").replace("-", "").replace("_", "").lower()
        )
        logger.debug(f"converted {bucket} to {valid_bucket_name}")
        return valid_bucket_name

    def does_file_exist(self, filename: str, bucket: str) -> Result[bool]:
        with self.tracer.start_as_current_span("check-file-existens"):
            try:
                bucket_name = self._create_valid_bucket_name(bucket)
                if not self.__minio.bucket_exists(bucket_name):
                    logger.info(f"Bucket {bucket_name} does not exist")
                    return Result.Ok(False)
                self.__minio.stat_object(bucket_name, filename)
                return Result.Ok(True)
            except S3Error as e:
                if e.code == "NoSuchKey":
                    return Result.Ok(False)
                return Result.Err(e)
            except Exception as e:
                return Result.Err(e)

    def get_file_info(
        self, filename: str, bucket: str
    ) -> Result[FileStorageObjectMetadata | None]:
        with self.tracer.start_as_current_span("fetch-file-info"):
            try:
                bucket_name = self._create_valid_bucket_name(bucket)
                if not self.__minio.bucket_exists(bucket_name):
                    logger.info(f"Bucket {bucket_name} does not exist")
                    return Result.Ok(None)
                obj = self.__minio.stat_object(bucket_name, filename)

                assert obj.metadata is not None
                metadata: dict[str, str] = obj.metadata

                metadata_obj = FileStorageObjectMetadata(version=0, db_id="")
                metadata_obj_dump = metadata_obj.model_dump()
                for key in metadata_obj_dump.keys():
                    minio_metadata_key = f"{self.prefix_meta_data}{key}"
                    value = metadata.get(minio_metadata_key)
                    if value is None:
                        logger.warning(
                            f"Minio Object {filename} in Bucket: {bucket_name} does not contain metadata {minio_metadata_key}"
                        )
                        continue
                    metadata_obj_dump[key] = value

                metadata_obj = FileStorageObjectMetadata(**metadata_obj_dump)
                return Result.Ok(metadata_obj)
            except S3Error as e:
                if e.code == "NoSuchKey":
                    return Result.Ok(None)
                return Result.Err(e)
            except Exception as e:
                return Result.Err(e)

    def upload_file(self, file: FileStorageObject) -> Result[None]:
        data = BytesIO(file.content)
        size_bytes = len(data.getbuffer())
        size_mb = size_bytes / (1024 * 1024)
        with self.tracer.start_as_current_span("upload-file"):
            logger.info(f"upload file:{file.filename} with {size_mb} MB")
            try:
                bucket_name = self._create_valid_bucket_name(file.bucket)
                if not self.__minio.bucket_exists(bucket_name):
                    self.__minio.make_bucket(bucket_name)
                self.__minio.put_object(
                    bucket_name=bucket_name,
                    object_name=file.filename,
                    data=data,
                    length=len(data.getvalue()),
                    metadata=file.metadata.model_dump(),
                    content_type=file.filetype,
                )
                return Result.Ok()
            except Exception as e:
                return Result.Err(e)
