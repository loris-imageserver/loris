import logging

import pytest


@pytest.fixture
def reset_logger():
    """Reset the logger at the end of a test run."""
    yield
    logger = logging.getLogger()

    # Note: we wrap ``logger.handlers`` and ``logger.filters`` in calls to
    # ``list()`` because they change size mid-iteration, and we want to ensure
    # that we really do delete every handler and filter.
    for h in list(logger.handlers):
        logger.removeHandler(h)
    for f in list(logger.filters):
        logger.removeFilter(f)

    try:
        delattr(logger, 'handler_set')
    except AttributeError:
        pass

    assert len(logger.handlers) == 0
    assert len(logger.filters) == 0
