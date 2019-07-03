import time, threading
from datetime import datetime
import binascii
import numpy as np
from ocs import ocs_agent, site_config, client_t, ocs_feed
import os

from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor
from threading import RLock

if os.getenv('OCS_DOC_BUILD') != 'True':
    from spt3g import core
    import so3g


class Provider:
    """
    Stores data for a single provider (OCS Feed).

    Attributes:
        addresss (string):
            Full address of the Provider feed
        session_id (string):
            session_id of agent who owns the Feed
        frame_length (float):
            Time before data should be written into a frame
        remove (bool):
            If set true, Provider will be written to disk and deleted
            next iteration of the aggregator
        frame_start_time (float):
            Start time of current frame
        blocks (dict):
            All blocks that are written by provider.
    """
    def __init__(self, feed, prov_id):
        self.prov_id = prov_id

        self.address = feed['address']
        self.session_id = feed['session_id']
        self.frame_length = feed['agg_params']['frame_length']

        self.lock = RLock()

        # When set to True, provider will be written and removed next agg cycle
        self.remove = False
        self.frame_start_time = None
        self.blocks = {}

    def write(self, data):
        """
        Saves a list of data points into blocks.
        A block will be created for any new block_name.
        """

        if self.frame_start_time is None:
            # Get min frame time out of all blocks
            self.frame_start_time = time.time()
            for _,b in data.items():
                if b['timestamps']:
                    self.frame_start_time = min(self.frame_start_time, b['timestamps'][0])

        for key,block in data.items():
            try:
                b = self.blocks[key]
            except KeyError:
                self.blocks[key] = ocs_feed.Block(
                    key, block['data'].keys(),
                    prefix=block['prefix']
                )
                b = self.blocks[key]

            b.extend(block)


    def clear(self):
        """
        Clears all blocks and resets the frame_start_time
        """
        for _,b in self.blocks.items():
            b.clear()

        self.frame_start_time = None

    def to_frame(self, hksess=None):
        """
        Returns a G3Frame based on the provider's blocks.

        Args:
            hksess (optional):
                If provided, the frame will be based off of hksession's data frame.
                If the data will be put into a clean frame.

        """
        if hksess is not None:
            frame = hksess.data_frame(prov_id=self.prov_id)
        else:
            frame = core.G3Frame(core.G3FrameType.Housekeeping)

        frame['address'] = self.address
        frame['session_id'] = self.session_id

        for block_name, block in self.blocks.items():
            if not block.timestamps:
                continue

            hk = so3g.IrregBlockDouble()
            hk.prefix = block.prefix
            hk.t = block.timestamps
            for key, ts in block.data.items():
                hk.data[key] = ts

            frame['blocks'].append(hk)

        return frame


