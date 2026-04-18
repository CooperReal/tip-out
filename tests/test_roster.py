from tipout.roster import load_roster

def test_load_roster_resolves_known_alias(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.resolve("Anthony") == "Anthony Garcia"
    assert roster.resolve("anthony") == "Anthony Garcia"
    assert roster.resolve("Jake") == "Jake Purvis"

def test_unknown_name_returns_none(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.resolve("Maya") is None
