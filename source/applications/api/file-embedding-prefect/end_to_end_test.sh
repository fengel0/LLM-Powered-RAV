set -e
pytest ./tests/application_startup.py
pytest tests/test_hippo_end_to_end.py
pytest tests/test_llama_index_end_to_end.py

