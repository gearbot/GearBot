from enum import Enum


class ReminderStatus(Enum):
    Pending = 1
    Delivered = 2
    Failed = 3