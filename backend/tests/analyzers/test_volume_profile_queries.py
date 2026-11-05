from decimal import Decimal

from analyzers.volume_profile.model import VolumeProfile
from analyzers.volume_profile.queries import (
    get_bracketed_low_volume_nodes,
    get_low_volume_nodes,
)
from analyzers.volume_profile.utils import PriceBin


def create_volume_profile(volumes: list[int]) -> VolumeProfile:
    profile = VolumeProfile(price_bin_count=len(volumes), value_area_pct=70)
    profile.content = [
        PriceBin(
            low=Decimal(index),
            size=Decimal(1),
            buy_volume=Decimal(volume),
            sell_volume=Decimal(0),
        )
        for index, volume in enumerate(volumes)
    ]
    return profile


def test_low_volume_nodes_without_threshold_are_sorted_by_volume():
    profile = create_volume_profile([5, 1, 4, 2, 3])

    nodes = get_low_volume_nodes(profile, top=2)

    assert [node.volume for node in nodes] == [Decimal(1), Decimal(2)]


def test_threshold_keeps_lvn_bins_bracketed_by_non_lvn_bins():
    profile = create_volume_profile([1, 9, 1, 2, 10, 1])

    nodes = get_low_volume_nodes(profile, threshold_ratio=0.5)

    assert [node.low for node in nodes] == [Decimal(2), Decimal(3)]


def test_threshold_returns_no_lvns_when_none_have_non_lvn_on_both_sides():
    profile = create_volume_profile([1, 1, 2, 1])

    assert get_low_volume_nodes(profile, threshold_ratio=0.5) == []


def test_returns_only_lvns_between_high_volume_nodes():
    profile = create_volume_profile([1, 10, 2, 3, 10, 1])
    high_volume_nodes = [profile.content[1], profile.content[4]]
    low_volume_nodes = [
        profile.content[0],
        profile.content[2],
        profile.content[3],
        profile.content[5],
    ]

    nodes = get_bracketed_low_volume_nodes(
        high_volume_nodes,
        low_volume_nodes,
    )

    assert [node.low for node in nodes] == [Decimal(2), Decimal(3)]


def test_returns_no_lvns_without_high_volume_nodes_on_both_sides():
    profile = create_volume_profile([1, 10, 2, 3])
    high_volume_nodes = [profile.content[1]]
    low_volume_nodes = [profile.content[0], profile.content[2], profile.content[3]]

    assert (
        get_bracketed_low_volume_nodes(
            high_volume_nodes,
            low_volume_nodes,
        )
        == []
    )
