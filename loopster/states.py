import enum


class State(enum.Enum):

    INITIAL = 'initial'
    RUNNING = 'running'
    STOPPED = 'stopped'
    FAILED = 'failed'
    NUMB = 'numb'
