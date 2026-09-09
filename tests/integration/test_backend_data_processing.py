"""
Integration tests for the Django backend and data-processing layer.
"""

import pytest

from database.schema.models import UploadFile
from database.schema.connection import get_session


@pytest.mark.integration
def test_database_connection():
    """Verify that the application can connect to the database."""
    session = get_session()

    try:
        connection = session.connection()
        assert connection is not None
    finally:
        session.close()


@pytest.mark.integration
def test_upload_file_model_is_available():
    """Verify that the backend can import Member 3's UploadFile model."""
    assert UploadFile.__tablename__ == "upload_files"


@pytest.mark.integration
def test_backend_can_query_upload_files():
    """Verify that the backend can query Member 3's upload_files table."""
    session = get_session()

    try:
        result = session.query(UploadFile).limit(1).all()
        assert isinstance(result, list)
    finally:
        session.close()