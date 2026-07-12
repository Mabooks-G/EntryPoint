"""Shared country-scope rules for the existing text-based requirements schema."""


def _countries(value: object) -> set[str]:
    """Parse values such as '[ALL]' and '[Botswana,United States]'."""
    if not isinstance(value, str):
        return set()
    return {
        item.strip().upper()
        for item in value.strip().strip("[]").split(",")
        if item.strip() and item.strip().upper() not in {"ALL", "ALLEX"}
    }


def requirement_applies(requirement: dict, country_name: str | None) -> bool:
    country = (country_name or "").upper()
    included = _countries(requirement.get("applies_to_countries"))
    excluded = _countries(requirement.get("excluded_countries"))
    return (bool(requirement.get("applies_to_all")) or country in included) and country not in excluded
