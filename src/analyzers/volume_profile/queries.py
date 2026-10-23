from decimal import Decimal

from analyzers.volume_profile.model import VolumeProfile
from analyzers.volume_profile.utils import PriceBin, Volume

def get_high_volume_nodes(volume_profile: VolumeProfile, top: int | None = None, threshold_ratio: float | None = None) -> list[PriceBin]:
    """Return high-volume price bins filtered by rank and/or volume threshold."""
    if not volume_profile.content:
        return []

    if top is not None and top <= 0:
        raise ValueError("top must be greater than 0")

    if threshold_ratio is not None and not 0 < threshold_ratio <= 1:
        raise ValueError("threshold_ratio must be between 0 and 1")

    bins = volume_profile.content
    max_volume = max(bin.volume for bin in bins)

    if max_volume == 0:
        return []

    if threshold_ratio is not None:
        threshold = max_volume * Decimal(str(threshold_ratio))
        bins = [
            bin for bin in bins
            if bin.volume >= threshold
        ]

    bins = sorted(
        bins,
        key=lambda bin: bin.volume,
        reverse=True
    )

    if top is not None:
        bins = bins[:top]

    return bins

def get_low_volume_nodes(volume_profile: VolumeProfile, top: int | None = None, threshold_ratio: float | None = 0.5,
) -> list[PriceBin]:
    """Return local low-volume price bins filtered by ratio and/or rank."""
    if len(volume_profile.content) < 3:
        return []

    if top is not None and top <= 0:
        raise ValueError("top must be greater than 0")

    if threshold_ratio is not None and not 0 < threshold_ratio <= 1:
        raise ValueError("threshold_ratio must be between 0 and 1")

    bins = volume_profile.content
    result = []

    for i in range(1, len(bins) - 1):
        previous = bins[i - 1].volume
        current = bins[i].volume
        next_volume = bins[i + 1].volume

        neighbor_average = (previous + next_volume) / 2

        if neighbor_average <= 0:
            continue

        if (
            threshold_ratio is None
            or current <= neighbor_average * Decimal(str(threshold_ratio))
        ):
            result.append(bins[i])

    if top is not None:
        result.sort(key=lambda bin: bin.volume)
        result = result[:top]

    return result