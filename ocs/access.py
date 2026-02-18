"""Access Control is a system for restricting access to some Agents or
Agent functions to certain clients.

Functions in this module are prefixed with one of:

- ``agent_`` -- functions used by an Agent to determine access
  controls and verify client access credentials.

- ``client_`` -- functions used by client programs to interact with
  Agents that implement access control.

- ``director_`` -- functions used by Access Director to process access
  rules and grant requests.

"""

import hashlib
import os
import random
import string
import time
import yaml
from enum import IntEnum
from fnmatch import fnmatch

from typing import List, Optional, Tuple, Union

# "asdict" imported so module users can easily serialize dataclasses.
from dataclasses import field, fields, asdict  # noqa

# Use pydantic dataclass in order to deserialize complex hierarchical
# objects, such as a dataclass that has a member that is a list of
# some other dataclass.
from pydantic.dataclasses import dataclass


from . import ocs_client

#: The protocol version ("access_control") that agents report
#: themselves as using via get_api.
AC_VERSION = 1


class CredLevel(IntEnum):
    """Representation of the credential level of a client, or the
    required credential level for some operation."""
    BLOCKED = 0
    BASIC = 1
    ADVANCED = 2
    FULL = 3
    SUPERUSER = 4

    def __str__(self):
        return f'{self.value}-{self.name}'


#: Keys to use for passwords associated with each CredLevel. These are
#: used in config blocks for Access Director and OCS clients, for
#: example.
CRED_KEYS = [
    ('password_1', CredLevel(1)),
    ('password_2', CredLevel(2)),
    ('password_3', CredLevel(3)),
    ('password_4', CredLevel(4)),
]


# Password and hashing support

def _get_random_string(length=8):
    return ''.join([random.choice(string.ascii_letters) for i in range(length)])


def _hashfunc_no_hash(x):
    return x


def _hashfunc_short_md5(x):
    return hashlib.md5(x.encode('utf-8')).hexdigest()[:16]


HASHFUNCS = {
    'none': _hashfunc_no_hash,
    'blocked': lambda x: ValueError('Should not call this hash func.'),
    'md5': _hashfunc_short_md5,
}


@dataclass
class HashedPass:
    """Container for hashed password values, for internal storage in
    Access Director agent as well as for distribution to Agents that
    need to validate clients.

    """

    #: The identifier for the hash being used (use "none") for clear
    #: text, and "blocked" to refuse to match any user password.
    hash: str

    #: The hashed string.  If this string is empty, and hash !=
    #: "blocked", then *any* provided password will match.
    value: str = ''

    def check(self, value: str) -> bool:
        """Check if the provided clear-text password matches this
        object's stored password, after hashing.

        """
        if value is None:
            value = ''
        if self.hash == 'blocked':
            return False
        if self.value == '':
            return True
        hashfunc = HASHFUNCS[self.hash]
        return hashfunc(value) == self.value

    @classmethod
    def create_blocked(cls):
        """Return an object representing "blocked" access."""
        return cls(hash='blocked')

    @classmethod
    def create_free(cls):
        """Return an object representing passwordless access."""
        return cls(hash='none')

    @classmethod
    def create_from_value(cls, hash, clear_text):
        """Return on object constructed from the hashed value of
        clear_text password.

        """
        hashfunc = HASHFUNCS[hash]
        return cls(hash=hash, value=hashfunc(clear_text))


