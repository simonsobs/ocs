"""Access Control is a system for restricting access to some Agents or
Agent functions to certain clients.

"""

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
    # Interim, let the client state its credential level as an
    # integer.
    if isinstance(credentials, int) and credentials > 1:
        return CredLevel(credentials)
    return CredLevel(1)

def rejection_message(cred_level: CredLevel, access_level: AccessLevel):
    """Get a helpful message about what privs are needed to access a
    resource protected at access_level.

    """
    assert(cred_level.value < access_level.value)
    return 'The action requires privileges %s but the client has only %s' % (
        access_level.encode(), cred_level.encode())
