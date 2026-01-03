from core.config_loader import ConfigLoaderImplementation
from prefect import task

from dataset_loader_prefect.application_startup import ApplicationDatasetloader
from dataset_loader_prefect.prefrect.graphrag_bench import (
    FileType,
    upload_graphrag_bench,
)
from dataset_loader_prefect.prefrect.upload_dragonball import upload_dragonball
from dataset_loader_prefect.prefrect.upload_fh import upload_fh
from dataset_loader_prefect.prefrect.upload_weimar import upload_weimar


@task
async def startup():
    ApplicationDatasetloader.create(ConfigLoaderImplementation.create())
    ApplicationDatasetloader.Instance().start()
    _ = await ApplicationDatasetloader.Instance().astart()
    await ApplicationDatasetloader.Instance().create_usecase()


async def shutdown():
    _ = await ApplicationDatasetloader.Instance().ashutdown()
    ApplicationDatasetloader.Instance().shutdown()


async def upload_dataset():
    try:
        await startup()
        await upload_dragonball(
            jsonl_path="./datasets/dragonball/dragonball_queries_cleaned.jsonl"
        )
        await upload_fh("./datasets/fh_dataset/dataset.json")
        await upload_graphrag_bench(
            json_path="./datasets/graphrag_bench_novel/novel_questions_cleaned_and_filtered.json",
            file_type=FileType.novel,
        )
        await upload_graphrag_bench(
            json_path="./datasets/graphrag_bench_medical/medical_questions_cleaned_and_filtered.json",
            file_type=FileType.medical,
        )
        await upload_weimar("./datasets/weimar/09_100_questions.json")
    finally:
        await shutdown()
