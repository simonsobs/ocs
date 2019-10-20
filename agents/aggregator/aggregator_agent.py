import time, datetime, binascii, os, queue, argparse
from threading import RLock
from typing import Dict

from ocs import ocs_agent, site_config, ocs_feed
import argparse
if os.getenv('OCS_DOC_BUILD') != 'True':
    from spt3g import core
    import so3g


class Provider:
    """
    Stores data for a single provider (OCS Feed).

    Args:
        addresss (string):
            Full address of the provider
        sessid (string):
            session_id of the provider
        frame_length (float):
            Time before data should be written into a frame
        prov_id (bool):
            id assigned to the provider by the HKSessionHelper

    Attributes:

        blocks (dict):
            All blocks that are written by provider.
        frame_start_time (float):
            Start time of current frame
        fresh_time (float):
            time (in seconds) that the provider can go without data before being
            labeled stale, and scheduled to be removed
        last_refresh (time):
            Time when the provider was last refreshed (either through data or
            agent heartbeat).
    """
    def __init__(self, address, sessid, frame_length, prov_id):
        self.address = address
        self.sessid = sessid
        self.frame_length = frame_length
        self.prov_id = prov_id

        self.blocks = {}

        self._lock = RLock()

        # When set to True, provider will be written and removed next agg cycle
        self.frame_start_time = None

        # 1 min without refresh (data) will mark the provider
        # as stale, and it'll be flushed and removed next cycle.
        self.fresh_time = 3*60
        self.last_refresh = time.time() # Determines if


    def refresh(self):
        """ Refresh provider """
        self.last_refresh = time.time()

    def stale(self):
        """Returns true if provider is stale and should be removed"""
        return (time.time() - self.last_refresh) > self.fresh_time

    def new_frame_time(self):
        """Returns true if its time for a new frame to be written"""
        if self.frame_start_time is None:
            return False

        return (time.time() - self.frame_start_time) > self.frame_length

    def empty(self):
        """Returns true if all blocks are empty"""
        with self._lock:
            for _,b in self.blocks():
                if not b.empty():
                    return False

        return True

    def write(self, data):
        """
        Saves a list of data points into blocks.
        A block will be created for any new block_name.
        """
        self.refresh()
        with self._lock:

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
        """Clears all blocks and resets the frame_start_time"""
        with self._lock:
            for _,b in self.blocks.items():
                b.clear()

            self.frame_start_time = None

    def to_frame(self, hksess=None, clear=False):
        """
        Returns a G3Frame based on the provider's blocks.

        Args:
            hksess (optional):
                If provided, the frame will be based off of hksession's data frame.
                If the data will be put into a clean frame.
            clear (bool):
                Clears provider data if True.

        """
        with self._lock:

            if hksess is not None:
                frame = hksess.data_frame(prov_id=self.prov_id)
            else:
                frame = core.G3Frame(core.G3FrameType.Housekeeping)

            frame['address'] = self.address
            frame['provider_session_id'] = self.sessid

            for block_name, block in self.blocks.items():
                if not block.timestamps:
                    continue

                hk = so3g.IrregBlockDouble()
                hk.prefix = block.prefix
                hk.t = block.timestamps
                for key, ts in block.data.items():
                    hk.data[key] = ts

                frame['blocks'].append(hk)

            if clear:
                self.clear()

            return frame


class G3FileRotator(core.G3Module):
    """
    G3 module which handles file rotation.
    After time_per_file has elapsed, the rotator will end that file and create
    a new file with the `filename` function.
    It will write the last_session and last_status frame to any new file if they
    exist.

    Args:
        time_per_file (float):
            time (seconds) before a new file should be written
        filename (callable):
            function that generates new filenames.
    """
    def __init__(self, time_per_file, filename):
        self.time_per_file = time_per_file
        self.filename = filename

        self.file_start_time = None
        self.writer = None
        self.last_session = None
        self.last_status = None

    def flush(self):
        """Flushes current g3 file to disk"""
        if self.writer is not None:
            self.writer.Flush()

    def Process(self, frame):
        """
        Writes frame to current file. If file has not been started
        or time_per_file has elapsed, file is closed and a new file is created
        by `filename` function passed to constructor
        """
        ftype = frame['hkagg_type']

        if ftype == so3g.HKFrameType.session:
            self.last_session = frame
        elif ftype == so3g.HKFrameType.status:
            self.last_status = frame

        if self.writer is None:
            self.writer = core.G3Writer(self.filename())
            self.file_start_time = time.time()

            if ftype in [so3g.HKFrameType.data, so3g.HKFrameType.status]:
                if self.last_session is not None:
                    self.writer(self.last_session)

            if ftype == so3g.HKFrameType.data:
                if self.last_status is not None:
                    self.writer(self.last_status)

        self.writer(frame)

        if (time.time() - self.file_start_time) > self.time_per_file:
            self.writer = None


