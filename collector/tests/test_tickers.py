from collector.tickers import TICKERS


def test_ticker_count():
    assert len(TICKERS) == 201


def test_tickers_unique_and_named():
    symbols = [t for t, _, _ in TICKERS]
    assert len(set(symbols)) == 201
    assert all(name for _, name, _ in TICKERS)


def test_sector_count():
    sectors = {s for _, _, s in TICKERS}
    assert len(sectors) == 18
    assert all(s for s in sectors)