@dataclass
class AccessPasswordItem:
    """A single entry in a password configuration file.

    This is used both in the Access Configuration File, which
    configures the Access Director, and in the OCS Password File,
    which clients reference to find passwords to use for specific
    agents.

    Each field in this object is either a **selector** or a
    **password**.

    The **selectors** are used to determine whether this rule applies
    to a particular agent instance (described in terms of its *agent_class* and
    *instance_id*).  Those keys are:

    - ``default`` (bool): True if this selector should apply to all
      agent instances -- when this is set, all other selector keys
      are ignored.
    - ``agent_class`` (str): This is a pattern to match against the
      provided *agent_class*.  If absent or set to None, this is
      ignored.
    - ``instance_id`` (str): This is a pattern to match against the
      provided *instance_id*.  If absent or set to None, this is
      ignored.

    Patterns and matching are as described in this module's
    :func:`pattern_match`.

    The **passwords** consist of:

    - ``password_1``: The password associated with credential level 1.
    - ``password_2``: The password ... level 2.
    - ``password_3``: The password ... level 3.
    - ``password_4``: The password ... level 4.

    When used in the Access Configuration File, the *password* entries
    define passwords that should be accepted, to grant clients that
    level of access.  The passwords may be strings (which will be
    interpreted as either clear-text, or pre-hashed values, depending
    on the ``passwords_block_default_hashfunc`` setting).  When the
    Agent is checking a password, it considers all the rules and
    returns the highest credential level matched by the password and
    target.

    When used in the OCS Password File, only ``password_2`` and/or
    ``password_3`` keys should be used -- and the values should be
    strings, which will be interpreted as the clear text passwords to
    use in the Client.

    """
    #: Selector variables
    default: Optional[bool] = False
    agent_class: Optional[str] = None
    instance_id: Optional[str] = None

    #: Password variables
    password_1: Optional[Union[str, HashedPass]] = None
    password_2: Optional[Union[str, HashedPass]] = None
    password_3: Optional[Union[str, HashedPass]] = None
    password_4: Optional[Union[str, HashedPass]] = None

    def get_scope_spec(self):
        return ScopeSpec(default=self.default,
                         agent_class=self.agent_class,
                         instance_id=self.instance_id)


@dataclass
class AgentSpec:
    """Identifying information for a specific Agent Instance.  Info
    here is compared against a ScopeSpec for an AccessRule, to see if
    rule should be applied to the Instance.

    """
    instance_id: str
    agent_class: str

    #: The superuser_key is used for an Agent to start its own
    #: operations, internally, such as on startup.
    superuser_key: Optional[object] = None


@dataclass
class ActionContext:
    """Placeholder class for future fine-grain access control /
    lockout of individual operations at the Access Director level.

    """
    op_name: Optional[str] = None
    action: Optional[str] = None


def pattern_match(target: str, pattern: str, raw=False):
    """Pattern-matching of a target against a pattern is defined as
    follows:

    - A pattern consists of one or more sub-patterns, separated by
      commas. The pattern matches the target if any of the
      positive sub-patterns match the target, as long as none of
      the negative sub-patterns matches the target.
    - If a sub-pattern does not start with "!", it is considered a
      positive sub-pattern and fnmatch is used to test the
      sub-pattern against the target.
    - If a sub-pattern starts with "!", then it is a negative
      sub-pattern and the remainder of the sub-pattern text is
      used with fnmatch to test against the target.

    Examples:

      - The pattern ``"Director,Act*,*Producer*"`` matches the string
        "Director" or any string that starts with "Act" or contains
        "Producer".
      - The pattern ``"*Agent,!FakeDataAgent"`` matches any string
        that ends with "Agent", except the string "FakeDataAgent".
      - The pattern ``"compute*,login*,!*9,!*8"`` matches any string
        that starts with "compute" or "login" and does not end with
        "8" or "9".

    """
    assert (',' not in target) and ('!' not in target)
    pos, neg = [], []
    for subpat in pattern.split(','):
        dest = pos
        if subpat.startswith('!'):
            dest = neg
            subpat = subpat[1:]
        if len(subpat) == 0:
            continue
        dest.append(fnmatch(target, subpat))
    if raw:
        return pos, neg
    return (len(pos) == 0 or any(pos)) and not any(neg)


