import sys

from app.main import create_app


def test_application_factory_and_python_runtime():
    assert sys.version_info[:3] == (3, 13, 12)
    assert create_app().title == "Company Management API"
