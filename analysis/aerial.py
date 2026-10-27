"""
analysis/aerial.py - shop-wise pit map of every coach physically inside:
holding (received, no desp date, not excluded) + FND (desp date, no actual desp date).
Uses the same holding() / is_fnd() as every other page, so the counts always agree.
No AC locos, no movement history.
"""
from collections import OrderedDict

from core import rules as R
from analysis.position import holding, fnd_now

# shop -> pit lines west->east, (line, label, slots)
SHOPS = OrderedDict([
    ("Paint Shop", [("PS/P2", "P2", 2), ("PS/L2", "L2", 2), ("PS/L1", "L1", 2), ("PS/P1", "P1", 2)]),
    ("LBR Shed", [("LBR/WP", "WP", 2), ("LBR/L4", "L4", 2), ("LBR/L3", "L3", 2), ("LBR/L2", "L2", 2),
                  ("LBR/P1", "P1", 2), ("LBR/L1", "L1", 2)]),
    ("Augmentation Shop", [("AS/L6", "L6", 2), ("AS/L5", "L5", 2), ("AS/P4", "P4", 2), ("AS/P3", "P3", 2),
                           ("AS/P2", "P2", 2), ("AS/L1", "L1", 2)]),
    ("DEMU Shop", [("DM/B", "Wash B", 1), ("DM/L32A", "L32A", 1), ("DM/L32", "L32", 1), ("DM/L31", "L31", 1),
                   ("DM/L30", "L30", 1), ("DM/L29", "L29", 1), ("DM/L28", "L28", 1), ("DM/L27", "L27", 1),
                   ("DM/C", "Central", 1)]),
    ("Light Coach Bay", [("LCB/L16A", "L16A", 1), ("LCB/L16", "L16", 1), ("LCB/L15", "L15", 1),
                         ("LCB/P14", "P14", 1), ("LCB/L13", "L13", 1), ("LCB/L12", "L12", 1),
                         ("LCB/L11", "L11", 1), ("LCB/C", "Central", 1)]),
    ("Heavy Coach Bay", [("HCB/L26", "L26", 1), ("HCB/L25", "L25", 1), ("HCB/L24", "L24", 1),
                         ("HCB/L23", "L23", 1), ("HCB/L22", "L22", 1), ("HCB/L21", "L21", 1),
                         ("HCB/L20", "L20", 1), ("HCB/L19", "L19", 1), ("HCB/L18", "L18", 1),
                         ("HCB/L17", "L17", 1)]),
])
PREFIX_SHOP = {"PS": "Paint Shop", "LBR": "LBR Shed", "AS": "Augmentation Shop", "DM": "DEMU Shop",
               "LCB": "Light Coach Bay", "HCB": "Heavy Coach Bay"}
ALIASES = {"LBR/P2": "LBR/P1", "DM/BL": "DM/B"}


def _split_pit(pit):
    p = (pit or "").strip().upper()
    slot = None
    if "_" in p:
        p, s = p.rsplit("_", 1)
        slot = int(s) if s.isdigit() else None
    return ALIASES.get(p, p), slot


def _chip(d, as_on, fnd=False, km=None):
    rd = R.pdate(d.get("receivedDate"))
    cs, cc = R.pdate(d.get("corrPlace") or d.get("corrPd")), R.pdate(d.get("corrComp"))
    if fnd:
        corr = "done"
    else:
        corr = "done" if cc else ("under" if cs else "")
    days = (as_on - rd).days if rd else None
    band = "" if days is None else ("d30" if days > 30 else ("d20" if days > 20 else "d0"))
    return dict(coach=d.get("coachNo"), group=d["_group"], family=d["_family"], days=days, band=band,
                corr=corr, fnd=fnd, pit=d.get("pitNum") or "", lh=R.light_heavy(d),
                desp=R.pdate(d.get("dispatchDate")), km=(km or {}).get(R.coach_key(d), ""))


def aerial(demands, as_on, km_status=None):
    H = holding(demands, as_on)
    F = fnd_now(demands)
    km = {k: v for k, v in ((km_status or {}).get("coaches") or {}).items() if not v.startswith("OUT")}
    chips = [(h, _chip(h, as_on, km=km)) for h in H] + [(f, _chip(f, as_on, fnd=True, km=km)) for f in F]

    shops = OrderedDict((s, OrderedDict((ln, dict(label=lab, slots=[None] * n, extra=[]))
                                        for ln, lab, n in lines)) for s, lines in SHOPS.items())
    yard, other = [], []
    for d, c in chips:
        if not c["fnd"] and R.location(d) == "Yard":
            yard.append(c)
            continue
        line, slot = _split_pit(d.get("pitNum"))
        shop = PREFIX_SHOP.get(line.split("/")[0])
        if not shop:
            other.append(c)
            continue
        lines = shops[shop]
        if line not in lines:
            lines[line] = dict(label=line.split("/", 1)[-1], slots=[None], extra=[])
        L = lines[line]
        i = (slot - 1) if slot and slot <= len(L["slots"]) else next(
            (k for k, v in enumerate(L["slots"]) if v is None), None)
        if i is not None and L["slots"][i] is None:
            L["slots"][i] = c
        else:
            L["extra"].append(c)          # more coaches on a line than slots - still shown

    key = lambda c: (c["family"] != "ICF", c["group"], -(c["days"] or 0))
    in_shop = sum(1 for d, c in chips if c not in yard and c not in other)
    counts = {s: sum(sum(1 for c in L['slots'] if c) + len(L['extra']) for L in lines.values())
              for s, lines in shops.items()}
    return dict(shops=shops, counts=counts, km_updated=(km_status or {}).get("updated", ""),
                n_km=sum(1 for _, c in chips if c["km"]), yard=sorted(yard, key=key), other=sorted(other, key=key),
                n_hold=len(H), n_fnd=len(F), n_yard=len(yard), n_shop=in_shop, n_other=len(other),
                total=len(chips))
