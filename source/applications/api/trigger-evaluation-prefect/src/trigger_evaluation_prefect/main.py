from core.config_loader import ConfigLoaderImplementation
from prefect import serve
from trigger_evaluation_prefect.application_startup import TriggerApplication
from trigger_evaluation_prefect.prefrect.prefrect_tasks import (
    upload_dataset,
    trigger_eval,
)


if __name__ == "__main__":
    TriggerApplication.create(config_loader=ConfigLoaderImplementation.create())
    deployment1 = upload_dataset.to_deployment(
        f"{TriggerApplication.Instance().get_application_name()}-dataset"
    )
    deployment2 = trigger_eval.to_deployment(
        f"{TriggerApplication.Instance().get_application_name()}-eval"
    )

    serve(deployment1, deployment2)
