from deployment_base.enviroment import log_env
from core.logger import OTELConfig, init_logging
from core.config_loader import ConfigLoader

from deployment_base.application import SyncLifetimeReg


class LoggerStartupSequence(SyncLifetimeReg):
    def __init__(self, application_name: str, application_version: str) -> None:
        self._application_name = application_name
        self._application_version = application_version
        super().__init__()

    def start(self, config_loader: ConfigLoader):
        result = config_loader.load_values(log_env.SETTINGS)
        if result.is_error():
            raise result.get_error()
        otel_config: OTELConfig | None = None
        if config_loader.get_bool(log_env.OTEL_ENABLED):
            host = config_loader.get_str(log_env.OTEL_HOST)
            otel_config = OTELConfig(
                title=self._application_name,
                version=self._application_version,
                otel_host=host,
                otel_metric_host=host,
                otel_log_host=host,
                insecure=config_loader.get_bool(log_env.OTEL_INSECURE),
            )
        init_logging(
            config_loader.get_str(log_env.LOG_LEVEL),
            otel_config,
        )

    def shutdown(self):
        return