@dataclass
class ScopeSpec:
    """A specification of the scope of an AccessRule.  See ``check``
    function for matching details.

    """
    default: Optional[bool] = False
    agent_class: Optional[str] = None
    instance_id: Optional[str] = None

    def check(self, agent: AgentSpec):
        """Determine whether ``agent`` matches the present ScopeSpec.

        If ``self.default`` is True, then this function returns True.
        Otherwise, if ``self.agent_class`` and ``self.instance_id``
        are both None, then this function returns False.  Otherwise
        the agent must match the pattern in self.agent_class, and the
        pattern in self.instance_id.

        See :func:`pattern_match` in this module for a description of
        patterns and matching.

        """
        if self.default:
            return True
        if self.agent_class is None and self.instance_id is None:
            return False
        if (self.agent_class is not None
                and not pattern_match(agent.agent_class, self.agent_class)):
            return False
        if (self.instance_id is not None
                and not pattern_match(agent.instance_id, self.instance_id)):
            return False
        return True

    def get_specificity(self):
        """Return the *specificity* of this rule, for sorting.  The
        principles are that positive patterns are more specific than
        negative patterns; and then that instance_id selection is more
        specific than agent_class selection.

        If default=True, then 0 is returned.  If not default, but
        agent_class and instance_id are both None, then 0 is returned.

        Otherwise, the specificity is the sum of the following
        contributions:

        - 8 if instance_id includes any positive subpatterns.
        - 4 if agent_class includes any positive subpatterns.
        - 2 if instance_id includes any negative subpatterns.
        - 1 if agent_class includes any negative subpatterns.

        """
        if self.default:
            return 0
        spec_bits = []
        if self.instance_id is not None:
            pos, neg = pattern_match('', self.instance_id, raw=True)
            if len(pos):
                spec_bits.append(3)
            if len(neg):
                spec_bits.append(1)
        if self.agent_class is not None:
            pos, neg = pattern_match('', self.agent_class, raw=True)
            if len(pos):
                spec_bits.append(2)
            if len(neg):
                spec_bits.append(0)
        if len(spec_bits) == 0:
            return -1
        return sum([(1 << b) for b in spec_bits])


@dataclass
class AccessRule:
    """A Rule for consumption by an Agent to grant or revoke access.
    The ``scope_spec`` determines what Agent Instances the rule should
    be applied to.  The cred_level is the level granted by this rule,
    if password in hashed_pass has been provided.

    The lockout_* entries are populated in the case that this rule
    arises from an Exclusive Access Grant.  The lockout_id is the name
    given to some specific lockout definition.  The lockout_owner is
    some identifier provided by whoever requested the lockout.  And
    lockout_levels is the list of CredLevels that other callers (those
    without the present lockout password) are forbidden from having.

    """
    hashed_pass: Optional[HashedPass]
    cred_level: Optional[CredLevel]
    scope_spec: ScopeSpec = field(default_factory=lambda: ScopeSpec(default=True))
    lockout_id: Optional[str] = None
    lockout_owner: Optional[str] = None
    lockout_levels: Optional[List[CredLevel]] = field(default_factory=list)


@dataclass
class AgentAccessRules:
    """A container used by Agents to hold configuration, including
    AccessRule (whether generated in place or received from Access
    Director agent).

    """
    policy: Optional[str] = None
    director_id: Optional[str] = None
    agent: Optional[AgentSpec] = None
    rules: List[AccessRule] = field(default_factory=list)


def agent_get_policy_default(policy: str) -> [AgentAccessRules]:
    """Get the default access rules, based on a "policy" string
    (probably from the --access-policy Agent argument).

    The policy passed in by the user should be one of the following:

    - "none" (or "", or None).  This effectively disables Access
      Control, as the returned rules will give a caller maximum
      privileges, no matter what password.
    - "override:pw2,pw3", where "pw2" and "pw3" represent the desired
      level 2 and level 3 passwords (unhashed).
    - "director:access-dir", where "access-dir" represents the
      instance-id of an Access Director agent.  The rules returned in
      this case will, initially, block all access; it's expected these
      rules will be updated by messages from the Access Director.

    """
    default_scope = ScopeSpec(default=True)
    free_pass = HashedPass.create_free()
    blocked_pass = HashedPass.create_blocked()

    if policy in [None, '', 'none']:
        return AgentAccessRules(
            policy='none',
            rules=[AccessRule(scope_spec=default_scope,
                              hashed_pass=free_pass,
                              cred_level=CredLevel(level))
                   for level in [1, 2, 3]])

    policy, args = policy.split(':', 1)

    if policy == 'director':
        if args == '':
            args = 'access-director'
        return AgentAccessRules(
            policy='director',
            director_id=args,
            rules=[AccessRule(scope_spec=default_scope,
                              hashed_pass=blocked_pass,
                              cred_level=CredLevel(level))
                   for level in [1, 2, 3]])

    elif policy == 'override':
        pws = args.split(',')
        return AgentAccessRules(
            policy='override',
            rules=[
                AccessRule(scope_spec=default_scope,
                           hashed_pass=free_pass,
                           cred_level=CredLevel(1)),
                AccessRule(scope_spec=default_scope,
                           hashed_pass=HashedPass(hash='none', value=pws[0]),
                           cred_level=CredLevel(2)),
                AccessRule(scope_spec=default_scope,
                           hashed_pass=HashedPass(hash='none', value=pws[1]),
                           cred_level=CredLevel(3)),
            ])
    raise ValueError(f'Invalid policy "{policy}"')


