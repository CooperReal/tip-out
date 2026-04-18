from tipout.roster import load_roster

def test_load_roster_resolves_known_alias(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.resolve("Anthony") == "Anthony Garcia"
    assert roster.resolve("anthony") == "Anthony Garcia"
    assert roster.resolve("Jake") == "Jake Purvis"

def test_unknown_name_returns_none(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.resolve("Maya") is None

def test_fuzzy_candidates_one_match(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.fuzzy_candidates("Anthony") == ["Anthony Garcia"]
    assert roster.fuzzy_candidates("anthony") == ["Anthony Garcia"]

def test_fuzzy_candidates_two_matches(tiny_roster):
    roster = load_roster(tiny_roster)
    assert set(roster.fuzzy_candidates("Andrew")) == {"Andrew Roberts", "Andrew Neita"}

def test_fuzzy_candidates_zero_matches(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.fuzzy_candidates("Maya") == []

def test_resolve_canonical_name_returns_self(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.resolve("Anthony Garcia") == "Anthony Garcia"
