from tipout.regression import list_fixtures, run_fixture


def test_synthetic_fixture_passes():
    fixtures = [f for f in list_fixtures() if f.name == "_synthetic"]
    assert fixtures, "Synthetic fixture missing - rebuild it"
    diffs = run_fixture(fixtures[0])
    if diffs:
        preview = "\n".join(
            f"  {d.sheet}!{d.cell}: expected={d.expected!r} actual={d.actual!r}"
            for d in diffs[:10]
        )
        raise AssertionError(f"{len(diffs)} diff(s):\n{preview}")
