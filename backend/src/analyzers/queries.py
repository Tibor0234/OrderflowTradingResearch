import numpy as np
from analyzers.utils import MonotonicTrend, Outlier

def has_min_length(sequence, length):
    """Return whether the sequence contains at least the specified number of elements."""
    return len(sequence) >= length

def get_max(sequence, source_name, length=None):
    """Return the maximum value from the last `length` elements."""
    if not sequence:
        return None

    if length is None:
        length = len(sequence)

    length = min(length, len(sequence))

    values = [
        getattr(item, source_name)
        for item in sequence[-length:]
    ]

    return max(values)

def get_min(sequence, source_name, length=None):
    """Return the minimum value from the last `length` elements."""
    if not sequence:
        return None

    if length is None:
        length = len(sequence)

    length = min(length, len(sequence))

    values = [
        getattr(item, source_name)
        for item in sequence[-length:]
    ]

    return min(values)

def get_average(sequence, source_name, length=None):
    """Return the average value from the last `length` elements."""
    if not sequence:
        return None

    if length is None:
        length = len(sequence)

    length = min(length, len(sequence))

    values = [
        getattr(item, source_name)
        for item in sequence[-length:]
    ]

    return sum(values) / len(values)

def get_range(sequence, source_name, length=None):
    """Return the range between the maximum and minimum values."""
    if not sequence:
        return None

    if length is None:
        length = len(sequence)

    length = min(length, len(sequence))

    values = [
        getattr(item, source_name)
        for item in sequence[-length:]
    ]

    return max(values) - min(values)

def get_change(sequence, source_name, length=None):
    """Return the change between the first and last values."""
    if not sequence:
        return None

    if length is None:
        length = len(sequence)

    length = min(length, len(sequence))

    if length < 2:
        return None

    first = getattr(sequence[-length], source_name)
    last = getattr(sequence[-1], source_name)

    return last - first

def get_change_percentage(sequence, source_name, length=None):
    """Return the percentage change between the first and last values."""
    if not sequence:
        return None

    if length is None:
        length = len(sequence)

    length = min(length, len(sequence))

    if length < 2:
        return None

    first = float(getattr(sequence[-length], source_name))
    last = float(getattr(sequence[-1], source_name))

    if first == 0:
        return None

    return (last - first) / abs(first)

def get_std(sequence, source_name, length=None):
    """Return the standard deviation of the last `length` values."""
    if not sequence:
        return None

    if length is None:
        length = len(sequence)

    length = min(length, len(sequence))

    if length < 2:
        return 0.0

    values = [
        float(getattr(item, source_name))
        for item in sequence[-length:]
    ]

    return float(np.std(values))

def get_last(sequence, source_name):
    """Return the latest value."""
    if not sequence:
        return None

    return getattr(sequence[-1], source_name)

def get_previous(sequence, source_name):
    """Return the value immediately before the latest value."""
    if len(sequence) < 2:
        return None

    return getattr(sequence[-2], source_name)

def get_position_in_range(sequence, source_name, length=None):
    """Return the latest value's normalized position within the recent range."""
    if not sequence:
        return None

    if length is None:
        length = len(sequence)

    length = min(length, len(sequence))

    values = [
        float(getattr(item, source_name))
        for item in sequence[-length:]
    ]

    minimum = min(values)
    maximum = max(values)

    if maximum == minimum:
        return 0.5

    return (values[-1] - minimum) / (maximum - minimum)

def get_monotonic_trend(sequence, source_name):
    """Determine the direction and length of the latest monotonic trend."""
    if not sequence:
        return MonotonicTrend(False, 0, 0)

    if not hasattr(sequence[-1], source_name):
        raise AttributeError(f"{source_name} not found")

    if len(sequence) < 2:
        return MonotonicTrend(False, 0, 0)

    def v(i):
        return getattr(sequence[i], source_name)

    last, prev = v(-1), v(-2)

    if last == prev:
        return MonotonicTrend(False, 0, 0)

    direction = 1 if last > prev else -1
    length = 2

    for i in range(len(sequence) - 3, -1, -1):
        a, b = v(i), v(i + 1)

        if (direction == 1 and b > a) or (direction == -1 and b < a):
            length += 1
        else:
            break

    return MonotonicTrend(length >= 3, length, direction)

def get_trend_strength(sequence, source_name, recent_bias_pct=0, length=None):
    """Calculate normalized trend strength with optional weighting toward recent values."""
    recent_bias_rate = recent_bias_pct / 100.0

    if length is None:
        length = len(sequence)

    if not sequence:
        return 0.0

    length = min(length, len(sequence))

    if length < 2:
        return 0.0

    seq = sequence[-length:]

    try:
        closes = np.array([float(getattr(c, source_name)) for c in seq])
    except AttributeError:
        raise AttributeError(f"{source_name} not found")

    if closes.size < 2:
        return 0.0

    if hasattr(seq[0], "time"):
        timestamps = np.array([c.time for c in seq])
        x = (timestamps.astype(float) - timestamps[0]) / 60
    else:
        x = np.arange(len(closes))

    n = len(closes)

    decay = (1 - recent_bias_rate)
    weights = decay ** (n - np.arange(n) - 1)

    try:
        slope, intercept = np.polyfit(x, closes, 1, w=weights)
    except Exception:
        return 0.0

    trend_move = slope * (x[-1] - x[0])

    volatility = np.std(np.diff(closes))
    scale_factor = np.log1p(len(closes)) * 2

    if volatility == 0:
        return 0.0

    raw = (trend_move / volatility) / scale_factor

    return float(np.tanh(raw))

def get_outlier(sequence, source_name, length=None):
    """Detect whether the latest movement is an outlier relative to recent movements."""
    if length is None:
        length = len(sequence)

    if not sequence:
        return Outlier(False, 0.0)

    if not hasattr(sequence[-1], source_name):
        raise AttributeError(f"{source_name} not found")

    length = min(length, len(sequence) - 1)

    if length <= 0:
        return Outlier(False, 0.0)

    v = lambda i: getattr(sequence[i], source_name)

    diffs = [
        abs(v(i + 1) - v(i))
        for i in range(-length - 1, -1)
    ]

    avg = sum(diffs) / len(diffs) if diffs else 0
    last_diff = abs(v(-1) - v(-2))

    if avg == 0:
        ratio = 0.0 if last_diff == 0 else float("inf")
    else:
        ratio = last_diff / avg

    return Outlier(
        last_diff > avg,
        ratio if v(-1) >= v(-2) else -ratio
    )