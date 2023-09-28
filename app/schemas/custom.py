from enum import Enum


class PerplexityStatus(str, Enum):
    INIT = "Perplexity is initializing"
    READY = "Perplexity is ready to accept requests"
    UPDATING = "Perplexity is updating auth credentials"
    BUSY = "Perplexity is busy processing a request"


class PerplexityMode(str, Enum):
    COPILOT = "copilot"
    CONCISE = "concise"
