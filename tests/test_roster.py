from tipout.roster import load_roster


def test_load_roster_resolves_known_alias(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.resolve("Anthony") == "Anthony Garcia"
    assert roster.resolve("anthony") == "Anthony Garcia"
    assert roster.resolve("Jake") == "Jake Purvis"


def test_unknown_name_returns_none(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.resolve("Maya") is None


def test_resolve_canonical_name_returns_self(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.resolve("Anthony Garcia") == "Anthony Garcia"


def test_resolve_is_case_insensitive(tiny_roster):
    roster = load_roster(tiny_roster)
    # Canonical match, case-insensitive
    assert roster.resolve("anthony garcia") == "Anthony Garcia"
    assert roster.resolve("ANTHONY GARCIA") == "Anthony Garcia"
    # Alias match, case-insensitive even when only one case is in the alias table
    assert roster.resolve("JAKE") == "Jake Purvis"
    assert roster.resolve("jAkE") == "Jake Purvis"
