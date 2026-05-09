from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    GENERIC_FAILURE = 1
    BAD_USAGE = 2
    PREFLIGHT_FAILED = 3
    SOURCE_UNUSABLE = 4
    STAGE_FAILED = 5
    SIGINT = 130
