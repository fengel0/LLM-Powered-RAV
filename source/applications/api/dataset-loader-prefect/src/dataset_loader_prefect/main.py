from core.config_loader import ConfigLoaderImplementation
from dataset_loader_prefect.application_startup import ApplicationDatasetloader
from dataset_loader_prefect.prefrect.prefrect_tasks import upload_dataset
from prefect_core.base_deployment import CustomFlow


if __name__ == "__main__":
    ApplicationDatasetloader.create(ConfigLoaderImplementation.create())
    flow = CustomFlow(upload_dataset)  # type: ignore
    flow.serve(
        name=ApplicationDatasetloader.Instance().get_application_name(),
        tags=["dataset loader"],
    )
