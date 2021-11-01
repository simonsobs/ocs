import deprecation

from ocs.ocs_client import OCSClient


@deprecation.deprecated(
    deprecated_in='v0.9.0',
    details="Renamed to OCSClient"
)
class MatchedClient(OCSClient):
    def __init__(self, instance_id, **kwargs):
        super().__init__(instance_id, **kwargs)
