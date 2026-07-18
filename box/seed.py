"""Demo seed: a believable shelter mid-operation, so /supplies and
/brief have something true to say. Refuses to run twice (won't touch a
registry that already has real check-ins).

    python3 -m box.seed
"""
from __future__ import annotations

import time

from . import scribe

SUPPLIES = [
    ("water", 1140, "L"), ("blankets", 84, ""), ("MRE meals", 320, ""),
    ("first aid kits", 12, ""), ("flashlights", 25, ""),
    ("AA batteries", 96, ""), ("N95 masks", 150, ""), ("diapers", 40, ""),
]

HOUSEHOLDS = [
    ("Maria Lopez, Diego Lopez", "Diego: insulin, refrigerated",
     "Ana Lopez (daughter, 17)", "801-555-0142"),
    ("Chen family: Wei, Lin, Amy", "", "", ""),
    ("Robert Ferris", "hearing aid, needs batteries", "", ""),
]

LOG = [
    (7.5, "Shelter opened at Lehi Community Center"),
    (6.8, "Water delivery received: 1,200 L from county"),
    (6.1, "Volunteer nurse on site (Sarah K.)"),
    (4.9, "Distributed 60 L water, 22 blankets"),
    (3.6, "Generator refueled — 14 hours runtime remaining"),
    (2.2, "Red Cross ETA tomorrow 09:00 confirmed by radio"),
    (0.9, "Family reunification: 1 match via photo board"),
]


def seed(conn=None, force: bool = False) -> bool:
    conn = conn or scribe.connect()
    if scribe.stock(conn) and not force:
        print("already seeded (supplies present) — nothing done")
        return False
    for item, qty, unit in SUPPLIES:
        scribe.supply(conn, item, qty, unit)
    scribe.supply(conn, "water", -60, "L")
    scribe.supply(conn, "blankets", -22, "")
    for names, med, missing, phone in HOUSEHOLDS:
        scribe.register(conn, names, med, missing, phone)
    now = time.time()
    for hours_ago, entry in LOG:
        conn.execute("INSERT INTO log(ts,entry) VALUES (?,?)",
                     (now - hours_ago * 3600, entry))
    conn.commit()
    print(f"seeded: {len(SUPPLIES)} supply lines, {len(HOUSEHOLDS)} "
          f"households, {len(LOG)} log entries")
    return True


if __name__ == "__main__":
    import sys
    seed(force="--force" in sys.argv)
