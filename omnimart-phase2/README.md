# OmniMart Phase 2 tracking prototype

`tracker.py` keeps short-lived digital-twin state keyed by an upstream person tracker ID and returns four explainable review signals: carried item missing from cart near exit, possible concealment, boundary crossing with an item, and repeated shelf interaction without a cart update. It deliberately does not identify people or make a theft determination. Integrate a store-approved person/object tracker and persist tracks/events before using this beyond a demo; the built-in state is in-memory and per process.
