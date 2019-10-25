import time, datetime, binascii, os, queue, argparse, collections
import txaio
from typing import Dict

from ocs import ocs_agent, site_config, ocs_feed
import argparse
if os.getenv('OCS_DOC_BUILD') != 'True':
    from spt3g import core
    import so3g


def generate_id(hksess):
    """
    Generates a unique session id based on the start_time, process_id,
    and hksess description.

    Args:
        hksess (so3g.HKSessionHelper)
    """
    # Maybe this should go directly into HKSessionHelper
    elements = [
        (int(hksess.start_time), 32),
        (os.getpid(), 14),
        (binascii.crc32(bytes(hksess.description, 'utf8')), 14)
    ]
    agg_session_id = 0
    for i, b in elements:
        agg_session_id = (agg_session_id << b) | (i % (1 << b))
    return agg_session_id


def make_filename(base_dir, make_subdirs=True):
    """
    Creates a new filename based on the time and base_dir.
    If make_subdirs is True, all subdirectories will be automatically created.
    I don't think there's any reason that this shouldn't be true...

    Args:
        base_dir (path):
            Base path where data should be written.
        make_subdirs (bool):
            True if func should automatically create non-existing subdirs.
    """
    start_time = time.time()
    start_datetime = datetime.datetime.fromtimestamp(
        start_time, tz=datetime.timezone.utc
    )

    subdir = os.path.join(base_dir, "{:.5}".format(str(start_time)))

    if not os.path.exists(subdir):
        if make_subdirs:
            os.makedirs(subdir)
        else:
            raise FileNotFoundError("Subdir {} does not exist"
                                    .format(subdir))

    time_string = start_datetime.strftime("%Y-%m-%d-%H-%M-%S")
    filename = os.path.join(subdir, "{}.g3".format(time_string))
    return filename


class Provider:
    """
    Stores data for a single provider (OCS Feed).
    This class should only be accessed via a single thread.

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

        # When set to True, provider will be written and removed next agg cycle
        self.frame_start_time = None

        # 1 min without refresh (data) will mark the provider
        # as stale, and it'll be flushed and removed next cycle.
        self.fresh_time = 3*60
        self.last_refresh = time.time() # Determines if


    def refresh(self):
        """Refresh provider"""
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
        for _, b in self.blocks.items():
            if not b.empty():
                return False

        return True

    def write(self, data):
        """
        Saves a list of data points into blocks.
        A block will be created for any new block_name.
        """
        self.refresh()

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

    This class should only be accessed via a single thread.

    Args:
        time_per_file (float):
            time (seconds) before a new file should be written
        filename (callable):
            function that generates new filenames.
    """
    def __init__(self, time_per_file, filename):
        self.time_per_file = time_per_file
        self.filename = filename
        self.log = txaio.make_logger()

        self.file_start_time = None
        self.writer = None
        self.last_session = None
        self.last_status = None

    def close_file(self):
        if self.writer is not None:
            self.writer(core.G3Frame(core.G3FrameType.EndProcessing))
            self.writer = None

    def flush(self):
        """Flushes current g3 file to disk"""
        if self.writer is not None:
            self.writer.Flush()

    def Process(self, frames):
        """
        Writes frame to current file. If file has not been started
        or time_per_file has elapsed, file is closed and a new file is created
        by `filename` function passed to constructor
        """
        for frame in frames:

            ftype = frame['hkagg_type']

            if ftype == so3g.HKFrameType.session:
                self.last_session = frame
            elif ftype == so3g.HKFrameType.status:
                self.last_status = frame

            if self.writer is None:
                filename = self.filename()
                self.log.info("Creating file: {}".format(filename))
                self.writer = core.G3Writer(filename)
                self.file_start_time = time.time()

                if ftype in [so3g.HKFrameType.data, so3g.HKFrameType.status]:
                    if self.last_session is not None:
                        self.writer(self.last_session)

                if ftype == so3g.HKFrameType.data:
                    if self.last_status is not None:
                        self.writer(self.last_status)

            self.writer(frame)

        if (time.time() - self.file_start_time) > self.time_per_file:
            self.close_file()

        return frames


