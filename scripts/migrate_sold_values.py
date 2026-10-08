import sys

from ebay_research_agent.config import get_settings
from ebay_research_agent.sold_values import _resolve_path, migrate_sold_values


def main() -> None:
    path = _resolve_path(get_settings().sold_values_path)
    migrated = migrate_sold_values(path)
    if migrated:
        print(f"Migrated {path}")
    else:
        print(f"Already migrated (or no change): {path}")


if __name__ == "__main__":
    sys.exit(main())
