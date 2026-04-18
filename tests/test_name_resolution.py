from tipout.name_resolution import resolve_all


def test_resolve_all_separates_known_and_unknown(tiny_roster):
    from tipout.roster import load_roster
    roster = load_roster(tiny_roster)
    resolved, unknown = resolve_all(["Anthony", "Jake", "Maya", "Unknown"], roster)
    assert resolved == {"Anthony": "Anthony Garcia", "Jake": "Jake Purvis"}
    assert set(unknown) == {"Maya", "Unknown"}
