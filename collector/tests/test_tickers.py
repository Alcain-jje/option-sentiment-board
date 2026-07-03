from collector.tickers import TICKERS


def test_ticker_count():
    assert len(TICKERS) == 52


def test_tickers_unique_and_named():
    symbols = [t for t, _ in TICKERS]
    assert len(set(symbols)) == 52
    assert all(name for _, name in TICKERS)
