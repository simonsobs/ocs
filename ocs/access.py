"""Access Control is a system for restricting access to some Agents or
Agent functions to certain clients.

"""

import os
import yaml
from enum import Enum

class CredLevel(Enum):
    """The credential level of a client."""
    BLOCKED = 0
    BASIC = 1
    ADVANCED = 2
    FULL = 3
    SUPERUSER = 4
    def encode(self):
        return f'{self.value}-{self.name}'

class AccessLevel(Enum):
    """The minimum credential level that is required to access an
    endpoint.

    Compare to a CredLevel using .value, e.g.::

      if cred_level.value >= access_level.value:
        do_the_thing()

    """
    BASIC = 1
    ADVANCED = 2
    FULL = 3
    def encode(self):
        return f'{self.value}-{self.name}'

def get_creds(credentials, rules, op_name=None, action=None):
    """Based on the current access control rules, and the credentials
    provided by the client, determine what credential level this
    client has.

    Returns:
      A CredLevel.

    """
    if credentials is None or credentials == '':
        return CredLevel(1)
    for k, level in [('password-2', CredLevel(2)),
                     ('password-3', CredLevel(3))]:
        if credentials == rules.get(k):
            return level
    return CredLevel(1)

def rejection_message(cred_level: CredLevel, access_level: AccessLevel):
    """Get a helpful message about what privs are needed to access a
    resource protected at access_level.

    """
    assert(cred_level.value < access_level.value)
    return 'The action requires privileges %s but the client has only %s' % (
        access_level.encode(), cred_level.encode())

def get_client_password(privs, agent_class, instance_id):
    """Determine the best client password to use.  This may lead to
    inspection of OCS password files.

    Args:
      privs (str or int): Either a string representing a password to
        use, or an integer (1, 2, 3) representing the Access Level
        that is desired.
      agent_class (str or None): If specified, will be used to match
        rules in the password config file.
      instance_id (str or None): If specified, will be used to match
        rules in the password config file.

    Returns:
      A string representing the password to use in all requests the
      client makes (these are passed to the agent in the
      "credentials=..." argument of the _ops_handler).

    Notes:

      If privs is a string, then this password is used directly and no
      inspection of config files is performend.

      If privs is 1, then the password '' is returned.

      If privs is 2 or 3, then the OCS password file is loaded and
      inspected for a suitable password.  The password file will be
      loaded from ~/.ocs-passwords.yaml, unless overridden by the
      environment variable OCS_PASSWORD_FILE.

      The OCS_PASSWORD_FILE must be yaml containing a single list.
      Each entry in the list is a dictionary referred to as a rule.

      A rule must have the following format::

        {
          <selector>: <value to match>
          'password-2': <password for level 2 access>,
          'password-3': <password for level 3 access>,
        }

      The "selector" must be either "agent-class", "instance-id", or
      "default" (in the case of default, the value to match should
      also be set to default).  It is permitted to include both an
      agent-class and a n instance-id selector, in which case both
      must be matched.

      Here's an example::

        - agent-class: FakeDataAgent
          password-2: fake-pw-2
          password-3: fake-pw-3

        - instance-id: registry
          password-3: please-let-me-register

        - default: default
          password-2: general-level2-password
          password-3: general-level2-password

      When attempting to find a password, the *first* rule that
      matches will be used.  This means that the rules should be
      organized from most specific to least specific.

      If privs=2 is requested, and a matching rule is found, but the
      password-2 is not specified, then the password-3 value will be
      returned if present.

    """

    if isinstance(privs, str):
        return privs
    if privs is None:
        privs = 1
    if not isinstance(privs, int):
        raise ValueError("privs argument should be int or str.")
        assert(1 <= privs <= 3)

    if privs == 1:
        return ''

    if os.getenv('OCS_PASSWORDS_FILE'):
        cred_file = os.getenv('OCS_PASSWORDS_FILE')
    else:
        cred_file = os.path.expanduser('~/.ocs-passwords.yaml')

    creds = yaml.safe_load(open(cred_file, 'rb'))
    for row in creds:
        _d = row.get('default')
        _a = row.get('agent-class')
        _i = row.get('instance-id')
        if (_d is not None) or (
                (_a is None or _a == agent_class) and \
                (_i is None or _i == instance_id)):
            if 'password-2' in row and privs <= 2:
                return row['password-2']
            if 'password-3' in row and privs <= 3:
                return row['password-3']

    return ''
