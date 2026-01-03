from core.config_loader import ConfigLoaderImplementation
from prefect.events import emit_event

from evaluation_service.usecase.evaluation import EvaluationServiceUsecases
from prefect import flow, logging, task

from trigger_evaluation_prefect.application_startup import TriggerApplication
from domain.pipeline.events import EventName


@task
async def startup():
    TriggerApplication.create(config_loader=ConfigLoaderImplementation.create())
    TriggerApplication.Instance().start()
    await TriggerApplication.Instance().astart()
    await TriggerApplication.Instance().create_usecase()


async def shutdown():
    await TriggerApplication.Instance().ashutdown()
    TriggerApplication.Instance().shutdown()


@task
async def fetch_questions_to_evaluat(eval_config_id: str):
    logger = logging.get_logger(__name__)
    questions_result = await EvaluationServiceUsecases.Instance().get_questions_that_where_not_validated_by_system(
        eval_config_id
    )

    if questions_result.is_error():
        raise questions_result.get_error()

    questions = questions_result.get_ok()
    for config_id, task_id in questions:
        logger.info(f"triggert eval for task:{task_id} and config_id: {config_id}")
        emit_event(
            event=EventName.EVALUATE_RAG_SYSTEM.value,
            resource={
                "prefect.resource.id": f"{task_id}",
                "prefect.resource.name": f"{config_id}",
            },
        )


@task
async def fetch_dataset_question_and_trigger_event(
    dataset: str, question_start: int, question_end: int, number_of_facts: int = 0
):
    logger = logging.get_logger(__name__)
    questions_result = (
        await EvaluationServiceUsecases.Instance().fetch_dataset_question(
            dataset_id=dataset,
            from_number=question_start,
            to_number=question_end,
            number_of_facts=number_of_facts,
        )
    )

    if questions_result.is_error():
        raise questions_result.get_error()

    questions = questions_result.get_ok()
    for question in questions:
        logger.info(f"triggert event for question {question.id}")
        emit_event(
            event=EventName.ASK_RAG_SYSTEM.value,
            resource={"prefect.resource.id": f"question/{question.id}"},
        )


@flow
async def upload_dataset(dataset: str, question_start: int, question_end: int):
    await startup()
    await fetch_dataset_question_and_trigger_event(
        dataset=dataset, question_start=question_start, question_end=question_end
    )
    await shutdown()


@flow
async def trigger_eval(eval_config_id: str):
    await startup()
    await fetch_questions_to_evaluat(eval_config_id)
    await shutdown()
