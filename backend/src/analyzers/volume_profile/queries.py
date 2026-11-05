from decimal import Decimal

from analyzers.volume_profile.model import VolumeProfile
from analyzers.volume_profile.utils import PriceBin, Volume

def get_high_volume_nodes(
    volume_profile: VolumeProfile,
    top: int | None = None,
    threshold_ratio: float | None = None
    ) -> list[PriceBin]:
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

def get_low_volume_nodes(
    volume_profile: VolumeProfile,
    top: int | None = None,
    threshold_ratio: float | None = None,
    ) -> list[PriceBin]:
    """Return low-volume price bins filtered by ratio and/or rank."""
    if not volume_profile.content:
        return []

    if top is not None and top <= 0:
        raise ValueError("top must be greater than 0")

    if threshold_ratio is not None and not 0 < threshold_ratio <= 1:
        raise ValueError("threshold_ratio must be between 0 and 1")

    bins = volume_profile.content
    if threshold_ratio is not None:
        threshold = max(bin.volume for bin in bins) * Decimal(str(threshold_ratio))
        is_lvn = [bin.volume <= threshold for bin in bins]
        non_lvn_indices = [
            index for index, is_low_volume in enumerate(is_lvn) if not is_low_volume
        ]
        if not non_lvn_indices:
            return []

        first_non_lvn = non_lvn_indices[0]
        last_non_lvn = non_lvn_indices[-1]
        bins = [
            bin
            for index, bin in enumerate(bins)
            if is_lvn[index] and first_non_lvn < index < last_non_lvn
        ]

    bins = sorted(bins, key=lambda bin: bin.volume)
    if top is not None:
        bins = bins[:top]

    return bins


def get_bracketed_low_volume_nodes(
    high_volume_nodes: list[PriceBin],
    low_volume_nodes: list[PriceBin],
    ) -> list[PriceBin]:
    """Return LVNs with at least one HVN below and above each price bin."""
    return [
        low_volume_node
        for low_volume_node in low_volume_nodes
        if any(
            high_volume_node.low + high_volume_node.size <= low_volume_node.low
            for high_volume_node in high_volume_nodes
        )
        and any(
            high_volume_node.low
            >= low_volume_node.low + low_volume_node.size
            for high_volume_node in high_volume_nodes
        )
    ]