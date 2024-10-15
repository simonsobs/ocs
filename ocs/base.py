from enum import Enum


class ResponseCode(Enum):
    """Enumeration of response codes from the Operation API (start, stop,
    wait, ...).

    These response codes indicate only whether the API call was
    successful, in that the request was propagated all the way to the
    Agent's Operation code.  They are not used to represent success or
    failure of the Operation itself.

    """

    #: OK indicates the request was successful.
    OK = 0

    #: ERROR indicates that the request could not be propagated fully.
    #: This may occur, for example, if an invalid Operation name is
    #: passed, if a request is made that conflicts with an Operation's
    #: current state (e.g. .start() is called on an already-running
    #: Operation), if an API call is made to a Operation of an
    #: incompatible type (e.g. .stop() on a Task), or due to API
    #: syntax error (e.g. misspelled keyword argument to .wait()).
    ERROR = -1

    #: TIMEOUT is returned in the case that a Client issued a blocking
    #: call with timeout (.wait()), and the timeout expired before the
    #: Operation completed.
    TIMEOUT = 1


OK = ResponseCode.OK.value
ERROR = ResponseCode.ERROR.value
TIMEOUT = ResponseCode.TIMEOUT.value


class OpCode(Enum):
    """Enumeration of OpSession "op_code" values.

    The op_code corresponds to the session.status, with the following
    extensions:

    - If the session.status == "done" then the op_code will be
      assigned a value of either SUCCEEDED or FAILED based on
      session.success.
    - If the session.status == "running", and session.degraded is
      True, then the op_code will be DEGRADED rather than RUNNING.

    """

    #: NONE is used to represent an uninitialized OpSession, and does
    #: not correspond to some attempt to run the Operation.
    NONE = 1

    #: STARTING indicates that start() has been successfully called,
    #: but the Operation has not yet marked itself as successfully
    #: launched.  If this state is reached, then at the very least the
    #: start request was not rejected because it was already running.
    STARTING = 2

    #: RUNNING indicates that the Operation has performed its basic
    #: initialization and parameter checking and is performing its
    #: task.  Operation codes need to explicitly mark themselves as
    #: running by calling session.set_state('running').
    RUNNING = 3

    #: STOPPING indicates that the Agent has received a stop or abort
    #: request for this Operation and will try to wrap things up ASAP.
    STOPPING = 4

    #: SUCCEEDED indicates that the Operation has terminated and has
    #: indicated the Operation was successful.  This includes the case
    #: of a Process that was asked to stop and has shut down cleanly.
    SUCCEEDED = 5

    #: FAILED indicates that the Operation has terminated with some
    #: kind of error.
    FAILED = 6

    #: EXPIRED may used to mark session information as invalid in cases
    #: where the state cannot be determined.
    EXPIRED = 7

    #: DEGRADED indicates that an operation meets the requirements for
    #: state RUNNING, but is self-reporting as being in a problematic
    #: state where it is unable to perform its primary functions (for
    #: example, if a Process to operate some hardware is trying to
    #: re-establish connection to that hardware).
    DEGRADED = 8
