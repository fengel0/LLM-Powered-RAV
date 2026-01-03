import mimetypes


def get_content_type(filetype: str) -> str:
    """
    Returns the Content-Type (MIME type) for a given file extension.

    Args:
        filetype (str): The file extension or filename (e.g., '.txt', 'image.png').

    Returns:
        str: The corresponding MIME type, or 'application/octet-stream' if unknown.
    """
    # Ensure it starts with a dot if it's just an extension
    if not filetype.startswith(".") and "." not in filetype:
        filetype = f".{filetype}"

    content_type, _ = mimetypes.guess_type(filetype)
    return content_type or "application/octet-stream"
