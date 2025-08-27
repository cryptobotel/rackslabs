import yfinance as yf
import requests
import json

# --- Screener Configuration ---
GAP_THRESHOLD = 0.15
MARKET_CAP_LIMIT = 300_000_000

# --- GapScore Configuration ---
POSITIVE_KEYWORDS = ['upgrade', 'buyout', 'acquisition', 'fda approval', 'positive results', 'earnings beat', 'new contract', 'partnership']
NEGATIVE_KEYWORDS = ['downgrade', 'offering', 'investigation', 'lawsuit', 'earnings miss', 'delay', 'halts']

def get_all_tickers():
    """
    Fetches a list of all stock tickers from NASDAQ, NYSE, and AMEX.
    """
    all_tickers = []
    exchanges = ['nasdaq', 'nyse', 'amex']

    for exchange in exchanges:
        print(f"Fetching a list of all tickers from {exchange.upper()}...")
        try:
            url = f"https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=10000&exchange={exchange}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()

            if (
                'data' in data
                and data.get('data')
                and 'table' in data['data']
                and data['data'].get('table')
                and 'rows' in data['data']['table']
                and isinstance(data['data']['table']['rows'], list)
            ):
                tickers_data = data['data']['table']['rows']
                # Filter for small-cap stocks under $300M market cap
                exchange_tickers = [
                    item['symbol']
                    for item in tickers_data
                    if item.get('marketCap') and item['marketCap'].replace(',', '').isdigit() and float(item['marketCap'].replace(',', '')) < MARKET_CAP_LIMIT
                ]
                print(f"Successfully fetched and filtered {len(exchange_tickers)} small-cap tickers from {exchange.upper()}.")
                all_tickers.extend(exchange_tickers)
            else:
                print(f"Could not find 'rows' in the expected location in the API response for {exchange.upper()}.")

        except Exception as e:
            print(f"Could not fetch tickers from {exchange.upper()} API: {e}")
            continue # Continue to the next exchange

    if not all_tickers:
        print("Could not fetch any tickers. Falling back to a default list for demonstration.")
        return ['GME', 'AMC', 'BBBYQ', 'MULN']

    return all_tickers


def calculate_catalyst_score(news):
    score = 0
    if not news: return score
    headline = news[0].get('title', '').lower()
    for keyword in POSITIVE_KEYWORDS:
        if keyword in headline: score += 1
    for keyword in NEGATIVE_KEYWORDS:
        if keyword in headline: score -= 1
    return score

def calculate_squeeze_score(info):
    score = 0
    float_shares = info.get('floatShares')
    if float_shares:
        if float_shares < 10_000_000: score += 2
        elif float_shares < 20_000_000: score += 1
    short_percent_float = info.get('shortPercentOfFloat')
    if short_percent_float:
        score += short_percent_float * 5
    return score

def find_and_score_gappers(tickers):
    if not tickers: return []
    print(f"\nScanning {len(tickers)} tickers for gappers and calculating GapScore...")
    gappers = []

    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            previous_close = info.get('previousClose')
            current_price = info.get('preMarketPrice') or info.get('regularMarketPrice')

            if not previous_close or not current_price or current_price == 0 or previous_close == 0:
                continue

            gap_percent = (current_price - previous_close) / previous_close

            if gap_percent <= GAP_THRESHOLD:
                continue

            news = ticker.news
            gap_score_comp = gap_percent * 10
            catalyst_score_comp = calculate_catalyst_score(news)
            squeeze_score_comp = calculate_squeeze_score(info)
            total_gap_score = gap_score_comp + catalyst_score_comp + squeeze_score_comp

            gappers.append({
                "ticker": ticker_symbol,
                "gap_percentage": gap_percent,
                "current_price": current_price,
                "previous_close": previous_close,
                "catalyst": news[0].get('title', 'N/A') if news else "N/A",
                "gap_score": total_gap_score,
                "score_components": {
                    "gap": f"{gap_score_comp:.2f}",
                    "catalyst": f"{catalyst_score_comp:.2f}",
                    "squeeze": f"{squeeze_score_comp:.2f}",
                }
            })
        except Exception:
            pass

    return gappers

def main():
    print("--- Rackslabs Stock Screener V2.2 (Small-Cap Discovery Edition) ---")

    all_tickers = get_all_tickers()

    if not all_tickers:
        print("Could not find any small-cap stocks to scan. Exiting.")
        return

    gapping_stocks = find_and_score_gappers(all_tickers)

    if not gapping_stocks:
        print("\nNo small-cap gappers found matching the criteria at this time.")
        return

    gapping_stocks.sort(key=lambda x: x['gap_score'], reverse=True)

    print(f"\nFound {len(gapping_stocks)} potential gapper(s), ranked by GapScore:")

    for stock in gapping_stocks:
        print(f"\n--- {stock['ticker']} (GapScore: {stock['gap_score']:.2f}) ---")
        print(f"  Score Breakdown -> Gap: {stock['score_components']['gap']}, Catalyst: {stock['score_components']['catalyst']}, Squeeze: {stock['score_components']['squeeze']}")
        print(f"  Gap: +{stock['gap_percentage']:.2%}")
        print(f"  Price: ${stock['current_price']:.2f} (Prev. Close: ${stock['previous_close']:.2f})")
        print(f"  News: {stock['catalyst']}")

if __name__ == "__main__":
    main()
