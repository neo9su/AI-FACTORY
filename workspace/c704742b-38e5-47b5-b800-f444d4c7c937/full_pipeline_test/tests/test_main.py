import logging
import pytest
from full_pipeline_test.main import run_pipeline

logger = logging.getLogger(__name__)

def test_run_pipeline_with_valid_data():
    """Test run_pipeline with valid input."""
    data = {"key": "value"}
    result = run_pipeline(data)
    assert result == data

def test_run_pipeline_with_none():
    """Test run_pipeline raises ValueError when data is None."""
    with pytest.raises(ValueError, match="Input data cannot be None"):
        run_pipeline(None)

def test_run_pipeline_with_empty_dict():
    """Test run_pipeline with empty dictionary."""
    data = {}
    result = run_pipeline(data)
    assert result == data

def test_run_pipeline_with_list():
    """Test run_pipeline with list input."""
    data = [1, 2, 3]
    result = run_pipeline(data)
    assert result == data
