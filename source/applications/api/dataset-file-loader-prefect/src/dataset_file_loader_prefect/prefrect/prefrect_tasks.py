from core.config_loader import ConfigLoaderImplementation
from dataset_file_loader_prefect.application_startup import (
    DatasetFileUploaderApplication,
)

from prefect import task
from dataset_file_loader_prefect.prefrect.upload_dragonball import upload_dragonball

from dataset_file_loader_prefect.prefrect.graphrag_bench import (
    FileType,
    upload_graphrag_bench,
)


@task
async def startup():
    DatasetFileUploaderApplication.create(
        config_loader=ConfigLoaderImplementation.create()
    )
    DatasetFileUploaderApplication.Instance().start()
    _ = await DatasetFileUploaderApplication.Instance().astart()
    await DatasetFileUploaderApplication.Instance().create_usecase()


async def shutdown():
    _ = await DatasetFileUploaderApplication.Instance().ashutdown()
    DatasetFileUploaderApplication.Instance().shutdown()


async def upload_dataset():
    try:
        await startup()
        await upload_graphrag_bench(
            json_path="./datasets/graphrag_bench_medical/medical.json",
            file_type=FileType.medical,
        )
        await upload_graphrag_bench(
            json_path="./datasets/graphrag_bench_novel/novel.json",
            file_type=FileType.novel,
        )
        # await upload_dragonball(
        # jsonl_path="./datasets/dragonball/dragonball_docs.jsonl"
        # )
    finally:
        await shutdown()
