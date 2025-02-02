from nexus.services import data


def test_run():
    assert data.dummy_test() == 1
