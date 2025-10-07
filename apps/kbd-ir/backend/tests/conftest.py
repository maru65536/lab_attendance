import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ['KBDIR_DATABASE_URL'] = 'sqlite:///' + str(Path(tempfile.gettempdir()) / 'kbd_ir_test.db')

from ..main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
