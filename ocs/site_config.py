import ocs

import socket
import os
import yaml
    
class SiteConfig:
    def __init__(self):
        self.hosts = {}
        self.hub = None

    @classmethod
    def from_dict(cls, data):
        """
        Args:
            data: The configuration dictionary.

        The configuration dictionary should have the following elements:

        - ``hub`` (required): Describes what WAMP server and realm
          Agents and Clients should use.
        - ``hosts`` (required): A dictionary of HostConfig
            descriptions.  The keys in this dictionary can be real
            host names on the network, or pseudo-host names if needed.
        """
        self = cls()
        for k,v in data.get('hosts', {}).items():
            assert (k not in self.hosts) # duplicate host name in config file!
            self.hosts[k] = HostConfig.from_dict(v, parent=self)
        self.hub = HubConfig.from_dict(data['hub'], parent=self)
        return self
        
    @classmethod
    def from_yaml(cls, filename):
        with open(filename) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

class HostConfig:
    def __init__(self):
        self.instances = []
 
    @classmethod
    def from_dict(cls, data, parent=None):
        """
        Args:
            data: The configuration dictionary.
            parent: the SiteConfig from which this data was extracted
                (this is stored as self.parent, but not used).

        The configuration dictionary should have the following elements:
       
        - ``agent-instances`` (required): A list of AgentConfig
            descriptions.
        """
        self = cls()
        self.parent = parent
        self.data = data
        self.instances = data['agent-instances']
        return self

class HubConfig:
    @classmethod
    def from_dict(cls, data, parent=None):
        """
        Args:
            data: The configuration dictionary.
            parent: the SiteConfig from which this data was extracted
                (this is stored as self.parent, but not used).

        The configuration dictionary should have the following elements:

        - ``wamp_server`` (required): Address of the WAMP server
            (e.g. ws://host-1:8001/ws).
        - ``wamp_realm`` (required): Name of the WAMP realm to use.
        - ``address_root`` (required): Root to use when constructing
            agent addresses.  Do not include trailing '.'.
        """
        self = cls()
        self.parent = parent
        self.data = data
        return self

class InstanceConfig:
    def __init__(self):
        self.arguments = []

    @classmethod
    def from_dict(cls, data, parent=None):
        """
        Args:
            data: The configuration dictionary.
            parent: the HostConfig from which this data was extracted
                (this is stored as self.parent, but not used).

        The configuration dictionary should have the following elements:
       
        - ``instance-id`` (required): This string is used to set the
            Agent instance's base address.  This may also be matched
            against the instance-id provided by the Agent instance, as
            a way of finding the right InstanceConfig.
        - ``agent-class`` (optional): Name of the Agent class.  This
            may be matched against the agent_class name provided by
            the Agent instance, as a way of finding the right
            InstanceConfig.
        - ``arguments`` (optional): A list of arguments that should be
            passed back to the agent.
        """
        self = cls()
        self.parent = parent
        self.data = data
        self.arguments = self.data['arguments']
        return self

    
    
def add_arguments(parser=None):
    """
    Add OCS site_config options to an ArgumentParser.

    Args:
        parser: an ArgumentParser.  If this is None, a new parser is
            created.

    Returns:
        The ArgumentParser that was passed in, or the new one.

    The arguments added are:

    ``--site=...``
        Instead of the default site, use the configuration
        for the specified site.  The configuration is loaded from
        ``$OCS_CONFIG_DIR/{site}.yaml``.

    ``--site-file=...``
        Instead of the default site config, use the
        specified file.  Full path must be specified.

    ``--site-host=...``
        Override the OCS determination of what host this instance is
        running on, and instead use the configuration for the
        indicated host.

    ``--site-hub=...``:
        Override the ocs hub url (wamp_server).

    ``--site-realm=...``:
        Override the ocs hub realm (wamp_realm).

    ``--instance-id=...``:
        Look in the SCF for Agent-instance specific configuration
        options, and use those to launch the Agent.

    ``--address-root=...``:
        Override the site default address root.
    """
    if parser is None:
        import argparse
        parser = argparse.ArgumentParser()
    group = parser.add_argument_group('Site Config Options')
    group.add_argument('--site')
    group.add_argument('--site-file')
    group.add_argument('--site-host')
    group.add_argument('--site-hub')
    group.add_argument('--site-realm')
    group.add_argument('--instance-id')
    group.add_argument('--address-root')
    return parser
    
def get_config(args, agent_class=None):
    """
    Args:
        args: The argument object returned by
            ArgumentParser.parse_args(), or equivalent.  It is assumed
            that all properties defined by "add_arguments" are present
            in this object.
        agent_class: Class name passed in to match against the list of
            device classes in each host's list.

    Special values accepted for agent_class:
    - '*control*': do not insist on matching host or device.

    Returns:
        The tuple (site_config, host_config, device_config).
    """
    site_file = args.site_file
    site = args.site
    if site_file is None:
        if site is None:
            site = 'default'
        assert (os.getenv('OCS_CONFIG_DIR') is not None)
        site_file = os.path.join(os.getenv('OCS_CONFIG_DIR'),
                                 site + '.yaml')
    else:
        assert (site is None) # do not pass both --site and --site-file

    # Load the site config file.
    site_config = SiteConfig.from_yaml(site_file)

    # Override the WAMP hub?
    if args.site_hub is not None:
        site_config.hub.data['wamp_server'] = args.site_hub

    # Override the realm?
    if args.site_realm is not None:
        site_config.hub.data['wamp_realm'] = args.site_realm

    # Matching behavior.
    no_dev_match = (agent_class == '*control*')

    # Identify our host.
    host = args.site_host
    if host is None:
        host = socket.gethostname()

    if no_dev_match:
        host_config = None
    else:
        host_config = site_config.hosts[host]

    # Identify our agent-instance.
    instance_config = None
    if no_dev_match:
        pass
    elif args.instance_id is not None:
        # Find the config for this instance-id.
        for dev in host_config.instances:
            if dev['instance-id'] == args.instance_id:
                instance_config = InstanceConfig.from_dict(
                    dev, parent=host_config)
                break
    else:
        # Use the agent_class to figure it out...
        matches = 0
        for dev in host_config.instances:
            if dev['agent-class'] == agent_class:
                if instance_config is not None:
                    raise RuntimeError("Multiple matches found for "
                                       "agent-class=%s" % agent_class)
                instance_config = InstanceConfig.from_dict(
                    dev, parent=host_config)
    if instance_config is None and not no_dev_match:
        raise RuntimeError("Could not find matching device description.")

    return (site_config, host_config, instance_config)

def reparse_args(args, agent_class=None):
    """
    Process the site-config arguments, and modify them in place
    according to the agent-instance's computed instance-id.

    Args:
        args: The argument object returned by
            ArgumentParser.parse_args(), or equivalent.

        agent_class: Class name passed in to match against the list of
            device classes in each host's list.

    Special values accepted for agent_class:
    - '*control*': do not insist on matching host or device.
    """
    site, host, instance = get_config(args, agent_class=agent_class)

    if args.site_hub is None:
        args.site_hub = site.hub.data['wamp_server']
    if args.site_realm is None:
        args.site_realm = site.hub.data['wamp_realm']
    if args.address_root is None:
        args.address_root = site.hub.data['address_root']

    if instance is not None:
        if args.instance_id is None:
            args.instance_id = instance.data['instance-id']

        for k,v in instance.data['arguments']:
            kprop = k.lstrip('-').replace('-','_')
            setattr(args, kprop, v)

    return args
