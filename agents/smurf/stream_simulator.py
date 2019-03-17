from ocs import ocs_agent, site_config
from spt3g import core
import numpy as np
import time

class G3StreamSimulator:
    def __init__(self, agent, port=4536):
        """
        OCS Agent to simulate data streaming without connection to a smurf.
        """
        self.port = port
        self.agent = agent
        self.log = agent.log
        self.is_streaming = False

        # This does not close the port when streaming stops!
        # Only when the agent is quit!
        self.writer = core.G3NetworkSender(hostname="*", port=self.port)

        self.keys = ["{}".format(i) for i in range(4096)]
        self.channels = {k: (0, .05) for k in self.keys}

    def set_channel_val(self, session, params=None):
        if params is None:
            params = {}

        chan_num = params['chan_num']
        mean = params['mean']
        stdev = params.get('stdev', 0.5)

        self.channels[self.keys[chan_num]] = (mean, stdev)

    def start_stream(self, session, params=None):

        if params is None:
            params = {}

        delay = params.get('delay', 1)
        ts_len = params.get('ts_len', 100)

        # Writes status frame
        f = core.G3Frame(core.G3FrameType.Housekeeping)
        f['session_id'] = 0
        f['start_time'] = time.time()
        self.writer.Process(f)

        self.is_streaming = True
        frame_num = 0
        while self.is_streaming:

            f = core.G3Frame(core.G3FrameType.Scan)
            f['session_id'] = 0
            f['frame_num'] = frame_num
            f['data'] = core.G3TimestreamMap()
            for k,v in self.channels.items():
                f['data'][k] = core.G3Timestream(np.random.normal(v[0], v[1], ts_len))

            self.log.info("Writing G3 Frame")
            self.writer.Process(f)
            frame_num += 1
            time.sleep(delay)

        return True, "Finished streaming"

    def stop_stream(self, session, params=None):
        self.is_streaming = False
        return True, "Stopping stream"


if __name__ == '__main__':
    parser = site_config.add_arguments()
    args = parser.parse_args()
    site_config.reparse_args(args, 'G3StreamSimulator')

    agent, runner = ocs_agent.init_site_agent(args)
    ss = G3StreamSimulator(agent, port=int(args.port))

    agent.register_task('set', ss.set_channel_val)
    agent.register_process('stream', ss.start_stream, ss.stop_stream)

    runner.run(agent, auto_reconnect=True)
