import deprecation

from ocs.ocs_client import OCSClient


@deprecation.deprecated(
    deprecated_in='v0.9.0',
    details="Renamed to OCSClient"
)
class MatchedClient(OCSClient):
    pass
