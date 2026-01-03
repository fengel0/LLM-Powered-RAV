# Image Description Service

## Overview  

The **Image Description Service** is a Python package that automatically generates natural‑language descriptions for images stored in a file bucket.
By leveraging a multimodal AI model (e.g., Ollama), the service extracts visual information from an image, optionally enriches it with additional context files, and stores the resulting description back into the same storage system.

## What the Package Can Do  

- **Fetch Images:** Retrieves an image file from a specified bucket using the provided file storage abstraction.  
- **Contextual Enrichment:** Allows a list of additional files to be fetched and included as context for the description, enabling more accurate or domain‑specific outputs.  
- **AI‑Powered Description:** Sends the image (encoded as base64) together with a system prompt and optional contextual text to a multimodal language model, which returns a textual description of the image.  
- **Store Results:** Uploads the generated description as a new file (with a naming convention that identifies it as an image description) back to the same bucket, preserving the original image and its metadata.  
- **Error Handling:** Propagates any errors that occur during fetching, description generation, or uploading, ensuring that callers receive clear feedback.  

## Key Features  

| Feature | Description |
|---------|-------------|
| **Multimodal Model Integration** | Works with any multimodal model that accepts a base64‑encoded image and a textual prompt. |
| **Extensible Context** | Accepts a list of additional files whose contents are concatenated and supplied to the model to improve relevance. |
| **Configurable Prompts** | System and user prompts are defined in the service configuration, allowing customization of the description style. |
| **Workspace‑Based Development** | Uses UV workspace sources for `core`, `domain`, and `domain-test` packages, simplifying local development and testing. |
| **Optional Test Dependencies** | Provides a `test` extra that includes `domain-test==0.2.0` for unit and integration testing. |

## Project Structure  

- **pyproject.toml** – Defines the package metadata, required Python version (>=3.12,<3.13), core dependencies, and optional test dependencies [1].  
- **image_description.py** – Contains the core logic for fetching images, generating descriptions via the multimodal model, and uploading the results [2].  

## Typical Workflow (Conceptual)  

1. **Initialize** the service with configuration (system prompt, user prompt, file storage client, tracer, etc.).  
2. **Call** `describe_image(filename, bucket, context_files)` with the target image and any supplementary files.  
3. The service **fetches** the image and context files from the storage bucket.  
4. It **encodes** the image to base64 and sends it, along with the prompts and context, to the AI model.  
5. Upon receiving the description, the service **uploads** it as a new file named according to the image description convention.  
6. The result is returned as a success indicator or an error if any step fails.  

