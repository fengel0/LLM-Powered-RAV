set -e 
pytest tests/config_tests.py
pytest tests/result_tests.py
pytest tests/enviroment_setter.py
pytest tests/encodeing_tests.py
pytest tests/que_tests.py

