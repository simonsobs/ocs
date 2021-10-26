from ocs.ocs_client import OCSClient


class MatchedClient(OCSClient):
    def __init__(self, instance_id, **kwargs):
        super().__init__(instance_id, **kwargs)
