from core.config_loader import ConfigLoaderImplementation
from file_uploader_service.usecase.upload_files import UploadeFilesUsecase
from domain.pipeline.events import EventName
from prefect import task
import logging

from file_uploader_prefect.application_startup import FileUploaderPrefect
from prefect.events import emit_event

logger = logging.getLogger(__name__)


@task
def load_file() -> list[str]:
    return UploadeFilesUsecase.Instance().get_all_files_from_root_dir()


@task
async def should_file_be_uploaded(file: str) -> bool:
    result = await UploadeFilesUsecase.Instance().should_file_be_uploaded(filepath=file)
    if result.is_error():
        logger.error(result.get_error())
        return False
    return result.get_ok()[0]


@task
async def upload_file(filepath: str):
    result = await UploadeFilesUsecase.Instance().upload_file(filepath=filepath)
    if result.is_error():
        logger.error(result.get_error())
        return
    logger.info(f"Uploaded {filepath}")
    db_id = result.get_ok()

    emit_event(
        event=EventName.FILE_CREATED_UPDATES.value,
        resource={"prefect.resource.id": f"file/{db_id}"},
    )
    logger.info(f"Emitted file ID {db_id}")


@task
async def startup():
    FileUploaderPrefect.create(config_loader=ConfigLoaderImplementation.create())
    FileUploaderPrefect.Instance().start()
    await FileUploaderPrefect.Instance().astart()
    await FileUploaderPrefect.Instance().create_usecase()


async def shutdown():
    await FileUploaderPrefect.Instance().ashutdown()
    FileUploaderPrefect.Instance().shutdown()


async def upload_files():
    try:
        await startup()
        filepaths = load_file()
        logger.info(f"found {len(filepaths)} Files")
        for filepath in filepaths:
            await upload_file(filepath=filepath)
    finally:
        await shutdown()
