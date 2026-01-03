from core.config_loader import ConfigLoaderImplementation
from file_uploader_prefect.application_startup import FileUploaderPrefect
from file_uploader_prefect.prefrect.prefrect_tasks import upload_files
from prefect_core.base_deployment import CustomFlow


if __name__ == "__main__":
    FileUploaderPrefect.create(ConfigLoaderImplementation.create())
    flow = CustomFlow(upload_files)  # type: ignore

    flow.serve(  # type: ignore
        name=FileUploaderPrefect.Instance().get_application_name(),
        tags=["file upload"],
    )
