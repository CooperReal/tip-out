from tipout.roster import Roster

def resolve_all(raw_names: list[str], roster: Roster) -> tuple[dict[str, str], list[str]]:
    resolved: dict[str, str] = {}
    unknown: list[str] = []
    for raw in set(raw_names):
        canon = roster.resolve(raw)
        if canon:
            resolved[raw] = canon
        else:
            unknown.append(raw)
    return resolved, sorted(unknown)
