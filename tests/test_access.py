import pytest
import time
import yaml

from unittest import mock

from ocs import access


def test_access_enums():
    """Check ordering and stringification of access enums."""
    access.agent_rejection_message(access.CredLevel(1),
                                   access.CredLevel(2))
    assert access.CredLevel(1) == access.CredLevel(1)
    assert access.CredLevel(1) < access.CredLevel(2)


def test_access_policy():
    """Check that agent_get_creds produces correct CredLevel for
    typical policy requests.

    """
    agent = access.AgentSpec('my-id', 'my-class')

    rules = access.agent_get_policy_default('director:')
    assert access.agent_get_creds('', rules, agent)[0].value == 0

    rules = access.agent_get_policy_default('override:a,b')
    assert access.agent_get_creds('', rules, agent)[0].value == 1
    assert access.agent_get_creds('a', rules, agent)[0].value == 2
    assert access.agent_get_creds('b', rules, agent)[0].value == 3

    with pytest.raises(ValueError):
        rules = access.agent_get_policy_default('invalid:')


def test_agent_get_creds():
    """Check that agent_get_creds does things correctly."""

    def make_pw(pw, hash='none'):
        pw = access.HASHFUNCS[hash](pw)
        return {'hash': hash, 'value': pw}

    def test(pw, rules, agent, level):
        arules = access.AgentAccessRules(rules=rules)
        assert access.agent_get_creds(pw, arules, agent)[0].value == level

    agent = access.AgentSpec(agent_class='my-class',
                             instance_id='my-instance')

    # No rules -> reject.
    test('', [], agent, 0)

    # Any password will match empty password.
    rules = [
        {'cred_level': 2,
         'hashed_pass': make_pw('')}]
    test('', rules, agent, 2)
    test('anything', rules, agent, 2)
    test(None, rules, agent, 2)

    # Even if it matches other things
    rules = [
        {'cred_level': 1,
         'hashed_pass': make_pw('anything', 'md5')},
        {'cred_level': 2,
         'hashed_pass': make_pw('')},
    ]
    test('', rules, agent, 2)
    test('anything', rules, agent, 2)
    test(None, rules, agent, 2)

    # Match this agent
    rules = [
        {'cred_level': 1,
         'hashed_pass': make_pw('')},
        {'cred_level': 2,
         'hashed_pass': make_pw('my-pw2'),
         'scope_spec': {'agent_class': 'my-class'}},
        {'cred_level': 3,
         'hashed_pass': make_pw('my-pw3'),
         'scope_spec': {'instance_id': 'my-instance'}},
    ]
    test('', rules, agent, 1)
    test('my-pw2', rules, agent, 2)
    test('my-pw3', rules, agent, 3)

    # Don't match other agents.
    rules = [
        {'cred_level': 1,
         'hashed_pass': make_pw('my-pw')},
        {'cred_level': 2,
         'hashed_pass': make_pw('my-pw'),
         'scope_spec': {'agent_class': 'other-class'}},
        {'cred_level': 3,
         'hashed_pass': make_pw('my-pw'),
         'scope_spec': {'instance_id': 'other-instance'}},
    ]
    test('', rules, agent, 0)
    test('my-pw', rules, agent, 1)


def test_pattern_matching():
    def should_succeed(pattern, targets):
        for target in targets:
            assert access.pattern_match(target, pattern)

    def should_fail(pattern, targets):
        for target in targets:
            assert not access.pattern_match(target, pattern)

    pat = 'HWP*,Fake*,!HWPSuper,!FakeSerpent'
    should_succeed(pat, ['HWPxyz', 'FakeBlomp', 'HWPSuperX'])
    should_fail(pat, ['HWPSuper', 'FakeSerpent', 'NormalSerpent'])


def test_access_hashfuncs():
    """Check each hash function value stability."""
    # hashfunc test cases
    assert access.HASHFUNCS['none']('a') == 'a'
    assert len(access.HASHFUNCS['md5']('a')) > 1

    # hashfunc mapping
    agent = access.AgentSpec('my-id', 'my-class')
    bad_rules = access.AgentAccessRules(
        policy='test',
        rules=[
            access.AccessRule(cred_level=access.CredLevel(2),
                              hashed_pass=access.HashedPass(hash='invalid',
                                                            value='0x0x')),
            access.AccessRule(cred_level=access.CredLevel(1),
                              hashed_pass=access.HashedPass.create_free())
        ])
    with pytest.raises(KeyError):
        access.agent_get_creds('a', bad_rules, agent)


