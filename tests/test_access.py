import pytest
import os
import yaml

from unittest import mock

from ocs import access


def test_access_enums():
    """Instantiate and stringify all access enums."""
    for i in [1,2,3]:
        access.CredLevel(i).encode()
        access.AccessLevel(i).encode()
    for i in [0, 4]:
        access.CredLevel(i).encode()
        with pytest.raises(ValueError):
            b = access.AccessLevel(i)

    access.rejection_message(access.CredLevel(1),
                             access.AccessLevel(2))


def test_access_policy():
    """Check that get_creds produces correct CredLevel for typical
    policy requests.

    """
    rules = access.get_policy_default('director:')
    assert access.get_creds('', rules).value == 1
    assert access.get_creds('a', rules).value == 1

    rules = access.get_policy_default('override:a,b')
    assert access.get_creds('', rules).value == 1
    assert access.get_creds('a', rules).value == 2
    assert access.get_creds('b', rules).value == 3

    with pytest.raises(ValueError):
        rules = access.get_policy_default('invalid:')


def test_access_hashfuncs():
    """Check each hash function value stability."""
    # hashfunc test cases
    assert access.no_hash('a') == 'a'

    # hashfunc mapping
    bad_rules = {
        'password-2': {
            'hash': 'invalid',
            'value': '0x0x',
        }
    }
    assert access.get_creds('a', bad_rules).value == 1


@pytest.fixture(scope='session')
def password_file(tmp_path_factory):
    """Write a password file."""
    fn = tmp_path_factory.mktemp('ocs') / 'passwords.yaml'
    yaml.dump([
        {'agent-class': 'TestAgent',
         'password-2': 'TA-two'},
        {'instance-id': 'test-agent1',
         'password-2': 'ta-two',
         'password-3': 'ta-three'},
        {'default': 'default',
         'password-2': 'two'},
    ], fn.open('w'))
    return fn


def test_access_get_client_password(password_file):
    """Check that get_client_password parses the password_file data
    appropriately.

    """
    with mock.patch('os.getenv', mock.Mock(return_value=str(password_file))):
        # Fall through to default
        assert access.get_client_password(2, 'A', 'I') == 'two'

        # Agent / instance matching
        assert access.get_client_password(2, 'TestAgent', 'test-agent1') == 'TA-two'
        assert access.get_client_password(3, 'TestAgent', 'test-agent1') == 'ta-three'

        # No-match
        assert access.get_client_password(3, 'A', 'I') == ''

        # Passing strings just returns the string
        assert access.get_client_password('x', 'A', 'I') == 'x'