class Aggregator:
    """
    Data aggregator. This manages a collection or providers, and contains
    methods to write to them and write them to disk.

    This class should only be accessed by a single thread. Data can be passed
    to it by appending it to the referenced `incoming_data` queue.

    Args:
        incoming_data (queue.Queue):
            A thread-safe queue of (data, feed) pairs.
        time_per_file (float):
            Time (sec) before a new file should be written to disk.
        data_dir (path):
            Base directory for new files to be written.

    Attributes:
        log (txaio.Logger):
            txaio logger
        hksess (so3g.HKSessionHelper):
            HKSession helper that assigns provider id's to providers,
            and constructs so3g frames.
        writer (G3Module):
            Module to use to write frames to disk.
        providers (Dict[Provider]):
            dictionary of active providers, indexed by the hksess's assigned
            provider id.
        pids (Dict[Int]):
            Dictionary of provider id's assigned by the hksession. Indexed
            by (prov address, session_id).
        write_status (bool):
            If true, a status frame will be written next time providers are
            written to disk. This is set to True whenever a provider is added
            or removed.
    """
    def __init__(self, incoming_data, time_per_file, data_dir):
        self.log = txaio.make_logger()

        self.hksess = so3g.hk.HKSessionHelper(description="HK data")
        self.hksess.start_time = time.time()
        self.hksess.session_id = generate_id(self.hksess)

        self.incoming_data = incoming_data

        self.writer = G3FileRotator(
            time_per_file,
            lambda: make_filename(data_dir, make_subdirs=True),
        )
        self.writer.Process([self.hksess.session_frame()])

        self.providers: Dict[Provider] = {} # by prov_id
        self.pids = {}  # By (address, sessid)

        self.write_status = False

    def process_incoming_data(self):
        """
        Takes all data from the incoming_data queue, and puts them into
        provider blocks.
        """
        while not self.incoming_data.empty():

            data, feed = self.incoming_data.get()

            address = feed['address']
            sessid = feed['session_id']
            frame_length = feed['agg_params']['frame_length']

            pid = self.pids.get((address, sessid))
            if pid is None:
                pid = self.add_provider(address, sessid, frame_length)

            prov = self.providers[pid]
            prov.write(data)

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
        self.write_status = True
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
            self.writer.Process([prov.to_frame(self.hksess, clear=False)])

        self.log.info("Removing provider {}".format(prov.address))
        self.hksess.remove_provider(pid)
        del self.providers[pid]
        del self.pids[(addr, sessid)]
        self.write_status = True

    def remove_stale_providers(self):
        """
        Loops through all providers and check if they've gone stale. If they
         have, write their remaining data to disk (they shouldn't have any)
        and delete them.
        """
        stale_provs = []

        for pid, prov in self.providers.items():
            if prov.stale():
                self.log.info("Provider {} went stale".format(prov.address))
                stale_provs.append(prov)

        for prov in stale_provs:
            self.remove_provider(prov)

    def write_to_disk(self, clear=True, write_all=False):
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

        frames = []

        if self.write_status:
            frames.append(self.hksess.status_frame())
            self.write_status = False

        for pid, prov in self.providers.items():
            if prov.empty():
                continue
            if write_all or prov.new_frame_time():
                frames.append(prov.to_frame(self.hksess, clear=clear))

        self.writer.Process(frames)

    def run(self):
        """
        Main run iterator for the aggregator. This processes all incoming data,
        removes stale providers, and writes active providers to disk.
        """
        self.process_incoming_data()
        self.remove_stale_providers()
        self.write_to_disk()
        self.writer.flush()

    def close(self):
        """Flushes all remaining providers and closes file."""
        self.write_to_disk(write_all=True)
        self.writer.close_file()


class AggregatorAgent:
    """
    This class provide a WAMP wrapper for the data aggregator. The run function
    and the data handler **are** thread-safe, as long as multiple run functions
    are not started at the same time, which should be prevented through OCSAgent.

    Args:
        agent (OCSAgent):
            OCS Agent object
        args (namespace):
            args from the function's argparser.

    Attributes:
        time_per_file (int):
            Time (sec) before files should be rotated.
        data_dir (path):
            Path to the base directory where data should be written.
        aggregate (bool):
           Specifies if the agent is currently aggregating data.
        incoming_data (queue.Queue):
            Thread-safe queue where incoming (data, feed) pairs are stored before
            being passed to the Aggregator.
        loop_time (float):
            Time between iterations of the run loop.
    """
    def __init__(self, agent, args):
        self.agent: ocs_agent.OCSAgent = agent
        self.log = agent.log

        self.time_per_file = int(args.time_per_file)
        self.data_dir = args.data_dir

        self.aggregate = False
        self.incoming_data = queue.Queue()
        self.loop_time = 1

        # SUBSCRIBES TO ALL FEEDS!!!!
        # If this ends up being too much data, we can add a tag '.record'
        # at the end of the address of recorded feeds, and filter by that.
        self.agent.subscribe_on_start(self.enqueue_incoming_data,
                                      'observatory..feeds.',
                                      options={'match': 'wildcard'})

        record_on_start = (args.initial_state == 'record')
        self.agent.register_process('record',
                                    self.start_aggregate, self.stop_aggregate,
                                    startup=record_on_start)

    def enqueue_incoming_data(self, _data):
        """
        Data handler for all feeds. This checks to see if the feeds should
        be recorded, and if they are it puts them into the incoming_data queue
        to be processed by the Aggregator during the next run iteration.
        """
        data, feed = _data

        if not feed['record'] or not self.aggregate:
            return

        self.incoming_data.put((data, feed))

    def start_aggregate(self, session: ocs_agent.OpSession, params=None):
        """
        Process for starting data aggregation. This process will create an
        Aggregator instance, which will collect and write provider data to disk
        as long as this process is running.
        """
        session.set_status('starting')
        self.aggregate = True

        aggregator = Aggregator(self.incoming_data, self.time_per_file, self.data_dir)

        session.set_status('running')
        while self.aggregate:
            time.sleep(self.loop_time)
            aggregator.run()

        aggregator.close()

        return True, "Aggregation has ended"

    def stop_aggregate(self, session, params=None):
        session.set_status('stopping')
        self.aggregate = False
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