@pytest.fixture(scope='session')
def password_file(tmp_path_factory):
    """Write a password file."""
    fn = tmp_path_factory.mktemp('ocs') / 'passwords.yaml'
    yaml.dump([
        {'default': True,
         'password_2': 'two'},
        {'instance_id': 'test-agent1',
         'password_2': 'ta-two',
         'password_3': 'ta-three'},
        {'agent_class': 'TestAgent',
         'password_2': 'TA-two'},
        {'agent_class': '!NormalAgent',
         'password_2': 'spec-test'},
    ], fn.open('w'))
    return fn


def test_access_client_get_password(password_file):
    """Check that client_get_password parses the password_file data
    appropriately.

    """
    with mock.patch('os.getenv', mock.Mock(return_value=str(password_file))):
        # Fall through to default
        assert access.client_get_password(2, 'NormalAgent', 'I') == 'two'

        # Agent / instance matching
        assert access.client_get_password(2, 'TestAgent', 'test-agent1') == 'ta-two'
        assert access.client_get_password(3, 'TestAgent', 'test-agent1') == 'ta-three'

        assert access.client_get_password(2, 'OtherAgent', 'other-agent-x') == 'spec-test'

        # No-match
        assert access.client_get_password(3, 'A', 'I') == ''

        # Passing strings just returns the string
        assert access.client_get_password('x', 'A', 'I') == 'x'


def test_director_parse_config():
    config_raw = {
        'distrib_hashfunc': 'md5',
        'passwords': [
            {'default': True,
             'password_3': "test"},
            {'instance_id': 'faker4',
             'password_2': {'hash': 'none',
                            'value': 'blech'}}],
        'exclusive_access_blocks': [
            {'name': 'fake-subsystem',
             'password': 'lockout-test',
             'grants': [
                 {'instance_id': 'faker4',
                  'cred_level': 3,
                  'lockout_levels': [1, 2, 3]},
             ]}
        ],
    }

    config = access.director_parse_config(config_raw)
    assert config['_rules'][1].hashed_pass.hash == 'md5'


def test_lockouts():
    dag = access.DistributedAccessGrant(
        name='test-lockout',
        grants=[
            {'instance_id': 'my-instance',
             'lockout_levels': [1, 2, 3],
             'cred_level': 3,
             },
            {'agent_class': 'my-class',
             'lockout_levels': [2, 3],
             'cred_level': 2,
             },
            {'default': True,
             'cred_level': 1,
             },
        ])
    pw, rules = access.director_get_access_rules(dag, 'this-owner')
    assert (pw != '')

    agent = access.AgentSpec(instance_id='my-instance',
                             agent_class='my-class')
    related_agent = access.AgentSpec(instance_id='other-instance',
                                     agent_class='my-class')

    arules = access.AgentAccessRules(rules=rules)
    assert access.agent_get_creds(pw, arules, agent)[0].value == 3
    assert access.agent_get_creds(pw, arules, related_agent)[0].value == 2

    assert access.agent_get_creds('not-' + pw, arules, agent)[0].value == 0

    # What if we had existing permissions?
    rules0 = [access.AccessRule(scope_spec={'default': True}, cred_level=3,
                                hashed_pass={'hash': 'none', 'value': 'backdoor'}),
              access.AccessRule(scope_spec={'default': True}, cred_level=4,
                                hashed_pass={'hash': 'none', 'value': 'superu'})]
    arules = access.AgentAccessRules(rules=rules0 + rules)
    # This gets blocked by lockout_levels.
    assert access.agent_get_creds('backdoor', arules, agent)[0].value == 0
    # But super-user cannot be blocked.
    assert access.agent_get_creds('superu', arules, agent)[0].value == 4

    # If not my-instance, then access is only partially blocked...
    assert access.agent_get_creds('backdoor', arules, related_agent)[0].value == 1


def test_exclusive_access_grant_helper():
    def fake_accessdir(special, action=None, grant_name=None, **kwargs):
        if action == 'acquire':
            return {
                'grant_name': grant_name,
                'message': 'grant acquired',
                'password': 'abcdefg',
                'expire_at': time.time() + 5,
            }
        elif action == 'renew':
            return {
                'grant_name': grant_name,
                'message': 'grant renewed',
                'expire_at': time.time() + 5,
            }
        elif action == 'release':
            return {
                'grant_name': grant_name,
                'message': 'grant released',
            }

    client = mock.MagicMock()
    client._client.special = fake_accessdir
    eag = access.ExclusiveAccessClient(client, 'test-func', 'fake-subsystem',
                                       password='lockout-test')
    ok, detail = eag.acquire()
    assert ok
    ok, detail = eag.renew()
    assert ok
    ok, detail = eag.release()
    assert ok
