import os

import pytest


@pytest.fixture(autouse=True)
def setup_testing_environment():
    """
    Sets up the IR_TESTING environment variable before each test and cleans it up after.
    This fixture runs automatically for all tests due to autouse=True.
    """
    # Set up environment variable before test
    old_value = os.environ.get("IR_TESTING")
    os.environ["IR_TESTING"] = "1"

    # Run the test
    yield

    # Clean up after test
    if old_value is not None:
        os.environ["IR_TESTING"] = old_value
    else:
        os.environ.pop("IR_TESTING", None)
