from ocs.ocs_agent import in_reactor_context
from twisted.internet import reactor
import time

class Block:
    def __init__(self, name, keys, prefix=''):
        """
        Structure of block for a so3g IrregBlockDouble.
        """
        self.name = name
        self.prefix = prefix
        self.timestamps = []
        self.data = {
            k: [] for k in keys
        }

    def clear(self):
        """
        Empties block's buffers
        """
        self.timestamps = []
        for key in self.data:
            self.data[key] = []

    def add(self, d):
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
        return {
            'name': self.name,
            'data': {k: self.data[k] for k in self.data.keys()},
            'timestamps': self.timestamps,
            'prefix': self.prefix
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
            Parameters used by the aggregator.

            Params:
                **frame_length** (float):
                    Deterimes the amount of time each G3Frame should be (in seconds).

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
        self.buffer = []

        self.max_messages = max_messages
        self.messages = []

        self.agent_address = self.agent.agent_address
        self.address = "{}.feeds.{}".format(self.agent_address, self.feed_name)

    def encoded(self):
        return {
            "agent_address": self.agent_address,
            "agg_params": self.agg_params,
            "feed_name": self.feed_name,
            "address": self.address,
            "messages": self.messages,
            "record": self.record,
            "agent_session_id": self.agent.agent_session_id
        }

    def flush_buffer(self):
        """Publishes all messages in buffer and empties it."""

        if not in_reactor_context():
            return reactor.callFromThread(self.flush_buffer)
        print(len(self.buffer))
        if self.buffer_start_time is None:
            return

        if self.record:
            self.agent.publish(self.address,(
                                   {k: b.encoded() for k,b in self.blocks.items() if b.timestamps},
                                    self.encoded()
                               ))
            for k,b in self.blocks.items():
                b.clear()

        else:
            self.agent.publish(self.address, (self.buffer, self.encoded()))
            self.buffer = []

    def publish_message(self, message, timestamp=None):
        """
        Publishes message to feed and stores it in ``self.messages``.
        If self.buffered, message is stored in buffer and the feed
        waits until `buffer_time` seconds have elapsed before publishing
        the entire buffer as a list.

        Args:
            message:
                Data to be published

                If the feed is aggregated, the message must have the structure::

                    message = {
                        'block_name': Key given to the block in blocking param
                        'timestamp': timestamp of data
                        'data': {
                                key1: datapoint1
                                key2: datapoint2
                            }
                    }

                Where they keys are exactly those specified in the one of the
                block dicts in the blocking parameter.

            timestamp (float):
                timestamp given to the message. Defaults to time.time()
        """
        current_time = time.time()

        if timestamp is None:
            timestamp = current_time

        if not in_reactor_context():
            return reactor.callFromThread(self.publish_message, message,
                                          timestamp=timestamp)

        if self.record:
            # Data is stored in Block objects
            block_name = message['block_name']
            try:
                b = self.blocks[block_name]
            except KeyError:
                b = Block(block_name, message['data'].keys(), message.get('prefix', ''))
                self.blocks[block_name] = b

            b.add(message)
        else:
            if self.buffer_time == 0:
                # Publish message immediately
                self.agent.publish(self.address, (message, self.encoded()))
            else:
                # Will there be buffered feeds that are not recorded?
                self.buffer.append(message)


        if self.record or self.buffer_time != 0:
            if self.buffer_start_time is None:
                self.buffer_start_time = current_time

            if (current_time - self.buffer_start_time) >= self.buffer_time:

                self.flush_buffer()
                self.buffer_start_time = None

        # Caches message
        if self.max_messages > 0:
            self.messages.append((timestamp, message))
            if len(self.messages) > self.max_messages:
                self.messages.pop(0)
