from ocs.ocs_agent import in_reactor_context
from twisted.internet import reactor
from autobahn.wamp.exception import TransportLost
import time
import re


class Block:
    def __init__(self, name, keys):
        """
        Structure of block for a so3g IrregBlockDouble.
        """
        self.name = name
        self.timestamps = []
        self.data = {
            k: [] for k in keys
        }

    def empty(self):
        """ Returns true if block is empty"""
        return self.timestamps == []

    def clear(self):
        """
        Empties block's buffers
        """
        self.timestamps = []
        for key in self.data:
            self.data[key] = []

    def append(self, d):
        """
        Adds a single data point to the block
        """
        if d['data'].keys() != self.data.keys():
            raise Exception("Block structure does not match: {}".format(self.name))

        self.timestamps.append(d['timestamp'])

        for k in self.data:
            self.data[k].append(d['data'][k])

    def extend(self, block):
        """
        Extends the data block by an encoded block
        """
        if block['data'].keys() != self.data.keys():
            raise Exception("Block structure does not match: {}".format(self.name))

        self.timestamps.extend(block['timestamps'])
        for k in self.data:
            self.data[k].extend(block['data'][k])

    def encoded(self):
        n = len(self.timestamps)
        assert (all([n == len(v) for v in self.data.values()]))
        return {
            'block_name': self.name,
            'data': {k: self.data[k] for k in self.data.keys()},
            'timestamps': self.timestamps,
        }


