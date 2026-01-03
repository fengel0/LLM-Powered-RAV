from core.config_loader import ConfigLoaderImplementation
from prefect import task
from grading_prefect.application_startup import (
    GradingApplication,
    GradingConfigLoaderApplication,
)
from grading_service.usecase.grading import GradingServiceUsecases


@task
async def grade_answer(test_sample_id: str, candiate: str):
    result = await GradingServiceUsecases.Instance().evaluate_answer(
        test_sample_id=test_sample_id, candidate_to_evaluate=candiate
    )
    if result.is_error():
        raise result.get_error()


@task
async def startup():
    GradingConfigLoaderApplication.create(ConfigLoaderImplementation.create())
    GradingConfigLoaderApplication.Instance().start()
    await GradingConfigLoaderApplication.Instance().astart()
    await GradingConfigLoaderApplication.Instance().create_usecase()

    grading_config = await GradingConfigLoaderApplication.Instance().get_config()

    await GradingConfigLoaderApplication.Instance().ashutdown()
    GradingConfigLoaderApplication.Instance().shutdown()

    GradingApplication.create(ConfigLoaderImplementation.create())
    GradingApplication.Instance().set_grading_config(config=grading_config)
    GradingApplication.Instance().start()
    await GradingApplication.Instance().astart()
    await GradingApplication.Instance().create_usecase()


async def shutdown():
    await GradingApplication.Instance().ashutdown()
    GradingApplication.Instance().shutdown()


async def evaluate_answer(task_id: str, candiate: str):
    try:
        await startup()
        await grade_answer(test_sample_id=task_id, candiate=candiate)
    finally:
        await shutdown()
