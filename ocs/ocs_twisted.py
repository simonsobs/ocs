import threading

def in_reactor_context():
    """
    Determine whether the current threading context is the twisted
    main (reactor) thread, or a worker pool thread.  Returns True if
    it's the main thread.  Will raise RuntimeError if the thread name
    is confusing.
    """
    t = threading.currentThread()
    if 'PoolThread' in t.name:
        return False
    if 'MainThread' in t.name:
        return True
    raise RuntimeError('Could not determine threading context: '
                       'currentThread.name="%s"' % t.name)