class Feed:
    """
    Manages publishing to a specific feed and storing of messages.

    Args:
        agent (OCSAgent):
            agent that is registering the feed
        feed_name (string):
            name of the feed
        record (bool, optional):
            Determines if feed should be aggregated. At the moment, each agent
            can have at most one aggregated feed. Defaults to False
        agg_params (dict, optional):
            Parameters used by the aggregator and influx publisher.

            Params:
                **frame_length** (float):
                    Deterimes the amount of time each G3Frame should be (in seconds).
                **fresh_time** (float):
                    Time until feed is considered stale by aggregator.
                **exclude_aggregator** (bool):
                    If True, the HK Aggregator will not record feed to g3.
                **exclude_influx** (bool):
                    If True, the InfluxPublisher will not write the feed to
                    Influx.

        buffer_time (int, optional):
            Specifies time that messages should be buffered in seconds.
            If 0, message will be published immediately.
            Defaults to 0.
        max_messages (int, optional):
            Max number of messages stored. Defaults to 20.
    """

    def __init__(self, agent, feed_name, record=False, agg_params={},
                 buffer_time=0, max_messages=0):

        self.agent = agent
        self.feed_name = feed_name
        self.record = record
        self.agg_params = agg_params

        self.buffer_time = buffer_time
        self.buffer_start_time = None

        self.blocks = {}

        self.agent_address = self.agent.agent_address
        self.address = "{}.feeds.{}".format(self.agent_address, self.feed_name)

    def encoded(self):
        return {
            "agent_address": self.agent_address,
            "agg_params": self.agg_params,
            "feed_name": self.feed_name,
            "address": self.address,
            "record": self.record,
            "session_id": self.agent.agent_session_id,
            "agent_class": self.agent.class_name
        }

    def flush_buffer(self):
        """Publishes all messages in buffer and empties it."""

        if not in_reactor_context():
            return reactor.callFromThread(self.flush_buffer)
        if self.buffer_start_time is None:
            return

        if self.record:
            try:
                self.agent.publish(self.address, (
                    {k: b.encoded() for k, b in self.blocks.items() if b.timestamps},
                    self.encoded()
                ))
            except TransportLost:
                self.agent.log.error('Could not publish to Feed. TransportLost. '
                                     + 'crossbar server likely unreachable.')
            for k, b in self.blocks.items():
                b.clear()

    def publish_message(self, message, timestamp=None):
        """
        Publishes message to feed.  If this is an aggregatable feed
        (record=True), then it may be buffered.  Otherwise it is
        dispatched immediately.

        Args:
            message:
                Data to be published (see notes about acceptable formats).
            timestamp (float):
                timestamp given to the message. Defaults to time.time()

        If this feed is not intended to provide structured data for
        aggregation, then the format of the message is unrestricted as
        long as it is WAMP-serializable.

        For aggregated feeds, the message should be a dict with one of
        the following formats:

        1. A single sample for several co-sampled channels.  The
           structure is::

             message = {
                 'block_name': Key given to the block in blocking param
                 'timestamp': timestamp of data
                 'data': {
                      key1: datapoint1
                      key2: datapoint2
                  }
             }

           Samples recorded in this way may be buffered, if
           self.sample_time > 0.

        2. Multiple or more samples for several co-sampled channels.
           The structure is::


             message = {
                 'block_name': Key given to the block in blocking param
                 'timestamps': [timestamp, timestamp...]
                 'data': {
                      key1: [datapoint, datapoint...]
                      key2: [datapoint, datapoint...]
                  }
             }

           Note that the code distinguishes between these cases based
           on the presence of the key 'timestamps' rather than
           'timestamp'.  These data can be buffered, too, if
           self.sample_time > 0.

        """
        current_time = time.time()

        if timestamp is None:
            timestamp = current_time

        if not in_reactor_context():
            # Take a copy, for thread-safety.
            message = message.copy()
            return reactor.callFromThread(self.publish_message, message,
                                          timestamp=timestamp)

        if self.record:
            # check message contents
            for k, v in message['data'].items():
                Feed.verify_data_field_string(k)
                Feed.verify_message_data_type(v)

            # Data is stored in Block objects
            block_name = message['block_name']
            try:
                b = self.blocks[block_name]
            except KeyError:
                b = Block(block_name, message['data'].keys())
                self.blocks[block_name] = b

            if 'timestamp' in message:
                b.append(message)
            elif 'timestamps' in message:
                b.extend(message)
            else:
                raise RuntimeError('Invalid message when record=True.  keys=%s' %
                                   message.keys())

            if self.buffer_start_time is None:
                self.buffer_start_time = current_time

            if (current_time - self.buffer_start_time) >= self.buffer_time:
                self.flush_buffer()
                self.buffer_start_time = None

        else:
            # Publish message immediately
            try:
                self.agent.publish(self.address, (message, self.encoded()))
            except TransportLost:
                self.agent.log.error('Could not publish to Feed. TransportLost. '
                                     + 'crossbar server likely unreachable.')

    @staticmethod
    def verify_message_data_type(value):
        """Aggregated Feeds can only store certain types of data. Here we check
        that the type of all data contained in a message's 'data' dictionary are
        supported types.

        Args:
            value (list, float, int, bool):
                'data' dictionary value published (see Feed.publish_message for details).

        """
        valid_types = (float, int, str, bool)

        # multi-sample check
        if isinstance(value, list):
            if not all(isinstance(x, valid_types) for x in value):
                type_set = set([type(x) for x in value])
                invalid_types = type_set.difference(valid_types)
                raise TypeError("message 'data' block contains invalid data"
                                + f"types: {invalid_types}")

        # single sample check
        else:
            if not isinstance(value, valid_types):
                invalid_type = type(value)
                raise TypeError("message 'data' block contains invalid "
                                + f"data type: {invalid_type}")

    @staticmethod
    def verify_data_field_string(field):
        """There are strict rules for the characters allowed in field names.
        This function verifies the names in a message are valid.

        A valid name:

        * contains only letters (a-z, A-Z; case sensitive), decimal digits (0-9), and the
          underscore (_).
        * begins with a letter, or with any number of underscores followed by a letter.
        * is at least one, but no more than 255, character(s) long.

        Args:
            field (str):
                Field name string to verify.

        Returns:
            bool: True if field name is valid.

        Raises:
            ValueError: If field name is invalid.

        """
        # Check for empty field name
        if not field:
            raise ValueError("Empty field name encountered, please enter "
                             + "a valid field name.")

        # Complement (^) the set, matching any unlisted characters
        check_invalid = re.compile('[^a-zA-Z0-9_]')

        # Similar to check_invalid, search for non letter characters
        # Leading ^ matches the start of string, so following numbers are valid
        check_start = re.compile('^[^a-zA-Z]')

        # check for invalid characters
        result = check_invalid.search(field)
        if result:
            raise ValueError(f"message 'data' block contains the key {field} "
                             f"with the invalid character '{result.group(0)}'. "
                             "Valid characters are a-z, A-Z, 0-9, and underscore.")

        # check for non-letter start, even after underscores
        stripped_key = field.strip("_")
        if check_start.search(stripped_key):
            raise ValueError(f"message 'data' block contains the key {field}, "
                             + "which does not start with a letter (after any "
                             + "number of leading underscores.)")

        # check key length
        if len(field) > 255:
            raise ValueError(f"message 'data' block contains key {field} which "
                             + "exceeds the valid length of 255 characters.")

        return True

    @staticmethod
    def enforce_field_name_rules(field_name):
        """Enforce naming rules for field names.

        A valid name:

        * contains only letters (a-z, A-Z; case sensitive), decimal digits (0-9), and the
          underscore (_).
        * begins with a letter, or with any number of underscores followed by a letter.
        * is at least one, but no more than 255, character(s) long.

        Args:
            field_name (str):
                Field name string to check and modify if needed.

        Returns:
            str: New field name, meeting all above rules. Note this isn't
                 guarenteed to not collide with other field names passed
                 through this method, and that should be checked.

        """
        # check for empty string
        if field_name == "":
            new_field_name = "invalid_field"
        else:
            new_field_name = field_name

        # replace spaces with underscores
        new_field_name = new_field_name.replace(' ', '_')

        # replace invalid characters
        new_field_name = re.sub('[^a-zA-Z0-9_]', '', new_field_name)

        # grab leading underscores
        underscore_search = re.compile('^_*')
        underscores = underscore_search.search(new_field_name).group()

        # remove leading underscores
        new_field_name = re.sub('^_*', '', new_field_name)

        # remove leading non-letters
        new_field_name = re.sub('^[^a-zA-Z]*', '', new_field_name)

        # add underscores back
        new_field_name = underscores + new_field_name

        # limit to 255 characters
        new_field_name = new_field_name[:255]

        return new_field_name
