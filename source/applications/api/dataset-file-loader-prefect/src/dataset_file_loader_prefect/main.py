from core.config_loader import ConfigLoaderImplementation
from dataset_file_loader_prefect.application_startup import (
    DatasetFileUploaderApplication,
)
from dataset_file_loader_prefect.prefrect.prefrect_tasks import upload_dataset
from prefect_core.base_deployment import CustomFlow


if __name__ == "__main__":
    DatasetFileUploaderApplication.create(
        config_loader=ConfigLoaderImplementation.create()
    )
    flow = CustomFlow(upload_dataset)  # type: ignore
    flow.serve(
        name=DatasetFileUploaderApplication.Instance().get_application_name(),
        tags=["dataset loader"],
    )
