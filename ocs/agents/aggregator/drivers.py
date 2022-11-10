import os
import binascii
import time

from typing import Dict

import txaio
txaio.use_twisted()

from ocs.ocs_feed import Block, Feed

import so3g
from spt3g import core


HKAGG_VERSION = 2
_g3_casts = {
    str: core.G3String,
    int: core.G3Int,
    float: core.G3Double,
    bool: core.G3Bool,
}
_g3_list_casts = {
    str: core.G3VectorString,
    int: core.G3VectorInt,
    float: core.G3VectorDouble,
    bool: core.G3VectorBool,
}

LOG = txaio.make_logger()


def g3_cast(data, time=False):
    """
    Casts a generic datatype into a corresponding G3 type. With:
        int   -> G3Int
        str   -> G3String
        float -> G3Double
        bool  -> G3Bool

    and lists of type X will go to G3VectorX. If ``time`` is set to True, will
    convert to G3Time or G3VectorTime with the assumption that ``data`` consists
    of unix timestamps.

    Args:
        data (int, str, float, or list):
            Generic data to be converted to a corresponding G3Type.
        time (bool, optional):
            If True, will assume data contains unix timestamps and try to cast
            to G3Time or G3VectorTime.

    Returns:
        g3_data:
            Corresponding G3 datatype.
    """
    is_list = isinstance(data, list)
    if is_list:
        dtype = type(data[0])
        if not all(isinstance(d, dtype) for d in data):
            raise TypeError("Data list contains varying types!")
    else:
        dtype = type(data)
    if dtype not in _g3_casts.keys():
        raise TypeError("g3_cast does not support type {}. Type must "
                        "be one of {}".format(dtype, _g3_casts.keys()))
    if is_list:
        if time:
            return core.G3VectorTime(list(map(
                lambda t: core.G3Time(t * core.G3Units.s), data)))
        else:
            cast = _g3_list_casts[type(data[0])]
            return cast(data)
    else:
        if time:
            return core.G3Time(data * core.G3Units.s)
        else:
            cast = _g3_casts[type(data)]
            return cast(data)


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
            try:
                os.makedirs(subdir)
            except PermissionError as e:
                LOG.error("Permission error encountered while trying to create "
                          f"data sub-directory: {e}")
                raise e
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
            Time (in seconds) before data should be written into a frame. Defaults to 5 min.
        fresh_time (float, optional):
            Time (in seconds) before provider should be considered stale. Defaults to 3 min.

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

    def __init__(self, address, sessid, prov_id, frame_length=5 * 60, fresh_time=3 * 60):
        self.address = address
        self.sessid = sessid
        self.frame_length = frame_length
        self.prov_id = prov_id
        self.log = txaio.make_logger()

        self.blocks = {}

        # When set to True, provider will be written and removed next agg cycle
        self.frame_start_time = None

        self.fresh_time = fresh_time
        self.last_refresh = time.time()  # Determines if
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

    def _verify_provider_data(self, data):
        """Check the provider data for invalid field names. Meant to be used in
        combination with Provider._rebuild_invalid_data().

        Args:
            data (dict): data dictionary passed to Provider.save_to_block()

        Returns:
            bool: True if all field names valid. False if any invalid names found

        """
        verified = True
        for block_name, block_dict in data.items():
            for field_name, field_values in block_dict['data'].items():
                try:
                    Feed.verify_data_field_string(field_name)
                except ValueError:
                    self.log.error("data field name '{field}' is "
                                   + "invalid, removing invalid characters.",
                                   field=field_name)
                    verified = False

        return verified

    @staticmethod
    def _check_for_duplicate_names(field_name, name_list):
        """Check name_list for matching field names and modify field_name if
        matches are found.

        The results of ocs_feed.Feed.enforce_field_name_rules() are not guarenteed
        to be unique. This method will check field_name against a list of
        existing field names and try to append '_N', with N being a zero padded
        integer up to 99. Longer integers, though not expected to see use, are
        also supported, though will not be zero padded.

        In the event the field name is at the maximum allowed length, we remove
        some characters before appending the additional underscore and integer.

        Examples:
            >>> current_field_names = ['test', 'test_01']
            >>> name = 'test'
            >>> new_name = Provider._check_for_duplicate_names(name, current_field_names)
            >>> print(new_name)
            test_02

        Args:
            field_name (str): field name to check against name_lsit
            name_list (list): list of field names already in a Block

        Returns:
            str: A new field name that is not already in name_list

        """
        name_index = 1

        while field_name in name_list:
            suffix = f'_{name_index:02}'
            suf_len = len(suffix)
            field_name = field_name[:255 - suf_len] + suffix
            name_index += 1

        return field_name

    def _rebuild_invalid_data(self, data):
        """Rebuild an invalid data dictionary.

        Args:
            data (dict): data dictionary passed to Provider.save_to_block().

        Returns:
            dict: A rebuilt data dictionary with invalid characters stripped
                  from the field names, limited to 255 characters in length.

        """
        new_data = {}
        for block_name, block_dict in data.items():
            new_data[block_name] = {}
            # rebuild block_dict
            for k, v in block_dict.items():
                if k == 'data':
                    new_data[block_name]['data'] = {}
                    new_field_names = []
                    for field_name, field_values in block_dict['data'].items():
                        new_field_name = Feed.enforce_field_name_rules(field_name)

                        # Catch instance where rule enforcement strips all characters
                        if not new_field_name:
                            new_field_name = Feed.enforce_field_name_rules("invalid_field_" + field_name)

                        new_field_name = Provider._check_for_duplicate_names(new_field_name,
                                                                             new_field_names)

                        new_data[block_name]['data'][new_field_name] = field_values

                        new_field_names.append(new_field_name)
                else:
                    new_data[block_name][k] = v

        return new_data

    def save_to_block(self, data):
        """Saves a list of data points into blocks. A block will be created
        for any new block_name.

        Examples:
            The format of data is shown in the following example:

            >>> data = {'test': {'block_name': 'test',
                             'timestamps': [time.time()],
                             'data': {'key1': [1],
                                      'key2': [2]},
                             }
                       }
            >>> prov.save_to_block(data)

            Note the block name shows up twice, once as the dict key in the
            outer data dictionary, and again under the 'block_name' value.
            These must match -- in this instance both the word 'test'.

        Args:
            data (dict): data dictionary from incoming data queue

        """
        self.refresh()

        if self.frame_start_time is None:
            # Get min frame time out of all blocks
            self.frame_start_time = time.time()
            for _, b in data.items():
                if b['timestamps']:
                    self.frame_start_time = min(self.frame_start_time, b['timestamps'][0])

        self.log.debug('data passed to block: {d}', d=data)
        verified = self._verify_provider_data(data)

        if not verified:
            self.log.info('rebuilding data containing invalid field name')
            data = self._rebuild_invalid_data(data)
            self.log.debug('data after rebuild: {d}', d=data)

        for key, block in data.items():
            try:
                b = self.blocks[key]
            except KeyError:
                self.blocks[key] = Block(
                    key, block['data'].keys(),
                )
                b = self.blocks[key]

            b.extend(block)
            self.last_block_received = key

    def clear(self):
        """Clears all blocks and resets the frame_start_time"""
        for _, b in self.blocks.items():
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

        block_names = []
        for block_name, block in self.blocks.items():
            if not block.timestamps:
                continue
            try:
                m = core.G3TimesampleMap()
                m.times = g3_cast(block.timestamps, time=True)
                for key, ts in block.data.items():
                    m[key] = g3_cast(ts)
            except Exception as e:
                self.log.warn("Error received when casting timestream! {e}",
                              e=e)
                continue
            frame['blocks'].append(m)
            block_names.append(block_name)

        if 'block_names' in frame:
            frame['block_names'].extend(block_names)
        else:
            frame['block_names'] = core.G3VectorString(block_names)

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

    Attributes:
        filename (function):
            Function to call to create new filename on rotation
        file_start_time (int):
            Start time for current file
        writer (core.G3Writer):
            G3Writer object for current file. None if no file is open.
        last_session (core.G3Frame):
            Last session frame written to disk. This is stored and written as
            the first frame on file rotation.
        last_status (core.G3Frame):
            Last status frame written to disk. Stored and written as the second
            frame on file rotation.
        current_file (str, optional):
            Path to the current file being written.
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
    """Data aggregator. This manages a collection of providers, and contains
    methods to write them to disk.

    This class should only be accessed by a single thread. Data can be passed
    to it by appending it to the referenced `incoming_data` queue.

    Args:
        incoming_data (queue.Queue):
            A thread-safe queue of (data, feed) pairs.
        time_per_file (float):
            Time (sec) before a new file should be written to disk.
        data_dir (path):
            Base directory for new files to be written.
        session (OpSession, optional):
            Session object of current agent process. If not specified, session
            data will not be written.

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

        self.hksess = so3g.hk.HKSessionHelper(description="HK data",
                                              hkagg_version=HKAGG_VERSION)
        self.hksess.start_time = time.time()
        self.hksess.session_id = generate_id(self.hksess)

        self.incoming_data = incoming_data

        self.writer = G3FileRotator(
            time_per_file,
            lambda: make_filename(data_dir, make_subdirs=True),
        )
        self.writer.Process([self.hksess.session_frame()])

        self.providers: Dict[Provider] = {}  # by prov_id
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
            agg_params = feed['agg_params']

            if agg_params.get('exclude_aggregator', False):
                continue

            address = feed['address']
            sessid = feed['session_id']

            pid = self.pids.get((address, sessid))
            if pid is None:
                prov_kwargs = {}
                for key in ['frame_length', 'fresh_time']:
                    if key in agg_params:
                        prov_kwargs[key] = agg_params[key]

                pid = self.add_provider(address, sessid, **prov_kwargs)

            prov = self.providers[pid]
            prov.save_to_block(data)

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
        if self.session is not None:
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