class DataAggregator:
    """
    The Data Aggregator Agent listens to data provider feeds, and outputs the housekeeping data as G3Frames.

    Attributes:

        providers (dict):
            All active providers that the aggregator is subscribed to.
        next_prov_id (int):
            Stores the prov_id to be used on the next registered agent
        hksess (so3g HKSession):
            The so3g HKSession that generates status, session, and data frames.
        aggregate (bool):
           Specifies if the agent is currently aggregating data.
        writer (G3File):
            Writer for the current G3File
    """

    def __init__(self, agent, time_per_file, data_dir):

        self.agent = agent
        self.log = agent.log

        self.time_per_file = time_per_file
        self.data_dir = data_dir

        self.providers = {} # by prov_id
        self.prov_ids = {} # by (address, session_id)
        self.next_prov_id = 0

        self.should_write_status =False
        self.hksess = so3g.hk.HKSessionHelper(description="HK data")

        self.aggregate = False
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
        prov_id = self.prov_ids[(feed["address"], feed["session_id"])]
        prov = self.providers[prov_id]

        prov.lock.acquire()
        prov.write(data)
        prov.lock.release()

    def _new_agent_handler(self, _data):
        """
            Callback for whenever the registry publishes new agent status.

            If the agent has not yet been subscribed to and has an aggregated
            feed, this will add it to `self.providers` and subscribe to the
            feed.
        """

        (action, agent_data), feed_data = _data
        agent_address = agent_data['agent_address']
        session_id = agent_data['session_id']

        self.log.debug("Agent activity --- Agent: {}, session_id: {}, action: {}"
                      .format(agent_address, session_id, action))

        for feed in agent_data['feeds']:
            if not feed['record']:
                continue

            pid = self.prov_ids.get((feed["address"], session_id))
            if pid is not None:
                prov = self.providers[pid]
            else:
                prov = None

            if action == 'removed' and prov is not None:
                self.log.info("Scheduled remove for provider {} ({})"
                              .format(feed['address'], session_id))
                prov.remove = True

            if action in ['added', 'status']:
                if prov is not None:
                    self.log.warn("Provider {} ({}) already exists.".format(feed['address'], session_id))
                    return

                prov_id = self.hksess.add_provider(
                    description="{}".format(feed['address'])
                )
                self.providers[prov_id] = Provider(feed, prov_id)
                self.prov_ids[(feed["address"], session_id)] = prov_id
                self.log.info("Added provider {} (session_id: {}) with id {}"
                              .format(feed['address'], session_id, prov_id))
                self.should_write_status = True
                self.agent.subscribe_to_feed(agent_address,
                                             feed['feed_name'],
                                             self._data_handler)

    def add_feed(self, session, params={}):
        """
        Task to subscribe to a feed.

        Arguments:
            address (str):
                Full address of the feed
            frame_length:
                Time before frames should be written to disk
        """
        agent_addr, feed_name = params['address'].split('.feeds.')
        prov_id = self.hksess.add_provider(
            description="{}".format(params['address'])
        )

        x = {
            'session_id': -1,
            'address': params['address'],
            'frame_length': params['frame_length'],
        }

        self.providers[prov_id] = Provider(x, prov_id)
        self.agent.subscribe_to_feed(agent_addr,
                                     feed_name,
                                     self._data_handler)
        self.should_write_status = True
        return True, "Feed added"

    def initialize(self, session, params=None):
        """TASK: Subscribes to `agent_activity` feed and has registry dump
        info on all active agents.  Optionally starts the "record"
        Process.

        ``params`` is a dict with the following keys:

        - 'start_record' (bool, optional): Default is False.  If True,
            start the "record" Process after performing registration.
        """
        if params is None:
            params = {}

        reg_address = self.agent.site_args.registry_address

        if reg_address is None:
            self.log.warn("No registry address is in site args")
            return True, "Initialized Aggregator"

        self.agent.subscribe_to_feed(reg_address,
                                     'agent_activity',
                                     self._new_agent_handler)

        self.agent.call_op(reg_address, 'dump_agent_info', 'start')

        if params.get('start_record', False):
            self.agent.start('record')

        return True, "Initialized Aggregator"

    def start_file(self, data_dir):
        """
        Starts new G3File with in directory `data_dir`.
        """

        file_start_time = datetime.utcnow()
        timestamp = file_start_time.timestamp()
        sub_dir = os.path.join(data_dir, "{:.5}".format(str(timestamp)))

        # Create new dir for current day
        if not os.path.exists(sub_dir):
            os.makedirs(sub_dir)

        time_string = file_start_time.strftime("%Y-%m-%d-%H-%M-%S")
        filename = os.path.join(sub_dir, "{}.g3".format(time_string))

        self.log.info("Creating file: {}".format(filename))
        self.writer = core.G3Writer(filename)

        session_frame = self.hksess.session_frame()
        self.writer(session_frame)

        self.write_status()

    def write_status(self):
        """
        Writes hksess status frame to disk and sets write_status flag to False
        """
        if self.writer is None:
            return

        status = self.hksess.status_frame()
        self.writer(status)
        self.should_write_status = False

    def end_file(self):
        """
        Writes all non-empty providers to disk, clears them,
        and then writes an EndProcessing frame
        """
        self.log.info("Ending file")

        for pid, prov in self.providers.items():
            if prov.frame_start_time is None:
                continue

            with prov.lock:
                frame = prov.to_frame(self.hksess)
                prov.clear()

            self.writer(frame)

        self.writer(core.G3Frame(core.G3FrameType.EndProcessing))
        self.writer = None

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

        self.hksess.start_time = time.time()
        # Encode a suitable agg_session_id.  if 1:
        elements = [(int(self.hksess.start_time), 32),
                    (os.getpid(), 14),
                    (binascii.crc32(bytes(self.hksess.description, 'utf8')), 14)]
        agg_session_id = 0
        for i, b in elements:
            agg_session_id = (agg_session_id << b) | (i % (1<<b))
        self.log.info("New aggregator session_id=%i" % agg_session_id)
        # The cast here to G3Int can be dropped in the future -- spt3g
        # was updated on May 1 2019 to handle direct puts of int64_t.
        self.hksess.session_id = core.G3Int(agg_session_id)

        new_file_time = True

        self.aggregate = True

        while self.aggregate:
            time.sleep(1)

            if new_file_time:
                if self.writer is not None:
                    self.end_file()
                self.start_file(data_dir)
                ts = datetime.utcnow().timestamp()

            # Removes old providers if new ones exist
            keys = sorted(self.prov_ids, key=lambda x: x[1], reverse=True)
            feeds = []
            for k in keys:
                if k[0] in feeds:
                    prov = self.providers[self.prov_ids[k]]
                    if not prov.remove:
                        print("Newer {} feed found".format(k[0]))
                        prov.remove = True
                else:
                    feeds.append(k[0])

            to_remove = [p for _, p in self.providers.items() if p.remove]
            if to_remove != []:
                self.should_write_status = True

            # If any providers have been removed, write those to disk first
            # And remove provider from hksess
            prov : Provider
            for prov in to_remove:
                if prov.frame_start_time is not None:
                    with prov.lock:
                        frame = prov.to_frame(self.hksess)
                        prov.clear()
                    self.writer(frame)

                self.log.info("Removing provider {} with session_id {}"
                              .format(prov.address, prov.session_id))
                pid = prov.prov_id
                self.hksess.remove_provider(pid)
                del self.providers[pid]
                del self.prov_ids[(prov.address, prov.session_id)]

            # Then write status if we need to
            if self.should_write_status:
                self.write_status()

            # Write to disk any active providers that have surpassed frame_length
            for pid, prov in self.providers.items():
                if prov.frame_start_time is None:
                    continue

                if prov.remove or (time.time() - prov.frame_start_time > prov.frame_length):
                    with prov.lock:
                        frame = prov.to_frame(self.hksess)
                        prov.clear()
                    self.writer(frame)


            # Check if its time to write new frame/file
            new_file_time = (datetime.utcnow().timestamp() - ts) > time_per_file

        self.end_file()
        return True, 'Acquisition exited cleanly.'

    def stop_aggregate(self, session, params=None):
        self.aggregate = False
        return (True, "Stopped aggregation")


if __name__ == '__main__':
    parser = site_config.add_arguments()

    # Add options specific to this agent.
    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--initial-state', default='idle',
                        choices=['idle', 'record'])
    pgroup.add_argument('--time-per-file', default='3600')
    pgroup.add_argument('--data-dir', default='data/')

    args = parser.parse_args()
    site_config.reparse_args(args, 'AggregatorAgent')

    agent, runner = ocs_agent.init_site_agent(args)

    data_aggregator = DataAggregator(agent, int(args.time_per_file), args.data_dir)

    # Run 'initialize' Task and start 'record' Process?
    init_params = False
    if args.initial_state == 'record':
        init_params = {'start_record': True}

    agent.register_task('initialize', data_aggregator.initialize,
                        blocking=False, startup=init_params)
    agent.register_task('add_feed', data_aggregator.add_feed)
    agent.register_process('record', data_aggregator.start_aggregate, data_aggregator.stop_aggregate)

    runner.run(agent, auto_reconnect=True)
