import yfinance as yf

# --- Screener Configuration ---
GAP_THRESHOLD = 0.15  # The minimum gap percentage to be considered
TICKERS_TO_SCAN = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'MRNA', 'GME', 'AMC']

# --- GapScore Configuration ---
# Keywords for catalyst scoring
POSITIVE_KEYWORDS = ['upgrade', 'buyout', 'acquisition', 'fda approval', 'positive results', 'earnings beat', 'new contract', 'partnership']
NEGATIVE_KEYWORDS = ['downgrade', 'offering', 'investigation', 'lawsuit', 'earnings miss', 'delay', 'halts']

def calculate_catalyst_score(news):
    """
    Calculates a score based on keywords found in the most recent news headline.
    """
    score = 0
    if not news:
        return score

    # We only check the headline of the most recent news article
    headline = news[0].get('title', '').lower()

    for keyword in POSITIVE_KEYWORDS:
        if keyword in headline:
            score += 1
    for keyword in NEGATIVE_KEYWORDS:
        if keyword in headline:
            score -= 1

    return score

def calculate_squeeze_score(info):
    """
    Calculates a score based on "squeeze" potential (low float, high short interest).
    """
    score = 0

    # 1. Score based on float size (lower float = higher score)
    float_shares = info.get('floatShares')
    if float_shares:
        if float_shares < 10_000_000:  # Under 10M is very low
            score += 2
        elif float_shares < 20_000_000: # Under 20M is low
            score += 1

    # 2. Score based on short interest (higher short % = higher score)
    short_percent_float = info.get('shortPercentOfFloat')
    if short_percent_float:
        # We amplify the score. A 20% short float (0.2) adds 1.0 to the score.
        score += short_percent_float * 5

    return score

def find_and_score_gappers(tickers):
    """
    Finds gapping stocks and calculates a GapScore for each one.
    """
    print(f"Scanning {len(tickers)} tickers and calculating GapScore...")
    gappers = []

    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            # --- Gap Calculation ---
            previous_close = info.get('previousClose')
            current_price = info.get('preMarketPrice') or info.get('regularMarketPrice')

            if not previous_close or not current_price:
                continue

            gap_percent = (current_price - previous_close) / previous_close

            if gap_percent <= GAP_THRESHOLD:
                continue

            # --- Score Calculation ---
            # 1. Gap Score Component (raw gap % scaled by 10)
            gap_score_comp = gap_percent * 10

            # 2. Catalyst Score Component
            news = ticker.news
            catalyst_score_comp = calculate_catalyst_score(news)

            # 3. Squeeze Score Component
            squeeze_score_comp = calculate_squeeze_score(info)

            # NOTE: RVOL component is omitted for now to ensure screener speed.
            # A proper implementation would require heavy historical data calls.
            rvol_score_comp = 0

            total_gap_score = gap_score_comp + catalyst_score_comp + squeeze_score_comp + rvol_score_comp

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
        except Exception as e:
            # Silently continue if a ticker fails, to not interrupt the whole scan
            pass

    return gappers

def main():
    """
    Main function to run the screener and display ranked results.
    """
    print("--- Rackslabs Stock Screener V2 (with GapScore) ---")

    gapping_stocks = find_and_score_gappers(TICKERS_TO_SCAN)

    if not gapping_stocks:
        print("\nNo stocks found matching the criteria at this time.")
        return

    # Sort the found gappers by their GapScore in descending order
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
