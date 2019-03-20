from ocs import ocs_agent, site_config
from spt3g import core
import numpy as np
import time
import copy

class G3StreamSimulator:
    def __init__(self, agent, port=4536):
        """
        OCS Agent to simulate data streaming without connection to a smurf.
        """
        self.port = port
        self.agent = agent
        self.log = agent.log
        self.is_streaming = False
        self.freq = 100 # [Hz]

        self.writer = core.G3NetworkSender(hostname="*", port=self.port)

        # This does not close the port when streaming stops!
        # Only when the agent is quit!
        self.keys = ["{}".format(i) for i in range(4096)]
        self.channels = {
            k: {
                'type': 'const',
                'val': 0,
                'stdev': 0.05,
            }
            for k in self.keys
        }

    def set_channel(self, session, params=None):
        if params is None:
            params = {}

        cids = params['channels']
        cids = cids if type(cids) == list else [cids]

        fparams = params['func_params']
        fparams = fparams if type(fparams) == list else [fparams]

        for i in range(len(cids)):
            self.channels[cids[i]] = fparams[i]

        return True, "Set Channels {}".format(cids)

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

            t1 = time.time()
            t0 = t1 - delay

            ts = np.arange(t0, t1, 1/self.freq)

            f['session_id'] = 0
            f['frame_num'] = frame_num
            f['data'] = core.G3TimestreamMap()

            for k,c in self.channels.items():

                fparams = copy.copy(c)
                bg = np.random.normal(0, fparams.get('stdev', 0), len(ts))
                if fparams['type'] == 'const':
                    xs = bg + fparams['val']
                elif fparams['type'] in ['lin', 'linear']:
                    xs = bg + ts * fparams['slope'] + fparams.get('offset', 0)
                # Wraps from -pi to pi
                xs = np.mod(xs + np.pi, 2 * np.pi) - np.pi

                f['data'][k] = core.G3Timestream(xs)
                f['data'][k].start = core.G3Time(t0 * core.G3Units.sec)
                f['data'][k].stop = core.G3Time(t1 * core.G3Units.sec)

            self.log.info("Writing G3 Frame")
            self.writer.Process(f)
            frame_num += 1
            time.sleep(delay)
        print("Writing EndProcessingFrame")
        f = core.G3Frame(core.G3FrameType.EndProcessing)
        self.writer.Process(f)
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

    agent.register_task('set', ss.set_channel)
    agent.register_process('stream', ss.start_stream, ss.stop_stream)

    runner.run(agent, auto_reconnect=True)
