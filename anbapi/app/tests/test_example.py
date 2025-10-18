from anbapi.app.services.service_example import bool_login

def test_is_login():
    assert bool_login(True) is True
