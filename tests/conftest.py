"""
pytest configuration file to exclude certain functions from being treated as tests
"""

def pytest_collection_modifyitems(items):
    """Modify test collection to exclude certain functions"""
    # Exclude functions that are imported but not meant to be tests
    for item in list(items):
        if item.name == "test_rtu_connection" and not item.parent.name.startswith("Test"):
            items.remove(item)
