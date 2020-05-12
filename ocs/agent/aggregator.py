import os
import datetime
import binascii
import time

from typing import Dict

import txaio

from ocs import ocs_feed

if os.getenv('OCS_DOC_BUILD') != 'True':
    from spt3g import core
    import so3g
    G3Module = core.G3Module
else:
    # Alias classes that are needed for clean import in docs build.
    G3Module = object


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

    subdir = os.path.join(base_dir, "{:.5}".format(str(start_time)))

    if not os.path.exists(subdir):
        if make_subdirs:
            os.makedirs(subdir)
        else:
            raise FileNotFoundError("Subdir {} does not exist"
                                    .format(subdir))

    time_string = int(start_time)
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
        prov_id (bool):
            id assigned to the provider by the HKSessionHelper
        frame_length (float, optional):
            Time before data should be written into a frame. Defaults to 5 min.
        fresh_time (float, optional):
            Time before provider should be considered stale. Defaults to 3 min.

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
        last_block_received (str):
            String of the last block_name received.

        log (txaio.Logger):
            txaio logger

    """
    def __init__(self, address, sessid, prov_id, frame_length=5*60, fresh_time=3*60):
        self.address = address
        self.sessid = sessid
        self.frame_length = frame_length
        self.prov_id = prov_id
        self.log = txaio.make_logger()

        self.blocks = {}

        # When set to True, provider will be written and removed next agg cycle
        self.frame_start_time = None

        self.fresh_time = fresh_time
        self.last_refresh = time.time() # Determines if
        self.last_block_received = None

    def encoded(self):
        return {
            'last_refresh': self.last_refresh,
            'sessid': self.sessid,
            'stale': self.stale(),
            'last_block_received': self.last_block_received
        }

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
            self.last_block_received = key

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
                try:
                    hk.data[key] = ts
                except TypeError:
                    all_types = set([type(x) for x in ts])
                    self.log.error("datapoint passed from address " +
                                   "{a} to the Provider feed is of " +
                                   "invalid type. Types contained " +
                                   "in the passed list are {t}",
                                   a=self.address, t=all_types)
                    self.log.error("full data list for {k}: {d}",
                                   k=key, d=ts)

            frame['blocks'].append(hk)

        if clear:
            self.clear()

        return frame


class G3FileRotator(G3Module):
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
        self.current_file = None

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
                self.current_file = self.filename()
                self.log.info("Creating file: {}".format(self.current_file))
                self.writer = core.G3Writer(self.current_file)
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
    def __init__(self, incoming_data, time_per_file, data_dir, session=None):
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
        self.provider_archive: Dict[Provider] = {}

        self.write_status = False
        self.session = session

    def process_incoming_data(self):
        """
        Takes all data from the incoming_data queue, and puts them into
        provider blocks.
        """
        while not self.incoming_data.empty():

            data, feed = self.incoming_data.get()

            address = feed['address']
            sessid = feed['session_id']

            pid = self.pids.get((address, sessid))
            if pid is None:
                pid = self.add_provider(address, sessid, **feed['agg_params'])

            prov = self.providers[pid]
            prov.write(data)

    def add_provider(self, prov_address, prov_sessid, **prov_kwargs):
        """
        Registers a new provider and writes a status frame.

        Args:
            prov_address (str):
                full address of provider
            prov_sessid (str):
                session id of provider

        Optional Arguments:
            Additional kwargs are passed directly to the Provider constructor,
            so defaults are set there.
        """
        pid = self.hksess.add_provider(description=prov_address)

        self.providers[pid] = Provider(
            prov_address, prov_sessid, pid, **prov_kwargs
        )
        self.provider_archive[prov_address] = self.providers[pid]

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

        self.session.data = {
            'current_file': self.writer.current_file,
            'providers': {}
        }
        for addr, prov in self.provider_archive.items():
            self.session.data['providers'][addr] = prov.encoded()


    def close(self):
        """Flushes all remaining providers and closes file."""
        self.write_to_disk(write_all=True)
        self.writer.close_file()