def agent_filter_rules(rules: List[AccessRule],
                       agent: AgentSpec) -> [List[AccessRule]]:
    """Filter a list of AccessRules, keeping only ones pertinent to
    agent.

    """
    return [rule for rule in rules
            if rule.scope_spec.check(agent)]


def agent_get_creds(
        password: Union[str, None],
        access_rules: AgentAccessRules,
        agent: AgentSpec,
        action: ActionContext = None,
) -> [CredLevel]:
    """Based on the access_rules, and the provided password, determine
    the credential level for the specified agent and action.

    """
    if access_rules.policy == 'none':
        return CredLevel(1), "No access policy -- level 1 for all."

    if agent.superuser_key is not None and password is agent.superuser_key:
        return CredLevel(4), "Super-user."

    cred_levels = [CredLevel(0)]
    blocked_levels = []
    lockout_owners = set()

    for rule in access_rules.rules:
        if not rule.scope_spec.check(agent):
            continue
        if rule.hashed_pass.check(password):
            cred_levels.append(rule.cred_level)
        elif len(rule.lockout_levels):
            blocked_levels.extend(rule.lockout_levels)
            lockout_owners.add(f"{rule.lockout_id}[{rule.lockout_owner}]")

    privs_diminished = False
    cred_level = max(cred_levels)
    while cred_level > CredLevel(0) and cred_level in blocked_levels:
        cred_level = CredLevel(cred_level.value - 1)
        privs_diminished = True

    return cred_level, ("" if not privs_diminished else
                        f"Privileges diminished; lockouts active: {list(lockout_owners)}")


def agent_rejection_message(cred_level: CredLevel, required_level: CredLevel,
                            lockout_detail: str = ''):
    """Get a helpful message about what privs are needed to access a
    resource protected at required_level.

    """
    assert cred_level.value < required_level.value
    text = (f'The action requires credential level {required_level} but the '
            f'client has only level {cred_level}')
    if lockout_detail != '':
        text += ' ' + lockout_detail
    return text


#
# Client support
#