class Aggregator:
    """
    The Data Aggregator Agent listens to data provider feeds, and outputs the
    housekeeping data as G3Frames.

    Args:
        args (namespace):
            args from the function's argparser.
        log:
            logger from the agent

    Attributes:

        providers (dict):
            All active providers that the aggregator is subscribed to.
            Indexed by provider id.
        pids (dict):
            Dictionary of provider id's.
            Indexed by provider's (address, sessid).
        hksess (so3g HKSession):
            The so3g HKSession that generates status, session, and data frames.
        aggregate (bool):
           Specifies if the agent is currently aggregating data.
        rotator (G3FileRotator):
            module for writing G3Files.
        frame_queue (queue.Queue):
            queue of frames to be written to disk. Every loop iteration in `run`
            this will be cleared and all frames will be written to disk.
        data_dir (path):
            base directory for hk data.
    """
    def __init__(self, args, log):
        self.log = log
        self.frame_queue = queue.Queue()

        self.data_dir = args.data_dir
        self._loop_time = 1

        self.rotator = G3FileRotator(int(args.time_per_file), self._make_filename)
        self.aggregate = False

        self.providers: Dict[Provider] = {} # by prov_id
        self.pids = {}  # By (address, sessid)

        self.hksess = so3g.hk.HKSessionHelper(description="HK data")

    def _make_filename(self, make_subdirs=True):
        """
        Creates a new filename based on the time and base_dir.
        If make_subdirs is True, all subdirectories will be automatically created.
        I don't think there's any reason that this shouldn't be true...

        Args:
            make_subdirs (bool):
                True if func should automatically create non-existing subdirs.
        """
        start_time = time.time()
        start_datetime = datetime.datetime.fromtimestamp(
            start_time, tz=datetime.timezone.utc
        )

        subdir = os.path.join(self.data_dir, "{:.5}".format(str(start_time)))

        if not os.path.exists(subdir):
            if make_subdirs:
                os.makedirs(subdir)
            else:
                raise FileNotFoundError("Subdir {} does not exist"
                                        .format(subdir))

        time_string = start_datetime.strftime("%Y-%m-%d-%H-%M-%S")
        filename = os.path.join(subdir, "{}.g3".format(time_string))
        self.log.info("Creating file {} ...".format(filename))
        return filename

    def write_status(self):
        """Adds a status frame to the frame_queue"""
        self.frame_queue.put(self.hksess.status_frame())

    def add_provider(self, prov_address, prov_sessid, frame_length):
        """
        Registers a new provider and writes a status frame.

        Args:
            prov_address (str):
                full address of provider
            prov_sessid (str):
                session id of provider
            frame_length (float):
                time (sec) per data frame.
        """
        pid = self.hksess.add_provider(description=prov_address)

        self.providers[pid] = Provider(
            prov_address, prov_sessid, frame_length, pid
        )
        self.log.info("Adding provider {}".format(prov_address))

        self.pids[(prov_address, prov_sessid)] = pid
        self.write_status()

        return pid

    def remove_provider(self, prov):
        """
        Writes remaining provider data to frame and removes provider.

        Args:
            prov (Provider):
                provider object that should be removed.
        """
        pid = prov.prov_id
        addr, sessid = prov.address, prov.sessid

        if not prov.empty():
            self.frame_queue.put(prov.to_frame(self.hksess, clear=False))

        self.hksess.remove_provider(pid)
        del self.providers[pid]
        del self.pids[(addr, sessid)]
        self.write_status()

    def write_data(self, data, pid):
        """
        Writes all blocks in data message to provider

        Args:
            data (list):
                list of Blocks' that should be written to the provider.
            pid (int):
                prov_id of provider
        """
        if not self.aggregate:
            return False

        prov = self.providers[pid]
        prov.write(data)

    def remove_stale_providers(self):
        """
        Loops through all providers and check if they've gone stale.
        If they have, write their remaining data to disk (they shouldn't have any)
        and delete them.
        """
        stale_provs = []

        for pid, prov in self.providers.items():
            if prov.stale():
                self.log.info("Provider {} went stale".format(prov.address))
                stale_provs.append(prov)

        for prov in stale_provs:
            self.remove_provider(prov)

    def write_providers_to_queue(self, clear=True, write_all=False):
        """
        Loop through all providers, and write their data to the frame_queue
        if they have surpassed their frame_time, or if write_all is True.

        Args:
            clear (bool):
                If True, provider data is cleared after write
            write_all (bool):
                If true all providers are written to disk regardless of whether
                frame_time has passed.
        """
        for pid, prov in self.providers.items():
            if write_all or prov.new_frame_time():
                self.frame_queue.put(prov.to_frame(self.hksess, clear=clear))

    def write_queue_to_disk(self):
        """
        Loops through frame_queue and writes them to disk.
        """
        while not self.frame_queue.empty():
            self.rotator.Process(self.frame_queue.get())

    def generate_id(self):
        """
        Generates a unique session id based on the start_time, process_id,
        and hksess description.
        """
        # Maybe this should go directly into HKSessionHelper
        elements = [
            (int(self.hksess.start_time), 32),
            (os.getpid(), 14),
            (binascii.crc32(bytes(self.hksess.description, 'utf8')), 14)
        ]
        agg_session_id = 0
        for i, b in elements:
            agg_session_id = (agg_session_id << b) | (i % (1 << b))
        return agg_session_id

    def run(self):
        """
        Runs aggregation until `stop` is called. This should run in a worker
        thread.
        """
        self.log.info("Aggregator running...")
        self.hksess.start_time = time.time()
        self.hksess.session_id = self.generate_id()

        self.rotator.Process(self.hksess.session_frame())

        self.aggregate = True
        while self.aggregate:
            time.sleep(self._loop_time)

            self.remove_stale_providers()
            self.write_providers_to_queue()
            self.write_queue_to_disk()

            self.rotator.flush()

        self.write_providers_to_queue(write_all=True)
        self.write_queue_to_disk()

        return True

    def stop(self):
        """Signals for aggregation to stop."""
        self.aggregate = False


