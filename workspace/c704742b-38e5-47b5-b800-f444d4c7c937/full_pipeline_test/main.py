import logging
from typing import Any

logger = logging.getLogger(__name__)

def run_pipeline(data: Any) -> Any:
    """
    Run the full pipeline on the given data.

    Args:
        data: Input data to process.

    Returns:
        Processed data.

    Raises:
        ValueError: If data is None.
    """
    if data is None:
        logger.error("Input data is None")
        raise ValueError("Input data cannot be None")
    logger.info("Pipeline started")
    # Placeholder for pipeline logic
    result = data
    logger.info("Pipeline completed successfully")
    return result
