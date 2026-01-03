from core.config_loader import ConfigLoaderImplementation
from domain.database.file.model import File, FragementTypes
from domain.pipeline.events import EventName
from image_description_service.usecase.image_description import DescribeImageUsecase
from prefect import logging, task
from prefect.events import emit_event

from file_converter_pipline_service.usecase.file_converte import ConvertFileUsecase

from file_converter_prefect.application_startup import ApplicationFileConverterPrefect
from file_converter_prefect.settings import ENABLED_IMAGE_DESCRIPTION


@task
async def convert_file(file_id: str) -> File:
    result = await ConvertFileUsecase.Instance().convert_file(file_id=file_id)
    logger = logging.get_run_logger()
    if result.is_error():
        logger.error(f"{result.get_error()}")
        raise result.get_error()
    file = result.get_ok()
    return file


@task
async def describe_image(file: File):
    logger = logging.get_run_logger()
    bucket = file.metadata.project_id

    for page in file.pages:
        for index, fragement in enumerate(page.fragements):
            if fragement.fragement_type != FragementTypes.IMAGE:
                continue
            context_files: list[str] = []

            for i in range(index, len(page.fragements)):
                if page.fragements[i].fragement_type == FragementTypes.TEXT:
                    context_files.append(page.fragements[i].storage_filename)
                    break

            for i in range(0, index + 1, -1):  # count in reverse
                if page.fragements[i].fragement_type == FragementTypes.TEXT:
                    context_files.append(page.fragements[i].storage_filename)
                    break

            logger.info(f"describe {fragement.storage_filename}")
            result = await DescribeImageUsecase.Instance().describe_image(
                bucket=bucket,
                filename=fragement.storage_filename,
                context_files=context_files,
            )
            if result.is_error():
                raise result.get_error()


@task
async def startup():
    ApplicationFileConverterPrefect.create(ConfigLoaderImplementation.create())
    ApplicationFileConverterPrefect.Instance().start()
    await ApplicationFileConverterPrefect.Instance().astart()
    await ApplicationFileConverterPrefect.Instance().create_usecase()


async def shutdown():
    await ApplicationFileConverterPrefect.Instance().ashutdown()
    ApplicationFileConverterPrefect.Instance().shutdown()


async def created_or_updated_file(file_id: str):
    try:
        await startup()
        file = await convert_file(file_id=file_id)

        if ConfigLoaderImplementation.Instance().get_bool(ENABLED_IMAGE_DESCRIPTION):
            await describe_image(file=file)

        emit_event(
            event=EventName.FILE_CONVERTED.value,
            resource={"prefect.resource.id": f"file/{file_id}"},
        )
    finally:
        await shutdown()
