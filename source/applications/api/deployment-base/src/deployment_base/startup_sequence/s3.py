from core.config_loader import ConfigLoader
from deployment_base.enviroment import minio_env

from deployment_base.application import AsyncLifetimeReg


class MinioStartupSequence(AsyncLifetimeReg):
    def __init__(self) -> None:
        super().__init__()

    async def start(self, config_loader: ConfigLoader):
        result = config_loader.load_values(minio_env.SETTINGS)
        if result.is_error():
            raise result.get_error()
        from s3.minio import MinioConnection, MinioFileStorageConfig

        minio_config = MinioFileStorageConfig(
            host=config_loader.get_str(minio_env.S3_HOST),
            access_key=config_loader.get_str(minio_env.S3_ACCESS_KEY),
            secret_key=config_loader.get_str(minio_env.S3_SECRET_KEY),
            sesssion_token=config_loader.get_str(minio_env.S3_SESSION_KEY),
            secure=config_loader.get_bool(minio_env.S3_IS_SECURE),
        )
        MinioConnection.init_connection(config=minio_config)

    async def shutdown(self):
        return
