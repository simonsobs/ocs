import time, threading
from datetime import datetime
import numpy as np
from ocs import ocs_agent, site_config, client_t
import os

from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor

if os.getenv('OCS_DOC_BUILD') != 'True':
    from spt3g import core
    import so3g

class DataAggregator:
    """
    The Data Aggregator Agent listens to data provider feeds, and outputs the housekeeping data as G3Frames.

    Attributes:

        providers (dict):
            The providers attribute stores all info on data providers that
            the aggregator has subscribed to, including the data buffers for
            the provider feeds. It is indexed by the agent_address, and the
            data structure for each provider looks like::

                providers[agent_address]  = {
                    "prov_id": int,
                    "agent_address: string,
                    "buffered": bool if Feed is buffered,
                    "buffer_time":  How long the feed should be buffered before
                                    written to frame [s]
                    "buffer_start_time": Time that the current buffer was started
                    "blocks": {
                        block_name1: {
                            "timestamps": [ list of timestamps ],
                            "data": {
                                key1: [ buffer for key1 ],
                                key2: [ buffer for key2 ]
                            }
                        },

                        block_name2: {
                            "timestamps": [ list of timestamps ],
                            "data": {
                                key3: [ buffer for key3 ]
                            }
                        }
                    }
                }

        next_prov_id (int):
            Stores the prov_id to be used on the next registered agent
        hksess (so3g HKSession):
            The so3g HKSession that generates status, session, and data frames.
        aggregate (bool):
           Specifies if the agent is currently aggregating data.
        filename (str):
            Filename that the current data is writen to.
        writer (G3File):
            Writer for the current G3File
    """

    def __init__(self, agent, time_per_file, data_dir):

        self.agent = agent
        self.log = agent.log

        self.time_per_file = time_per_file
        self.data_dir = data_dir

        self.providers = {} # by agent address
        self.next_prov_id = 0

        self.hksess = so3g.hkagg.HKSession(description="HK data")

        self.aggregate = False

        self.filename = ""
        self.writer = None

    def _data_handler(self, _data):
        """
        Callback for whenever data is published to an aggregator feed.

        If the feed is already buffered, the data handler will immediately
        write it to a G3Frame when this is called.

        If the feed is not buffered, it will add the data-point to the
        buffer in the correct block.
        """
        if not self.aggregate:
            return

        data, feed = _data
        agent_addr = feed["agent_address"]

        prov = self.providers[agent_addr]

        if feed['buffered']:

            # copies feed buffer to provider block
            for d in data:
                block_name = d['block_name']
                block = prov['blocks'][block_name]

                for key in block['data'].keys():
                    block['data'][key].append(d['data'][key])

                block['timestamp'].append(d['timestamp'])

            # Write blocks to file
            self.write_blocks_to_file(prov)

            # Clear block
            for _, block in prov['blocks'].items():
                block['timestamp'] = []
                for key in block['data'].keys():
                    block['data'][key] = []

        else:
            # If not, the aggregator needs to buffer the data itself.
            current_time = time.time()

            if prov['buffer_start_time'] is None:
                prov['buffer_start_time'] = current_time

            # Write data to buffer
            block_name = data['block_name']
            block = prov['blocks'][block_name]

            for key in block['data'].keys():
                block['data'][key].append(data['data'][key])

            block['timestamp'].append(data['timestamp'])

            # If buffer_time has elapsed, write blocks to frame and clear
            elapsed_time = current_time - prov['buffer_start_time']
            if elapsed_time > prov['buffer_time']:
                self.write_blocks_to_file(prov)

                prov['buffer_start_time'] = None

                # Clear block
                for _, block in prov['blocks'].items():
                    block['timestamp'] = []
                    for key in block['data'].keys():
                        block['data'][key] = []

    def create_provider(self, feed, prov_id):
        """
        Creates new provider object from an encoded feed and a prov_id
        """
        prov = {
            'prov_id': prov_id,
            'agent_address': feed['agent_address'],
            'buffer_time': feed['buffer_time'],
            'buffered': feed['buffered'],
            'buffer_start_time': None,
            'blocks': {},
        }
        for (key, block) in feed['agg_params']['blocking'].items():
            prov['blocks'][key] = {
                'prefix': block.get('prefix', ''),
                'timestamp': [],
                'data': {name: [] for name in block['data']}
            }

        return prov

    def _new_agent_handler(self, _data):
        """
            Callback for whenever the registry publishes new agent status.

            If the agent has not yet been subscribed to and has an aggregated
            feed, this will add it to `self.providers` and subscribe to the
            feed.
        """
        (action, agent_data), feed_data = _data
        agent_address = agent_data['agent_address']

        # Finds the aggregated feed if there is one.
        feed = None
        for f in agent_data.get("feeds", []):
            if f["aggregate"]:
                feed = f
                break

        if feed is None:
            #Then there are no aggregated feeds.
            return

        # if feed is already stored in self.providers
        is_registered = agent_address in self.providers.keys()
        if action == 'status' and is_registered:
            # Then aggregator probably called Dump_agents and we only need
            # providers that we have not already registered
            return

        if action == "removed" and is_registered:
            # Writes remaining blocks to file, then
            prov = self.providers[agent_address]
            self.log.info("Removing provider: {}".format(agent_address))

            if (self.writer is not None) and self.aggregate:
                self.write_blocks_to_file(prov)

            self.hksess.remove_provider(prov['prov_id'])
            del(self.providers[agent_address])

            if (self.writer is not None) and self.aggregate:
                status_frame = self.hksess.status_frame()
                self.writer(status_frame)
            return

        if action in ['added', 'updated', 'status']:
            self.log.info("Subscribing to provider {}".format(agent_address))
            if is_registered:
                # Writes all remaining blocks to file in case format is changed.
                self.write_blocks_to_file(self.providers[agent_address])
                prov_id = self.providers[agent_address]['prov_id']
            else:
                prov_id = self.hksess.add_provider(description=agent_address)

            prov = self.create_provider(feed, prov_id)
            self.providers[agent_address] = prov
            self.agent.subscribe_to_feed(agent_address,
                                         feed['feed_name'],
                                         self._data_handler)

            if (self.writer is not None) and self.aggregate and (not is_registered):
                status_frame = self.hksess.status_frame()
                self.writer(status_frame)

    def add_feed(self, session, params={}):
        """
        Task to subscribe to a feed.

        Arguments:
            address (str):
                Full address of the feed
            buffered (bool):
                True if data is buffered by feed and not the aggregator
            buffer_time:
                time to buffer frame before writing to file
            blocking:
                Determines structure of the blocking
        """

        agent_addr, feed_name = params['address'].split('.feeds.')

        # Registers provider
        prov = {
            'prov_id': self.next_prov_id,
            'agent_address': agent_addr,
            'buffer_time': params['buffer_time'],
            'buffered': params['buffered'],
            'buffer_start_time': None,
            'blocks': {},
        }

        for (key, block) in params['blocking'].items():
            prov['blocks'][key] = {
                'prefix': block.get('prefix', ''),
                'timestamp': [],
                'data': {name: [] for name in block['data']}
            }

        self.providers[agent_addr] = prov

        # If feed is already subscribed to, it is already a provider, and we
        # can just update provider info without re-registering with so3g
        # hksess.
        if params['address'] not in self.agent.subscribed_feeds:
            self.next_prov_id += 1
            self.hksess.add_provider(
                prov_id=prov['prov_id'],
                description=prov['agent_address']
            )

            self.agent.subscribe_to_feed(agent_addr,
                                         feed_name,
                                         self._data_handler)

            # Prints status frame to file
            if (self.writer is not None) and self.aggregate:
                status_frame = self.hksess.status_frame()
                self.writer(status_frame)

        return True, "Feed added"

    def initialize(self, session, params={}):
        """
        TASK: Subscribes to `agent_activity` feed and has registry dump
                info on all active agents.
        """
        reg_address = self.agent.site_args.registry_address

        if reg_address is None:
            self.log.warn("No registry address is in site args")
            return True, "Initialized Aggregator"

        self.agent.subscribe_to_feed(reg_address,
                                     'agent_activity',
                                     self._new_agent_handler)

        self.agent.call_op(reg_address, 'dump_agent_info', 'start')

        return True, "Initialized Aggregator"

    def write_blocks_to_file(self, prov):
        frame = self.hksess.data_frame(prov_id=prov["prov_id"])
        non_empty = False
        frame['agent_address'] = prov['agent_address']

        for key, block in prov['blocks'].items():

            # Skip block if empty
            if not block['timestamp']:
                continue
            non_empty = True

            hk = so3g.IrregBlockDouble()
            hk.prefix = block['prefix']
            hk.t = block['timestamp']
            for ts_name, ts in block['data'].items():
                hk.data[ts_name] = ts

            frame['blocks'].append(hk)

        # Only writes frame if there are non-empty blocks
        if non_empty:
            self.writer.Process(frame)

    def start_file(self):
        """
        Starts new G3File with filename `self.filename`.
        """
        print("Creating file: {}".format(self.filename))
        self.writer = core.G3Writer(filename=self.filename)

        session_frame = self.hksess.session_frame()
        status_frame = self.hksess.status_frame()


        self.writer(session_frame)
        self.writer(status_frame)

        return

    def end_file(self):
        """
        Ends current G3File with EndProcessing frame.
        """

        for _, prov in self.providers.items():
            self.write_blocks_to_file(prov)

        self.writer(core.G3Frame(core.G3FrameType.EndProcessing))

        print("Closing file: {}".format(self.filename))
        return

    def start_aggregate(self, session, params={}):
        """
        PROCESS: Starts the aggregation process.

        Args:
            time_per_file (int, optional):
                Specifies how much time should elapse before starting a new
                file (in seconds). Defaults to 1 hr.

            time_per_frame (int, optional):
                Specifies how much time should elapse before starting a new
                frame (in seconds). Defaults to 10 minutes.

            data_dir (string, optional):
                Path of directory to store data. Defaults to 'data/'.
        """
        if params is None:
            params = {}

        time_per_file = params.get("time_per_file", self.time_per_file) # [s]
        data_dir = params.get("data_dir", self.data_dir)

        self.log.info("Starting data aggregation in directory {}".format(data_dir))
        session.set_status('running')

        self.hksess.session_id = session.session_id
        self.hksess.start_time = time.time()

        new_file_time = True

        self.aggregate = True
        while self.aggregate:

            if new_file_time:
                if self.writer is not None:
                    self.end_file()

                file_start_time = datetime.utcnow()
                ts = file_start_time.timestamp()
                sub_dir = os.path.join(data_dir, "{:.5}".format(str(ts)))

                # Create new dir for current day
                if not os.path.exists(sub_dir):
                    os.makedirs(sub_dir)

                time_string = file_start_time.strftime("%Y-%m-%d-%H-%M-%S")
                self.filename = os.path.join(sub_dir, "{}.g3".format(time_string))

                self.start_file()

                session.add_message('Starting a new DAQ file: %s' % self.filename)

            time.sleep(.1)
            # Check if its time to write new frame/file
            new_file_time = (datetime.utcnow().timestamp() - ts) > time_per_file

        self.filename = ""
        self.end_file()
        self.writer = None

        return True, 'Acquisition exited cleanly.'

    def stop_aggregate(self, session, params=None):
        self.aggregate = False
        return (True, "Stopped aggregation")


if __name__ == '__main__':

    parser = site_config.add_arguments()

    # Add options specific to this agent.
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--initial-state', default='idle')
    pgroup.add_argument('--time-per-file', default='3600')
    pgroup.add_argument('--data-dir', default='data/')

    args = parser.parse_args()
    site_config.reparse_args(args, 'AggregatorAgent')

    agent, runner = ocs_agent.init_site_agent(args)

    data_aggregator = DataAggregator(agent, int(args.time_per_file), args.data_dir)

    agent.register_task('initialize', data_aggregator.initialize)
    agent.register_task('add_feed', data_aggregator.add_feed)
    agent.register_process('aggregate', data_aggregator.start_aggregate, data_aggregator.stop_aggregate)

    @inlineCallbacks
    def on_start():
        agent.log.info("Starting aggregator with initial state {}".format(args.initial_state))

        yield agent.call_op(agent.agent_address, 'initialize', 'start')
        yield agent.call_op(agent.agent_address, 'initialize', 'wait')

        if args.initial_state == 'record':
            yield agent.call_op(agent.agent_address, 'aggregate', 'start')

    reactor.callLater(1, on_start)
    runner.run(agent, auto_reconnect=True)
