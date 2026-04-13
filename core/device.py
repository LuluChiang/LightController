from enum import Enum, auto
from dataclasses import dataclass


class DeviceState(Enum):
    DISCONNECTED = auto()
    CONNECTING   = auto()
    CONNECTED    = auto()
    ERROR        = auto()


@dataclass
class Device:
    name: str
    address: str
    state: DeviceState = DeviceState.DISCONNECTED
    is_on: bool = False
    red: int = 255
    green: int = 255
    blue: int = 255
    brightness: int = 255
