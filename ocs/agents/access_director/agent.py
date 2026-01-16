from ocs import ocs_agent, site_config, access

import argparse
import os
import time
import yaml

from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep as dsleep


class AccessDirector:
    """Agent for distributing Access Control information to all Agents
    in a system.

    """

    def __init__(self, agent, config_file):
        self.agent = agent
        self.agent.register_feed('controls', record=False)
        self.log = agent.log

        self._registered = False

        self._config_file = config_file
        self._requests = []
        self._active_grants = []

        self._load_config()

    @ocs_agent.param('_')
    @inlineCallbacks
    def manager(self, session, params):
        """manager()

        **Process** Update the main access control feed with new
        access information.  This occurs in response to agent queries,
        or if new grants require updates to access.

        """
        session.set_status('running')
        session.data = {}

        if not self._registered:
            yield self.agent.register(
                self.agent_poll,
                f'{self.agent.agent_address}.agent_poll')
            yield self.agent.register(
                self.request_exclusive,
                f'{self.agent.agent_address}.request_exclusive')
            self._registered = True

        last_blast = 0

        while session.status in ['running']:
            yield dsleep(1)
            now = time.time()

            # Expire grants?
            keepers = []
            for _g in self._active_grants:
                if _g.expire_at <= now:
                    self.log.info(f'Grant expiring: {_g.name}')
                else:
                    keepers.append(_g)
            if len(keepers) < len(self._active_grants):
                self._active_grants = keepers
                self._update_all()

            session.data['grants'] = [v.encode() for v in self._active_grants]
            while len(self._requests):
                r = self._requests.pop(0)
                msg = {'reset': True,
                       'ac_version': access.AC_VERSION,
                       'rules': list(self._rules)}

                for _grant in self._active_grants:
                    msg['rules'].extend(_grant.rules)

                if r['type'] == 'reset':
                    last_blast = time.time()
                elif r['type'] == 'single':
                    agent = access.AgentSpec(
                        agent_class=r['agent_class'],
                        instance_id=r['instance_id'])
                    subrules = access.agent_filter_rules(msg['rules'], agent)
                    msg = {'target': r['instance_id'],
                           'ac_version': access.AC_VERSION,
                           'rules': subrules}

                if 'rules' in msg:
                    msg['rules'] = [access.asdict(r) for r in msg['rules']]

                self.agent.publish_to_feed('controls', msg)

            if time.time() - last_blast > 60:
                self._update_all()

        return True, 'Exited.'

    def _load_config(self):
        # Read the file and convert to internal rep.
        config_raw = yaml.safe_load(open(self._config_file, 'rb'))
        config = access.director_parse_config(config_raw)

        # Transfer new config to self.
        for k, v in config.items():
            setattr(self, k, v)

        # Request a compete update.
        self._update_all()

    def _update_all(self):
        self._requests.append({'type': 'reset'})

    @ocs_agent.param('_')
    @inlineCallbacks
    def reload_config(self, session, params):
        """reload_config()

        **Task** - Reload access config file.

        """
        yield self._load_config()
        return True, 'Update requested.'

    @inlineCallbacks
    def agent_poll(self, instance_id=None, agent_class=None):
        """*Special access point.* This is used for agents to request
        an announcement of their password rules on the control feed.
        The instance_id and agent_class arguments must both be
        specified.

        """
        self._requests.append({
            'type': 'single',
            'instance_id': instance_id,
            'agent_class': agent_class,
        })
        yield self.log.info(f'agent-poll received from {agent_class}:{instance_id}')

    def request_exclusive(self, grant_name=None, password=None,
                          action=None, expire_at=None, grantee=None,
                          strict=None):
        """*Special access point.* Request, renew, or release an
        exclusive access grant.

        Args:
          grant_name (str): Name of the grant, to match an entry in
            the "grant-blocks" section of the config file.
          password (str): The password, to be checked against the
            password specified in the grant block of the config.
          action (str): One of "acquire", "renew" or "release".
          expire_at (float): Unix timestamp for the desired expiry
            time of the grant.
          grantee (str): A string representing the client that has
            requested the lock. When passed with "acquire", it is
            stored for distribution to clients so they can explain who
            has locked them out.
          strict (bool): If True, reject all requests except acquire
            when a grant is inactive, renew when a grant is active,
            and release when a grant is active.

        Returns:
          A dict with useful info.

          On error, the dict has only an entry "error" with an error
          message in it.

          On success, the returned dict has at least the items
          'grant_name' (which matches the requested grant_name) and
          'message'; the 'message' is just "grant acquired" / "grant
          renewed" / "grant released".

          Additionally, if the 'action' is 'acquire' or 'renew' then
          the dict will include an entry 'expire_at' with the unix
          timestamp that the grant will be cancelled automatically.
          This timestamp may be earlier (but not later) than the time
          requested with the expire_at parameter.

          If the action is 'acquire', then the dict also has an entry
          'password', containing the password client should use to
          access the exclusive access targets for the duration of the
          access grant.

        """
        if grant_name is None:
            return {'error': 'No grant_name specified.'}
        if strict is None:
            strict = True

        for block in self._grant_blocks:
            if block.name == grant_name:
                break
        else:
            return {'error': f'Named grant not found ({grant_name})'}
        if block.password is not None and block.password != password:
            return {'error': f'Credential failed to access ({grant_name})'}

        # Does this grant already exist somewhere?
        for grant_idx, g in enumerate(self._active_grants):
            if g.name == grant_name:
                break
        else:
            grant_idx = None

        if action == 'acquire':
            if grant_idx is not None:
                if strict:
                    return {'error': 'Grant is already held; release it first.'}
                else:
                    self._active_grants.pop(grant_idx)

            # Generate passwords for this grant.
            password, rules = access.director_get_access_rules(block, grantee)
            new_grant = AccessGrant(grant_name, rules, expire_at, grantee)
            self._active_grants.append(new_grant)
            self._update_all()
            self.log.info(f'Exclusive access granted: {grant_name}')
            return {'message': 'grant acquired', 'password': password,
                    'grant_name': grant_name,
                    'expire_at': new_grant.expire_at}

        elif action == 'renew':
            if grant_idx is None:
                return {'error': 'Grant is not currently held; cannot renew.'}
            self._active_grants[grant_idx].renew(expire_at)
            return {'message': 'grant renewed',
                    'grant_name': grant_name,
                    'expire_at': self._active_grants[grant_idx].expire_at}

        elif action == 'release':
            if grant_idx is None:
                if strict:
                    return {'error': 'Grant is not currently held; cannot release.'}
            else:
                self._active_grants.pop(grant_idx)
                self._update_all()
                self.log.info(f'Exclusive access relinquished: {grant_name}')
            return {'message': 'grant released',
                    'grant_name': grant_name,
                    }

    @inlineCallbacks
    def _simple_stop(self, session, params):
        yield
        if session.status not in ['stopping', 'done']:
            session.set_status('stopping')
            return True, 'Stop initiated.'
        return False, 'Already done/stopping.'