class AggregatorAgent:
    def __init__(self, agent, args):
        self.agent: ocs_agent.OCSAgent = agent
        self.log = agent.log

        self.aggregator = Aggregator(args, self.log)

        # SUBSCRIBES TO ALL FEEDS!!!!
        # If this ends up being too much data, we can add a tag '.record'
        # at the end of the address of recorded feeds, and filter by that.
        self.agent.subscribe_on_start(self.data_handler,
                                      'observatory..feeds.',
                                      options={'match': 'wildcard'})

        record_on_start = (args.initial_state == 'record')
        self.agent.register_process('record', self.start_aggregate, self.stop_aggregate,
                                    startup=record_on_start)

    def data_handler(self, _data):
        data, feed = _data

        if not feed['record']:
            return

        address = feed['address']
        sessid = feed['session_id']
        frame_length = feed['agg_params']['frame_length']

        pid = self.aggregator.pids.get((address, sessid))

        if pid is None:
            pid = self.aggregator.add_provider(address, sessid, frame_length)

        self.aggregator.write_data(data, pid)

    def start_aggregate(self, session, params=None):
        """
        Process for starting data aggregation
        """
        self.aggregator.run()
        return True, "Aggregation has ended"

    def stop_aggregate(self, session, params=None):
        self.aggregator.stop()
        return True, "Stopping aggregation"


def make_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()

    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--data-dir',
                        help="Base directory to store data. "
                             "Subdirectories will be made here.")
    pgroup.add_argument('--initial-state',
                        default='idle',choices=['idle', 'record'],
                        help="Initial state of argument parser. Can be either"
                             "idle or record")
    pgroup.add_argument('--time-per-file', default='3600',
                        help="Time per file in seconds. Defaults to 1 hr")

    return parser


if __name__ == '__main__':
    parser = site_config.add_arguments()

    parser = make_parser(parser)

    args = parser.parse_args()

    site_config.reparse_args(args, 'AggregatorAgent')

    agent, runner = ocs_agent.init_site_agent(args)

    data_aggregator = AggregatorAgent(agent, args)
    runner.run(agent, auto_reconnect=True)
