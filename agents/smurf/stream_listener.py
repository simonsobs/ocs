from ocs import ocs_agent, site_config
from spt3g import core
from datetime import datetime
import os


class G3StreamListener:
    def __init__(self, agent, port=4536):
        self.agent = agent
        self.log = self.agent.log
        self.port = port
        self.is_streaming = False

    def start_stream(self, session, params=None):
        if params is None:
            params = {}

        time_per_file = params.get("time_per_file", 60*60) # [sec]
        data_dir = params.get("data_dir", "data/")

        self.log.info("Writing data to {}".format(data_dir))
        self.log.info("New file every {} seconds".format(time_per_file))

        reader = core.G3Reader("tcp://localhost:{}".format(self.port))
        writer = None

        last_meta = None
        self.is_streaming = True

        while self.is_streaming:
            if writer is None:
                start_time = datetime.utcnow()
                ts = start_time.timestamp()
                subdir = os.path.join(data_dir, "{:.5}".format(str(ts)))

                if not os.path.exists(subdir):
                    os.makedirs(subdir)

                filename = start_time.strftime("%Y-%m-%d-%H-%M-%S.g3")
                filepath = os.path.join(subdir, filename)
                writer = core.G3Writer(filename=filepath)
                if last_meta is not None:
                    writer(last_meta)

            frames = reader.Process(None)
            for f in frames:
                if f.type == core.G3FrameType.Housekeeping:
                    last_meta = f
                writer(f)

            if (datetime.utcnow().timestamp() - ts) > time_per_file:
                writer(core.G3Frame(core.G3FrameType.EndProcessing))
                writer = None

        if writer is not None:
            writer(core.G3Frame(core.G3FrameType.EndProcessing))

        return True, "Finished Streaming"

    def stop_stream(self, session, params=None):
        self.is_streaming = False
        return True, "Stopping Streaming"


if __name__ == '__main__':
    parser = site_config.add_arguments()
    args = parser.parse_args()
    site_config.reparse_args(args, 'G3StreamListener')

    agent, runner = ocs_agent.init_site_agent(args)
    listener = G3StreamListener(agent, port=int(args.port))

    agent.register_process('stream', listener.start_stream, listener.stop_stream)

    runner.run(agent, auto_reconnect=True)

