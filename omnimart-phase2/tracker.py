"""Phase two: lightweight customer digital-twin state and theft signal scoring."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class Track:
    track_id: str
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    zone: str = "entrance"
    path: list[dict[str, Any]] = field(default_factory=list)
    held_objects: dict[str, float] = field(default_factory=dict)
    cart_products: set[str] = field(default_factory=set)
    events: list[dict[str, Any]] = field(default_factory=list)

class DigitalTwinTracker:
    """In-memory prototype; production multi-camera re-identification needs a vision tracker."""
    def __init__(self, expiry_seconds: int = 300):
        self.tracks: dict[str, Track] = {}
        self.expiry_seconds = expiry_seconds

    def update(self, track_id: str, *, zone: str, objects: list[dict] | None = None,
               cart_products: list[str] | None = None, timestamp: datetime | None = None) -> Track:
        now = timestamp or datetime.now(timezone.utc)
        t = self.tracks.setdefault(track_id, Track(track_id))
        t.last_seen, t.zone = now, zone
        t.path.append({"at": now.isoformat(), "zone": zone})
        for obj in objects or []:
            label = str(obj.get("label", "unknown")); t.held_objects[label] = float(obj.get("confidence", 0))
        if cart_products is not None: t.cart_products = set(cart_products)
        t.events.extend(score_theft_signals(t, objects or [], now))
        self.expire(now)
        return t

    def expire(self, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        self.tracks = {k:v for k,v in self.tracks.items() if (now-v.last_seen).total_seconds() <= self.expiry_seconds}

def score_theft_signals(track: Track, objects: list[dict], now: datetime | None = None) -> list[dict]:
    """Four explainable signals. Output is an alert score, never a claim of theft."""
    now = now or datetime.now(timezone.utc)
    signals=[]
    # 1. Item carried beyond shelf zone but absent from the digital cart.
    for obj in objects:
        label=str(obj.get("label","")); product_id=obj.get("product_id")
        if obj.get("action")=="carry" and track.zone in {"exit","checkout","front"} and product_id and product_id not in track.cart_products:
            signals.append(("unscanned_item_at_exit",0.55,{"product_id":product_id,"label":label}))
    # 2. Object disappears into a bag/occluded zone after a pickup.
    if any(e.get("type")=="pickup" for e in track.events) and any(o.get("action")=="conceal" for o in objects):
        signals.append(("possible_concealment",0.65,{}))
    # 3. Restricted/exit boundary crossed with an unresolved item.
    if track.zone in {"exit","restricted"} and track.held_objects and not track.cart_products:
        signals.append(("boundary_crossing_with_item",0.45,{"zone":track.zone}))
    # 4. Repeated shelf interaction without a corresponding cart update.
    recent=[p for p in track.path if (now-datetime.fromisoformat(p["at"])).total_seconds()<120]
    shelf_visits=sum(1 for p in recent if p["zone"]=="shelf")
    if shelf_visits>=4 and track.held_objects and not track.cart_products:
        signals.append(("repeated_pickup_without_cart_update",0.35,{"shelf_visits":shelf_visits}))
    return [{"signal":name,"score":score,"detail":detail,"track_id":track.track_id,"at":now.isoformat(),"review_required":True} for name,score,detail in signals]