class AccessGrant:
    def __init__(self, name, rules, expire_at, grantee):
        self.name = name
        self.rules = rules
        self.renew(expire_at)
        self.grantee = grantee

    def renew(self, expire_at):
        if expire_at is None:
            expire_at = time.time() + 60
        self.expire_at = expire_at

    def encode(self):
        return {
            'name': self.name,
            'expire_at': self.expire_at,
            'grantee': self.grantee,
            'rules': [access.asdict(r) for r in self.rules],
        }


def make_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--config-file', default=None,
                        help="AccessDirectory config file.")
    return parser


def main(args=None):
    parser = make_parser()
    args = site_config.parse_args(agent_class='AccessDirector',
                                  parser=parser,
                                  args=args)
    config_file = args.config_file
    if config_file[0] != '/':
        # Relative to SCF location.
        config_file = os.path.join(
            os.path.dirname(args.site_file), config_file)

    # Force the access_policy arg to "none", to prevent OCSAgent from
    # stalling, trying to get access passwords from this instance ...
    args.access_policy = 'none'

    agent, runner = ocs_agent.init_site_agent(args)
    access_director = AccessDirector(agent, config_file)

    agent.register_process('manager',
                           access_director.manager,
                           access_director._simple_stop,
                           blocking=False,
                           startup=True)
    agent.register_task('reload_config',
                        access_director.reload_config,
                        blocking=False)
    runner.run(agent, auto_reconnect=True)


if __name__ == '__main__':
    main()
