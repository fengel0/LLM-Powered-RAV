import logging
import os
from dataclasses import dataclass, field
from string import Template
from types import ModuleType

from domain.llm.model import TextChatMessage

# from hippo_rag.template.templates import (
# ircot_musique,
# jrcot_hotpotqa,
# ner,
# ner_query,
# rag_qa_musique,
# triple_extraction,
# )

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplateManager:
    role_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "system": "system",
            "user": "user",
            "assistant": "assistant",
        },
        metadata={
            "help": "Mapping from default roles in prompte template files to specific LLM providers' defined roles."
        },
    )
    templates: dict[str, list[TextChatMessage]] = field(
        init=False,
        metadata={
            "help": "A dict from prompt template names to templates. A prompt template can be a Template instance or a chat history which is a list of dict with content as Template instance."
        },
    )

    def __post_init__(self) -> None:
        """
        Initialize the templates directory and load templates.
        """
        current_file_path = os.path.abspath(__file__)
        package_dir = os.path.dirname(current_file_path)
        self.templates_dir = os.path.join(package_dir, "templates")
        self._load_templates()

    def _load_templates(self) -> None:
        """
        Load all templates from Python scripts in the templates directory.
        """
        if not os.path.exists(self.templates_dir):
            logger.error(f"Templates directory '{self.templates_dir}' does not exist.")
            raise FileNotFoundError(
                f"Templates directory '{self.templates_dir}' does not exist."
            )

        self.templates = {}
        logger.info(f"Loading templates from directory: {self.templates_dir}")
        modules: list[ModuleType] = []
        for module in modules:
            try:
                prompt_template_raw: list[dict[str, str] | TextChatMessage] = (
                    module.prompt_template
                )
                prompt_template: list[TextChatMessage] = []

                for item in prompt_template_raw:
                    # logger.error(item)
                    prompt_template.append(
                        TextChatMessage(
                            role=self.role_mapping.get(item["role"], item["role"]),  # type: ignore
                            content=Template(item["content"]),  # type: ignore
                        )
                    )

                self.templates[module.__name__.split(".")[-1]] = prompt_template
                logger.debug(
                    f"Successfully loaded template from '{module.__name__}.py'."
                )

            except Exception as e:
                logger.error(f"Failed to load template from '{module.__name__}': {e}")
                raise

    def render(self, name: str, **kwargs: object) -> list[TextChatMessage]:
        """
        Render a template with the provided variables.

        Args:
            name (str): The name of the template.
            kwargs: Placeholder values for the template.

        Returns:
            Union[str, List[Dict[str, Any]]]: The rendered template or chat history.

        Raises:
            ValueError: If a required variable is missing.
        """
        template = self.get_template(name)
        try:
            rendered_list = [
                TextChatMessage(role=item.role, content=item.content.substitute(kwargs))  # type: ignore
                for item in template
            ]
            logger.debug(
                f"Successfully rendered chat history template '{name}' with variables: {kwargs}."
            )
            return rendered_list
        except KeyError as e:
            logger.error(f"Missing variable in chat history template '{name}': {e}")
            raise ValueError(f"Missing variable in chat history template '{name}': {e}")

    def list_template_names(self) -> list[str]:
        """
        List all available template names.

        Returns:
            List[str]: A list of template names.
        """
        logger.info("Listing all available template names.")

        return list(self.templates.keys())

    def get_template(self, name: str) -> list[TextChatMessage]:
        """
        Retrieve a template by name.

        Args:
            name (str): The name of the template.

        Returns:
            Union[Template, List[Dict[str, Any]]]: The requested template.

        Raises:
            KeyError: If the template is not found.
        """
        if name not in self.templates:
            logger.error(f"Template '{name}' not found.")
            raise KeyError(f"Template '{name}' not found.")
        logger.debug(f"Retrieved template '{name}'.")

        return self.templates[name]

    def print_template(self, name: str) -> None:
        """
        Print the prompt template string or chat history structure for the given template name.

        Args:
            name (str): The name of the template.

        Raises:
            KeyError: If the template is not found.
        """
        try:
            template = self.get_template(name)
            print(f"Template name: {name}")
            for item in template:
                logger.debug(f"Role: {item.role}, Content: {item.content}")
            logger.info(f"Printed template '{name}'.")
        except KeyError as e:
            logger.error(f"Failed to print template '{name}': {e}")
            raise

    def is_template_name_valid(self, name: str) -> bool:
        return name in self.templates
