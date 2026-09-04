"""Manual price ingestion entry point reserved for Phase 2+ operations."""


def main() -> None:
    raise SystemExit("Use GET /api/v1/stocks/{ticker}/prices for Phase 2 price ingestion.")


if __name__ == "__main__":
    main()
