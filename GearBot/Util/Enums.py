from enum import Enum, IntEnum


class ReminderStatus(IntEnum):
    Pending = 1
    Delivered = 2
    Failed = 3