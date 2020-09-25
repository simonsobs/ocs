from ocs import ocs_agent, site_config, client_t, ocs_feed
import time
import threading
import os
from autobahn.wamp.exception import ApplicationError
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep as dsleep
import numpy as np

class NotesAgent:
    def __init__(self, agent):
        self.agent = agent
        self.log = agent.log
        self.lock = threading.Semaphore()

        # Register feed
        agg_params = {
            'frame_length': 60
        }
        self.agent.register_feed('notes',
                                 record=True,
                                 agg_params=agg_params,
                                 buffer_time=0.)

    @inlineCallbacks
    def note_task(self, session, params={}):
        """Task to record a note.

        The session data includes the last note recorded, with
        timestamp and tag.  For example::

            {'last_note': [1800000000.0, 'general', 'Starting scan test.']}

        Args:
            note (str): String note to record.
            tag (str): Short tag for grouping.  Defaults to 'general'.

        """
        tag = str(params.get('tag', 'general'))
        note = str(params.get('note', ''))
        if note == '':
            return False, 'A non-empty "note" (str) argument is required.'
        if tag == '':
            tag = 'general'
        timestamp = time.time()

        block = ocs_feed.Block('default', ['note', 'tag'])

        block.timestamps = [timestamp]
        block.data['note'] = [note]
        block.data['tag'] = [tag]
        yield session.app.publish_to_feed('notes', block.encoded())

        session.data={'last_note': {'timestamp': timestamp,
                                    'note': note,
                                    'tag': tag}}

        return True, 'Recorded note under tag "%s"' % tag


if __name__ == '__main__':
    args = site_config.parse_args(agent_class='NotesAgent')
    agent, runner = ocs_agent.init_site_agent(args)
    noter = NotesAgent(agent)
    agent.register_task('note', noter.note_task, blocking=False)
    runner.run(agent, auto_reconnect=True)
