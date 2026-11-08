"""Domain failures shared by durable services and HTTP routes."""
from api.contracts import Problem


class BackendError(Exception):
    def __init__(self, http, status, code, reason, revision=None, choices=None):
        super().__init__(reason)
        self.http = http
        self.problem = Problem(status=status, code=code, reason=reason,
            choices=choices or [], current_revision=revision, retryable=http == 503)