def client_get_password(privs, agent_class, instance_id):
    """For OCSClient use -- determine the best client password to use.
    This may lead to inspection of OCS password files.

    Args:
      privs (str, int): If this is a string, it will be used as the
        password.  If this argument is an integer, it represents a
        desired credential level and the local password configuration
        will be inspected to find a password associated with access at
        that level.
      agent_class (str or None): If specified, will be used to match
        rules in the password config file.
      instance_id (str or None): If specified, will be used to match
        rules in the password config file.

    Returns:
      A string representing the password to use in all requests the
      client makes (these are passed to the agent in the
      "password=..." argument of the _ops_handler).

    Notes:
      If privs is a string, then this password is used directly and no
      inspection of config files is performend.

      If privs is 1, then the password '' is returned.

      If privs is 2 or 3, then the OCS password file is loaded and
      inspected for a suitable password.  The password file will be
      loaded from ``~/.ocs-passwords.yaml``, unless overridden by the
      environment variable ``OCS_PASSWORDS_FILE``.

      The password file is in yaml format, containing a single list.
      Each entry in the list is a dictionary referred to as a rule.
      Each rule is a dict with the schema described in
      :class:`ocs.access.AccessPasswordItem`.

      To find a suitable password, all rules are considered.  When
      multiple rules have selectors that match the target and contain
      a password of the required credential level or higher, then the
      one that is most *specific* is taken.  When multiple rules are
      tied for specificity, the one occurring latest in the list is
      taken.  "Specificity" is outlined in
      :func:`ScopeSpec.get_specificity`.

      Here's an example passwords file::

        - default: true
          password_3: "general-access-password"

        - agent_class: "FakeDataAgent"
          instance_id: "!faker4,!faker1"
          password_2: "normal-faker-password"

        - instance_id: "faker*"
          password_2: "special-faker-password"

        - instance_id: "faker4"
          password_2: "special-faker4-password"

      Suppose faker1 and faker4 both have agent_class "FakeDataAgent".
      For level 2 access, "faker1" matches the rules at index 0 and 2,
      but the most specific rule is 2 so that is used.  For "faker4",
      rules 0, 2, and 3 match.  Rules 2 and 3 are equally specific but
      rule 3 occurs later so it is used.

    """
    if isinstance(privs, str):
        return privs
    if privs is None:
        privs = 1
    if not isinstance(privs, int):
        raise ValueError("privs argument should be int or str.")
        assert 1 <= privs <= 3

    if privs == 1:
        return ''

    if os.getenv('OCS_PASSWORDS_FILE'):
        pw_file = os.getenv('OCS_PASSWORDS_FILE')
    else:
        pw_file = os.path.expanduser('~/.ocs-passwords.yaml')

    agent = AgentSpec(agent_class=agent_class, instance_id=instance_id)

    creds = yaml.safe_load(open(pw_file, 'rb'))
    candidates = []
    for i, row in enumerate(creds):
        scope_kw = {k: row.get(k) for k in ['default', 'agent_class', 'instance_id']}
        scope = ScopeSpec(**scope_kw)
        if scope.check(agent):
            specificity = scope.get_specificity()
            if 'password_2' in row and privs <= 2:
                candidates.append((specificity, i, row['password_2']))
            elif 'password_3' in row and privs <= 3:
                candidates.append((specificity, i, row['password_3']))
    if len(candidates) == 0:
        return ''
    return max(candidates)[2]


class ExclusiveAccessClient:
    """Manager class for Exclusive Access grants.

    Args:
      target:
        instance_id of the Access Director agent (or an
        OCSClient to use).
      grantee:
        Identifier for the requester (for consumer information).
      grant_name:
        The grant name, as defined in the grant config block.
      password:
        The password for the grant config block, if needed.

    The `acquire`, `renew` and `release` methods all return a tuple
    with `(ok, detail)`, where `ok` is a boolean indicating that
    things seem to have worked, and `detail` is the full "useful info"
    result returned by the call to :func:`AccessDirector.request_exclusive
    <ocs.agents.access_director.agent.AccessDirector.request_exclusive>`.
    See that function for details.

    """

    def __init__(self, target: str,
                 grantee: str, grant_name: str, password: str = None):
        if isinstance(target, str):
            self._client = ocs_client.OCSClient(target)
        else:
            self._client = target

        self._gargs = {
            'grantee': grantee,
            'grant_name': grant_name,
            'password': password,
        }
        self.password = None
        self.expire_at = None
        self.last_response = {'error': 'no history'}

    def acquire(self, expire_at: float = None) -> Tuple[bool, dict]:
        """Try to acquire the exclusive access grant. ``expire_at``
        is an optional unix timestamp to suggest as the grant expiry
        time.

        If this succeeds, the access password, and timestamp at which
        the grant will expire, are stored in ``self.password`` and
        ``self.expire_at``.

        """
        if expire_at is None:
            expire_at = time.time() + 100.
        resp = self._client._client.special('request_exclusive',
                                            action='acquire',
                                            expire_at=expire_at,
                                            **self._gargs)
        self.last_response = resp
        if 'error' in resp:
            return False, resp
        self.password = resp['password']
        self.expire_at = resp['expire_at']
        return True, resp

    def renew(self, expire_at: float = None) -> Tuple[bool, dict]:
        """Renew the Exclusive Access grant."""
        if expire_at is None:
            expire_at = time.time() + 100.
        resp = self._client._client.special('request_exclusive',
                                            action='renew',
                                            expire_at=expire_at,
                                            **self._gargs)
        if 'error' in resp:
            return False, resp
        self.expire_at = resp['expire_at']
        return True, resp

    def release(self) -> Tuple[bool, dict]:
        """Release the Exclusive Access grant."""
        resp = self._client._client.special('request_exclusive',
                                            action='release',
                                            **self._gargs)
        self.password = None
        self.expire_at = None
        return 'error' not in resp, resp

