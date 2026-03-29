from dataclasses import dataclass, field

ARRIVAL   = 0
DEPARTURE = 1

@dataclass(order=True)
class Event:
    time: float
    kind: int
    server: int = field(default=0, compare=False)
