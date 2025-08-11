from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Union, Dict, Any

EventType = Literal["key", "mouse"]

@dataclass
class BaseEvent:
    type: EventType
    time_delta_ms: int

@dataclass
class KeyEvent(BaseEvent):
    action: Literal["press", "release"]
    key: str

@dataclass
class MouseEvent(BaseEvent):
    action: Literal["move", "click", "press", "release", "scroll"]
    x: int
    y: int
    button: Optional[str] = None
    dx: Optional[int] = None
    dy: Optional[int] = None

Event = Union[KeyEvent, MouseEvent]

@dataclass
class Macro:
    id: str
    title: str
    events: List[Event] = field(default_factory=list)
    with_pauses: bool = True
    repetitions: int = 1
    favorite: bool = False
    preserve_cursor: bool = False

    def to_dict(self) -> Dict[str, Any]:
        def encode_event(e: Event) -> Dict[str, Any]:
            d = e.__dict__.copy()
            d["__class__"] = e.__class__.__name__
            return d

        return {
            "id": self.id,
            "title": self.title,
            "events": [encode_event(e) for e in self.events],
            "with_pauses": self.with_pauses,
            "repetitions": self.repetitions,
            "favorite": self.favorite,
            "preserve_cursor": self.preserve_cursor,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Macro":
        def decode_event(e: Dict[str, Any]) -> Event:
            cls = e.pop("__class__", "")
            if cls == "KeyEvent":
                return KeyEvent(**e)  # type: ignore[arg-type]
            if cls == "MouseEvent":
                return MouseEvent(**e)  # type: ignore[arg-type]
            raise ValueError(f"Unknown event class: {cls}")

        return Macro(
            id=d["id"],
            title=d.get("title", d["id"]),
            events=[decode_event(e) for e in d.get("events", [])],
            with_pauses=d.get("with_pauses", True),
            repetitions=int(d.get("repetitions", 1)),
            favorite=bool(d.get("favorite", False)),
            preserve_cursor=bool(d.get("preserve_cursor", False)),
        )

