"""World-time sampling shared by the renderer and the physics check (10/19).

Positions and angles pass through every key at its time (timing is unchanged), but between keys they follow a monotone
cubic (PCHIP / Fritsch–Carlson) instead of straight lines:
  - speed is continuous through a key, so nothing jerks at a key;
  - a key next to a hold (same value) gets zero slope → the object eases out of a stop and eases into one;
  - no overshoot (a car never drives past where a key puts it, never dips under the road).
SMOOTH=False gives the old linear sampling (what the editor still uses).
"""
SMOOTH = True
FIELDS = ("p", "r", "s", "a", "lens")


def _slopes(ts, vs):
    n = len(ts)
    if n < 2: return [0.0] * n
    d = [(vs[i + 1] - vs[i]) / max(1e-9, ts[i + 1] - ts[i]) for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0: m[i] = 0.0
        else:
            h0, h1 = ts[i] - ts[i - 1], ts[i + 1] - ts[i]
            w1, w2 = 2 * h1 + h0, h1 + 2 * h0
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    # ends: a key that starts or ends the track holds (zero slope) only if its neighbour segment is flat
    return m


_cache = {}


def _track(keys, field, comp):
    """(times, values, slopes) for one component, using only keys that have the field."""
    ck = (id(keys), field, comp)
    if ck in _cache: return _cache[ck]
    ks = [k for k in keys if field in k]
    ts = [k["t"] for k in ks]
    vs = [(k[field][comp] if isinstance(k[field], list) else k[field]) for k in ks]
    out = (ts, vs, _slopes(ts, vs))
    _cache[ck] = out
    return out


def _eval(ts, vs, ms, t):
    if t <= ts[0]: return vs[0]
    if t >= ts[-1]: return vs[-1]
    lo, hi = 0, len(ts) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ts[mid] <= t: lo = mid
        else: hi = mid
    h = ts[hi] - ts[lo]
    if h <= 1e-9: return vs[hi]
    u = (t - ts[lo]) / h
    if not SMOOTH: return vs[lo] + (vs[hi] - vs[lo]) * u
    h00, h10, h01, h11 = 2*u**3 - 3*u**2 + 1, u**3 - 2*u**2 + u, -2*u**3 + 3*u**2, u**3 - u**2
    return h00 * vs[lo] + h10 * h * ms[lo] + h01 * vs[hi] + h11 * h * ms[hi]


def sample(keys, t):
    """Same contract as the old render_blocking.sample: dict with p/r/s/a/lens, pose (key before), pose2 (key after), u."""
    if t <= keys[0]["t"]: a = b = keys[0]; u = 0.0
    elif t >= keys[-1]["t"]: a = b = keys[-1]; u = 0.0
    else:
        i = 0
        while keys[i + 1]["t"] <= t: i += 1
        a, b = keys[i], keys[i + 1]; u = (t - a["t"]) / max(1e-6, b["t"] - a["t"])
    out = {}
    for f in FIELDS:
        if not any(f in k for k in keys): continue
        first = next(k for k in keys if f in k)
        if isinstance(first[f], list):
            out[f] = [_eval(*_track(keys, f, c), t) for c in range(len(first[f]))]
        else:
            out[f] = _eval(*_track(keys, f, 0), t)
    # 姿勢の切り替えはなめらかに（smoothstep）：キーの間でじわっと移る
    us = u * u * (3 - 2 * u) if SMOOTH else u
    out["pose"] = a.get("pose"); out["pose2"] = b.get("pose"); out["u"] = us
    return out