#
# Access Director Agent support
#


@dataclass
class GrantConfigItem:

    """A single entry from Access Director config file.

    """
    cred_level: Optional[CredLevel]
    # For ScopeSpec...
    default: Optional[bool] = False
    agent_class: Optional[str] = None
    instance_id: Optional[str] = None
    # Levels to which this grant prevents regular access.
    lockout_levels: Optional[List[CredLevel]] = field(default_factory=list)

    def get_scope_spec(self):
        return ScopeSpec(default=self.default,
                         agent_class=self.agent_class,
                         instance_id=self.instance_id)


@dataclass
class DistributedAccessGrant:
    """Class for decoding a "grant" block of Access Director config
    file.

    """
    name: str
    grants: List[GrantConfigItem]
    password: Optional[str] = None
    hash: Optional[str] = 'md5'


@dataclass
class AccessDirectorConfig:
    passwords_block_default_hashfunc: str = 'none'
    distrib_hashfunc: str = 'md5'
    passwords: List[AccessPasswordItem] = field(default_factory=list)
    exclusive_access_blocks: List[DistributedAccessGrant] = field(default_factory=list)


def director_parse_config(config: dict) -> dict:
    """Parse a config file and return the config dict.  This includes
    some validation and some translation.

    The elements at the top level of the returned dict will become
    attributes of the AD instance, so be careful what you add in
    there.

    """
    # Do a bunch of validation ...
    adc = AccessDirectorConfig(**config)

    out = {
        '_hashname': adc.distrib_hashfunc,
        '_hashfunc': HASHFUNCS[adc.distrib_hashfunc],
    }

    def promote_pw(pw):
        """Encode a password with the chosen default hash; unless it
        is the empty password in which case just leave it unhashed.

        """
        if isinstance(pw, str):
            if pw == '':
                pw = HashedPass.create_free()
            else:
                pw = HashedPass(hash=adc.passwords_block_default_hashfunc,
                                value=pw)
        if pw.hash != 'none':
            return pw
        if pw.hash == 'none' and pw.value == '':
            return pw
        return HashedPass.create_from_value(out['_hashname'], pw.value)

    rules = []
    for entry in adc.passwords:
        scope = entry.get_scope_spec()
        for k, level in CRED_KEYS:
            if getattr(entry, k) is None:
                continue
            hashed = promote_pw(getattr(entry, k))
            rules.append(AccessRule(
                hashed_pass=hashed, cred_level=level, scope_spec=scope))

    out.update({
        '_rules': rules,
        '_grant_blocks': adc.exclusive_access_blocks,
    })
    return out


def director_get_access_rules(
        grant_def: DistributedAccessGrant,
        grant_owner: str) -> Tuple[str, List[AccessRule]]:
    """Generate password for a grant block, and the corresponding
    access rule blocks to be passed to agents for processing
    credentials.

    Returns:
      password
        The password granting access.
      rules
        The list of AccessRule objects for distribution to agents.

    """
    pw = _get_random_string()
    hashed_pass = HashedPass.create_from_value(grant_def.hash, pw)

    rules = []
    for grant in grant_def.grants:
        scope = ScopeSpec(default=grant.default,
                          agent_class=grant.agent_class,
                          instance_id=grant.instance_id)
        rule = AccessRule(scope_spec=scope,
                          cred_level=grant.cred_level,
                          hashed_pass=hashed_pass,
                          lockout_id=grant_def.name,
                          lockout_owner=grant_owner,
                          lockout_levels=grant.lockout_levels)
        rules.append(rule)

    return pw, rules
