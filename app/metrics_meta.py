METRICS_META = {
    'mvrv': {
        'page_title':  'Bitcoin MVRV Ratio — Market Cycle Indicator',
        'description': 'Live Bitcoin MVRV Ratio (Market Value / Realized Value). Below 1 = accumulation zone; above 3.5 = historic cycle tops. Updated daily.',
        'h1':          'Bitcoin MVRV Ratio',
        'subtitle':    'Market Value to Realized Value',
        'body':        'The MVRV Ratio compares Bitcoin\'s current market capitalization to the Realized Cap — the aggregate value of all UTXOs priced at the moment they last moved. When MVRV falls below 1, the market is trading below the collective cost basis of all holders, a zone that has historically preceded major bull runs. Values above 3.5 have consistently marked cycle tops across every Bitcoin market cycle since 2011.',
        'hint':        '<1 undervalued · 1–2 fair value · 2–3.5 caution · >3.5 top zone',
        'api':         'mvrv',
        'value_field': 'mvrv',
        'value_fmt':   '.2f',
        'series':      'values',
        'related':     ['nupl', 'mvrv_zscore', 'sopr'],
    },
    'sopr': {
        'page_title':  'Bitcoin SOPR — Spent Output Profit Ratio',
        'description': 'Live Bitcoin SOPR indicator. Above 1 = coins moved at profit; below 1 = selling at a loss (capitulation signal). Updated daily.',
        'h1':          'Bitcoin SOPR',
        'subtitle':    'Spent Output Profit Ratio',
        'body':        'SOPR measures whether Bitcoin moved on a given day was sold at a profit or a loss relative to its acquisition price. A value above 1 means on average coins were moved at a gain. Values below 1 signal capitulation — holders are selling at a loss. A sustained recovery of SOPR back above 1 after a period below is considered a classic bullish confirmation signal.',
        'hint':        '<1 selling at loss (capitulation) · ≈1 breakeven · >1 selling at profit',
        'api':         'sopr',
        'value_field': 'current',
        'value_fmt':   '.4f',
        'series':      'values',
        'related':     ['mvrv', 'nupl', 'cdd'],
    },
    'nvt': {
        'page_title':  'Bitcoin NVT Ratio — Network Value to Transactions',
        'description': 'Live Bitcoin NVT Ratio. Works like a P/E ratio for Bitcoin — high NVT signals overvaluation relative to on-chain usage. Updated daily.',
        'h1':          'Bitcoin NVT Ratio',
        'subtitle':    'Network Value to Transactions (28-day MA)',
        'body':        'The NVT Ratio divides Bitcoin\'s market cap by its 28-day moving average of on-chain transaction volume. It works like a P/E ratio: a high NVT means the network is valued far above its actual usage, historically a sign of overvaluation. A low NVT signals strong utility relative to price — a potential accumulation zone.',
        'hint':        '<50 undervalued · 50–100 fair · 100–150 caution · >150 overvalued',
        'api':         'nvt',
        'value_field': 'nvt',
        'value_fmt':   '.1f',
        'series':      'values',
        'related':     ['mvrv', 'active_addresses', 'tx_count'],
    },
    'nupl': {
        'page_title':  'Bitcoin NUPL — Net Unrealized Profit / Loss',
        'description': 'Live Bitcoin NUPL indicator. Below 0 = capitulation; above 0.75 = euphoria. Measures aggregate unrealized gain of all holders.',
        'h1':          'Bitcoin NUPL',
        'subtitle':    'Net Unrealized Profit / Loss',
        'body':        'NUPL measures the aggregate unrealized profit or loss of all Bitcoin holders. Derived from MVRV as NUPL = 1 − 1/MVRV. Values below 0 indicate the market is in capitulation — holders are collectively at a loss, historically a strong buy zone. Values above 0.75 signal euphoria, where most supply is in heavy profit and a reversal is likely.',
        'hint':        '<0 capitulation · 0–0.25 hope · 0.25–0.5 optimism · 0.5–0.75 belief · >0.75 euphoria',
        'api':         'nupl',
        'value_field': 'nupl',
        'value_fmt':   '.3f',
        'series':      'values',
        'related':     ['mvrv', 'sopr', 'supply_profit'],
    },
    'puell': {
        'page_title':  'Bitcoin Puell Multiple — Miner Revenue Cycle Indicator',
        'description': 'Live Bitcoin Puell Multiple. Divides daily miner revenue by its 365-day average. Below 0.5 = market bottom; above 4 = cycle top.',
        'h1':          'Bitcoin Puell Multiple',
        'subtitle':    'Daily miner revenue vs 365-day average',
        'body':        'The Puell Multiple divides the current daily miner revenue (block rewards + fees) by its 365-day moving average. Miners are systematic sellers — when revenue is unusually high relative to the historical average, they tend to sell more, creating downward price pressure. Values below 0.5 historically coincide with market bottoms; values above 4 with cycle tops.',
        'hint':        '<0.5 bottom zone · 0.5–2 fair · 2–4 caution · >4 top zone',
        'api':         'puell',
        'value_field': 'puell',
        'value_fmt':   '.2f',
        'series':      'values',
        'related':     ['hashrate', 'mvrv', 'stf'],
    },
    'rhodl': {
        'page_title':  'Bitcoin RHODL Ratio — Long-Term vs Short-Term Holder Supply',
        'description': 'Live Bitcoin RHODL Ratio. Compares BTC held 1–2 years vs 1d–1w. High ratio = LTH conviction; low = STH dominant.',
        'h1':          'Bitcoin RHODL Ratio',
        'subtitle':    'Ratio of HODLed 1–2y vs 1d–1w supply',
        'body':        'The RHODL Ratio compares Bitcoin held for 1–2 years to Bitcoin held for just 1 day to 1 week. A high ratio means long-term holders dominate supply — bullish conviction and supply contraction. A low ratio means recent buyers dominate, typical of early bear markets when experienced holders have already distributed.',
        'hint':        'High ratio: LTH conviction · Low ratio: STH dominant — early bear or opportunity',
        'api':         'rhodl',
        'value_field': 'rhodl',
        'value_fmt':   ',.0f',
        'series':      None,
        'related':     ['hodl', 'lth', 'sth'],
    },
    'supply_profit': {
        'page_title':  'Bitcoin Supply in Profit — % of BTC at Unrealized Gain',
        'description': 'Live % of Bitcoin supply in unrealized profit. >90% = top zone; <50% = capitulation and accumulation opportunity.',
        'h1':          'Bitcoin Supply in Profit',
        'subtitle':    '% of circulating supply at unrealized gain',
        'body':        'Supply in Profit measures what percentage of the circulating Bitcoin supply has an acquisition price below the current market price. When nearly all supply is in profit (>90%) the market is historically near cycle tops. When supply in profit falls below 50%, it signals widespread capitulation and historically strong accumulation zones.',
        'hint':        '>90% top zone · 50–75% fair · <50% capitulation / buy zone',
        'api':         'rhodl',
        'value_field': 'supply_in_profit_pct',
        'value_fmt':   '.1f',
        'value_suffix': '%',
        'series':      None,
        'related':     ['nupl', 'hodl', 'lth'],
    },
    'cdd': {
        'page_title':  'Bitcoin CDD — Coin Days Destroyed',
        'description': 'Live Bitcoin Coin Days Destroyed (CDD). Spikes signal old coins moving — potential distribution near tops. Updated daily.',
        'h1':          'Bitcoin Coin Days Destroyed',
        'subtitle':    'CDD — weighted measure of dormant supply movement',
        'body':        'Coin Days Destroyed weights each Bitcoin transaction by how long the coins sat idle before moving. One BTC held for 100 days and then spent destroys 100 coin-days. A spike in CDD means old, long-dormant coins are being moved — often a sign of large holders distributing near market tops. It is one of the oldest and most respected on-chain signals.',
        'hint':        'Spike above 2× 90d avg = old coins moving — potential distribution',
        'api':         'cdd',
        'value_field': 'current',
        'value_fmt':   ',.0f',
        'series':      'values',
        'related':     ['sopr', 'whale_tx', 'exchange_flow'],
    },
    'exchange_flow': {
        'page_title':  'Bitcoin Exchange Flow — Inflows & Outflows',
        'description': 'Live Bitcoin exchange inflows and outflows. Net inflow = bearish (sell pressure); net outflow = accumulation signal.',
        'h1':          'Bitcoin Exchange Flow',
        'subtitle':    'BTC inflows & outflows across 50+ exchanges',
        'body':        'Exchange Flow tracks Bitcoin moving into and out of known exchange wallets (761 labeled addresses across 50+ exchanges). Net inflow — more BTC entering exchanges — is historically bearish, as coins are often deposited to be sold. Net outflow — BTC leaving exchanges — suggests accumulation and reduced sell pressure. Data sourced from the Dune Analytics Spellbook.',
        'hint':        'Net >0 (inflow) = bearish · Net <0 (outflow) = accumulation',
        'api':         'exchange_flow',
        'value_field': 'current_net',
        'value_fmt':   ',.0f',
        'value_suffix': ' BTC',
        'series':      'net',
        'related':     ['whale_tx', 'cdd', 'sopr'],
    },
    'active_addresses': {
        'page_title':  'Bitcoin Active Addresses — Daily On-Chain Activity',
        'description': 'Live count of unique Bitcoin addresses transacting daily. Rising active addresses signal growing network adoption and on-chain demand.',
        'h1':          'Bitcoin Active Addresses',
        'subtitle':    'Unique addresses transacting per day',
        'body':        'Active Addresses counts the number of unique Bitcoin addresses that participated in a transaction on a given day. Rising active addresses signal growing network adoption and user activity. A divergence between rising price and falling active addresses can be a warning sign — price moves not supported by underlying on-chain activity often reverse.',
        'hint':        'Rising = growing adoption · Divergence from price = warning signal',
        'api':         'active_addresses',
        'value_field': 'current',
        'value_fmt':   ',.0f',
        'series':      'values',
        'related':     ['tx_count', 'nvt', 'whale_tx'],
    },
    'whale_tx': {
        'page_title':  'Bitcoin Whale Transactions — Large On-Chain Moves',
        'description': 'Daily count of Bitcoin transactions >100 BTC. Whale activity spikes often precede significant price moves.',
        'h1':          'Bitcoin Whale Transactions',
        'subtitle':    'Transactions > 100 BTC per day',
        'body':        'Whale Transactions counts the number of on-chain Bitcoin transactions moving more than 100 BTC (~$10M+) per day. A spike in whale activity often precedes significant price moves — large holders repositioning, OTC settlements, or exchange deposits ahead of selling. Sustained high whale volume alongside rising exchange inflows is a classic distribution signal.',
        'hint':        'Spike + rising exchange inflow = distribution risk · Spike + outflow = accumulation',
        'api':         'whale_tx',
        'value_field': 'current',
        'value_fmt':   ',.0f',
        'series':      'values',
        'related':     ['exchange_flow', 'cdd', 'active_addresses'],
    },
    'mvrv_zscore': {
        'page_title':  'Bitcoin MVRV Z-Score — Normalized Cycle Indicator',
        'description': 'Live Bitcoin MVRV Z-Score. Normalizes market cap vs realized cap by historical std dev. Above 7 = top; below 0 = buy zone.',
        'h1':          'Bitcoin MVRV Z-Score',
        'subtitle':    'Market cap distance from realized cap in standard deviations',
        'body':        'The MVRV Z-Score normalizes the gap between market cap and realized cap by the historical standard deviation of all market caps since 2013. Unlike plain MVRV, it accounts for variance across different market cycles. Values above 7 have consistently coincided with major cycle tops; values below 0 signal extreme undervaluation relative to holder cost basis.',
        'hint':        '<0 buy zone · 0–3 fair · 3–7 caution · >7 top zone',
        'api':         'mvrv_zscore',
        'value_field': 'z_score',
        'value_fmt':   '.2f',
        'series':      'values',
        'related':     ['mvrv', 'nupl', 'puell'],
    },
    'lth': {
        'page_title':  'Bitcoin LTH Supply — Long-Term Holder Bitcoin',
        'description': 'Live Bitcoin Long-Term Holder supply (BTC unmoved >1 year). Growing LTH supply = accumulation and conviction.',
        'h1':          'Bitcoin Long-Term Holder Supply',
        'subtitle':    'BTC held for more than 1 year',
        'body':        'Long-Term Holder supply counts all Bitcoin that has not moved in over 1 year. A growing LTH supply signals conviction and supply contraction — holders refuse to sell. When LTH supply starts declining near market tops, experienced holders are distributing into strength. The LTH Realized Price acts as a macro support level across cycles.',
        'hint':        'Growing LTH supply = accumulation · Declining = distribution phase',
        'api':         'lth_sth',
        'value_field': 'lth_supply',
        'value_fmt':   ',.0f',
        'value_suffix': ' BTC',
        'series':      None,
        'related':     ['sth', 'hodl', 'rhodl'],
    },
    'sth': {
        'page_title':  'Bitcoin STH Supply — Short-Term Holder Bitcoin',
        'description': 'Live Bitcoin Short-Term Holder supply (BTC moved within 1 year). Price below STH realized price = capitulation risk.',
        'h1':          'Bitcoin Short-Term Holder Supply',
        'subtitle':    'BTC held for less than 1 year',
        'body':        'Short-Term Holder supply tracks all Bitcoin moved within the last year. High STH supply relative to LTH reflects a market dominated by recent buyers. The STH Realized Price — the average entry price of short-term holders — is a critical level. When spot price falls below it, recent buyers are underwater and capitulation risk rises sharply.',
        'hint':        'Price below STH realized price = capitulation risk for recent buyers',
        'api':         'lth_sth',
        'value_field': 'sth_supply',
        'value_fmt':   ',.0f',
        'value_suffix': ' BTC',
        'series':      None,
        'related':     ['lth', 'hodl', 'sopr'],
    },
    'stf': {
        'page_title':  'Bitcoin Stock-to-Flow — Scarcity Model',
        'description': 'Live Bitcoin Stock-to-Flow ratio and model price. SF doubles after each halving. Compare current price vs scarcity-implied fair value.',
        'h1':          'Bitcoin Stock-to-Flow',
        'subtitle':    'Supply scarcity model (SF ratio)',
        'body':        'Stock-to-Flow divides Bitcoin\'s circulating supply by its annual issuance. After each halving, SF doubles, making Bitcoin progressively scarcer. PlanB\'s model maps SF to price via a power law, providing a scarcity-implied fair value. Halvings are clearly visible as step-changes in the SF ratio. The deviation from model price shows how far current price is from the model expectation.',
        'hint':        'Price near/below model = scarcity undervalued · Large premium = extended vs model',
        'api':         'stf',
        'value_field': 'sf',
        'value_fmt':   '.1f',
        'series':      'values',
        'related':     ['puell', 'hashrate', 'mvrv'],
    },
    'hashrate': {
        'page_title':  'Bitcoin Hash Rate — Network Mining Power',
        'description': 'Live Bitcoin network hash rate in EH/s. Rising hashrate = stronger security. Sustained decline = miner capitulation near market bottoms.',
        'h1':          'Bitcoin Hash Rate',
        'subtitle':    'Network mining power (EH/s)',
        'body':        'Hash Rate measures the total computational power directed at Bitcoin mining, in Exahashes per second (EH/s). A rising hash rate means more miners are competing, strengthening network security. Sustained declines reflect miner capitulation — unprofitable miners shutting down — which has historically coincided with market bottoms and strong buying opportunities.',
        'hint':        'Rising hashrate = security growth · Decline = miner stress / potential bottom',
        'api':         'hashrate',
        'value_field': 'hashrate_eh',
        'value_fmt':   '.1f',
        'value_suffix': ' EH/s',
        'series':      'values',
        'related':     ['puell', 'stf', 'mvrv'],
    },
    'hodl': {
        'page_title':  'Bitcoin HODL Waves — Age Distribution of BTC Supply',
        'description': 'Live Bitcoin HODL Waves showing age distribution of all BTC supply. Rising LTH share signals conviction and supply contraction.',
        'h1':          'Bitcoin HODL Waves',
        'subtitle':    'Age distribution of the entire Bitcoin supply',
        'body':        'HODL Waves show what percentage of Bitcoin supply has not moved within each time band. A rising Long-Term Holder (LTH) share — coins unmoved for over 1 year — signals conviction and supply contraction. Distribution phases are visible when old coins start moving, reducing the LTH percentage. This metric provides a macro view of holder behavior across all market cycles.',
        'hint':        'LTH >70% = strong accumulation · LTH <50% = distribution phase',
        'api':         'hodl',
        'value_field': 'lth_pct',
        'value_fmt':   '.1f',
        'value_suffix': '% LTH',
        'series':      None,
        'related':     ['lth', 'sth', 'rhodl'],
    },
    'rsi': {
        'page_title':  'Bitcoin RSI — Relative Strength Index',
        'description': 'Live Bitcoin RSI (14-period). Above 70 = overbought; below 30 = oversold. Available in multiple timeframes.',
        'h1':          'Bitcoin RSI',
        'subtitle':    'Relative Strength Index (14-period)',
        'body':        'RSI measures the speed and magnitude of recent price changes on a 0–100 scale. Values above 70 signal overbought conditions; below 30 oversold. In bull markets RSI tends to hold between 40–90; in bear markets 10–60. The 14-period is the classic setting used across all timeframes from intraday to weekly.',
        'hint':        '<30 oversold · 30–50 bearish · 50–70 bullish · >70 overbought',
        'api':         'rsi',
        'value_field': 'current',
        'value_fmt':   '.1f',
        'series':      'rsi',
        'related':     ['ema', 'bb', 'price'],
    },
    'ema': {
        'page_title':  'Bitcoin EMA — Exponential Moving Averages (20/50/200)',
        'description': 'Live Bitcoin EMA 20, 50, and 200. Price above EMA 200 = bull market. Golden cross (50/200) = classic buy signal.',
        'h1':          'Bitcoin EMA',
        'subtitle':    'Exponential Moving Averages 20 / 50 / 200',
        'body':        'EMAs weight recent prices more than older ones, making them more responsive to current market conditions. EMA 20 tracks short-term momentum, EMA 50 the medium-term trend, EMA 200 the macro trend. Price above EMA 200 defines a bull market. A golden cross (EMA 50 crossing above EMA 200) is a classic buy signal; a death cross (EMA 50 crossing below EMA 200) is bearish.',
        'hint':        'Price above EMA 200 = bull market · Golden cross = buy · Death cross = bearish',
        'api':         'ema',
        'value_field': 'ema200_val',
        'value_fmt':   ',.0f',
        'value_prefix': '$',
        'series':      'ema200',
        'related':     ['rsi', 'bb', 'price'],
    },
    'bb': {
        'page_title':  'Bitcoin Bollinger Bands — Volatility & Price Extremes',
        'description': 'Live Bitcoin Bollinger Bands (20-period, ±2σ). Price near upper band = overbought; near lower = oversold. Squeeze = breakout incoming.',
        'h1':          'Bitcoin Bollinger Bands',
        'subtitle':    '20-period SMA ± 2 standard deviations',
        'body':        'Bollinger Bands wrap price between a 20-period SMA (middle band) and upper/lower bands at ±2 standard deviations. Price touching the upper band signals overbought conditions; the lower band oversold. Bandwidth measures volatility — a squeeze (very narrow bands) often precedes a strong directional breakout. Bands widen during high volatility and contract during consolidation.',
        'hint':        'Price near upper = overbought · Price near lower = oversold · Squeeze = breakout incoming',
        'api':         'bb',
        'value_field': 'bandwidth_val',
        'value_fmt':   '.1f',
        'value_suffix': '% bandwidth',
        'series':      'bb_mid',
        'related':     ['rsi', 'ema', 'price'],
    },
    'tx_count': {
        'page_title':  'Bitcoin Daily Transaction Count — On-Chain Activity',
        'description': 'Live daily Bitcoin transaction count. Rising txs + rising price = fundamental growth. Divergence = speculative caution.',
        'h1':          'Bitcoin Daily Transactions',
        'subtitle':    'Daily on-chain transaction count',
        'body':        'Daily transaction count measures the number of on-chain Bitcoin transactions, excluding coinbase (miner reward) transactions. Rising activity signals growing network usage. A divergence — price rising while transaction count falls — can indicate a speculative rally not supported by genuine on-chain demand.',
        'hint':        'Rising count + rising price = fundamental growth · Divergence = speculative caution',
        'api':         'tx_stats',
        'value_field': 'tx_count',
        'value_fmt':   ',.0f',
        'series':      'tx_counts',
        'related':     ['active_addresses', 'nvt', 'avg_fee'],
    },
    'avg_fee': {
        'page_title':  'Bitcoin Average Transaction Fee',
        'description': 'Live Bitcoin average transaction fee in BTC. Fee spikes signal high block space demand during bull peaks or mempool congestion.',
        'h1':          'Bitcoin Average Transaction Fee',
        'subtitle':    'Average fee per on-chain transaction (BTC)',
        'body':        'Average fee per transaction measures how much users collectively pay for block space inclusion. Fee spikes signal high block space demand — typically during bull market peaks, inscription activity surges, or mempool congestion. Sustained low fees indicate reduced urgency and lower on-chain activity.',
        'hint':        'Fee spike = high block space demand · Low fee = network underutilized',
        'api':         'tx_stats',
        'value_field': 'avg_fee_btc',
        'value_fmt':   '.6f',
        'value_suffix': ' BTC',
        'series':      'avg_fees',
        'related':     ['tx_count', 'hashrate', 'active_addresses'],
    },
    'price': {
        'page_title':  'Bitcoin Price — Live BTC/USD Chart',
        'description': 'Live Bitcoin price in USD from Kraken (XBTUSD). Updated every 7 minutes. Multiple timeframes from 15 minutes to daily.',
        'h1':          'Bitcoin Price',
        'subtitle':    'BTC/USD — Kraken spot price',
        'body':        'The Bitcoin price displayed is the BTC/USD spot price sourced from Kraken (pair XBTUSD), updated every 7 minutes. Multiple timeframes are available from 15-minute to daily candles. The close price is used as the reference for all technical indicators on BTCFunk.',
        'hint':        'Source: Kraken XBTUSD · Updated every 7 minutes · Timeframes: 15m 30m 1h 4h 12h 1d',
        'api':         'price',
        'value_field': 'close',
        'value_fmt':   ',.0f',
        'value_prefix': '$',
        'series':      'close',
        'related':     ['rsi', 'ema', 'bb'],
    },
    'volume': {
        'page_title':  'Bitcoin Trading Volume — BTC/USD Daily Volume',
        'description': 'Live Bitcoin trading volume in USD from Kraken. Volume confirms price moves — breakouts on high volume are stronger signals.',
        'h1':          'Bitcoin Trading Volume',
        'subtitle':    'BTC/USD trading volume — Kraken',
        'body':        'Bitcoin trading volume measures the total amount of BTC traded on Kraken (XBTUSD pair) within each candle. Volume confirms or contradicts price moves — a breakout accompanied by high volume is a stronger signal than one on low volume. Volume spikes often mark key reversals or the beginning of a new trend.',
        'hint':        'High volume breakout = strong signal · Low volume move = weak / suspect',
        'api':         'price',
        'value_field': 'volume',
        'value_fmt':   ',.0f',
        'series':      'volume',
        'related':     ['price', 'rsi', 'active_addresses'],
    },
}

METRIC_LABELS = {k: v['h1'] for k, v in METRICS_META.items()}

METRIC_QUERIES = {
    'mvrv': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- Realized Cap: sum each unspent output at the price when it was created
-- Market Cap / Realized Cap = MVRV Ratio
SELECT
    DATE(o.block_timestamp)  AS day,
    SUM(o.value) / 1e8       AS btc_value   -- current unspent BTC per creation day
FROM `bigquery-public-data.crypto_bitcoin.outputs` o
LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
    ON  o.transaction_hash = i.spent_transaction_hash
    AND o.index            = i.spent_output_index
WHERE i.transaction_hash IS NULL   -- UTXO: never spent
GROUP BY day
ORDER BY day""",
    },
    'sopr': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- SOPR = sum(value at spend time) / sum(value at creation time)
-- Join inputs to their originating outputs to get acquisition price
SELECT
    DATE(i.block_timestamp)  AS spend_day,
    DATE(o.block_timestamp)  AS creation_day,
    SUM(o.value) / 1e8       AS btc_amount
FROM `bigquery-public-data.crypto_bitcoin.inputs` i
JOIN `bigquery-public-data.crypto_bitcoin.outputs` o
    ON  i.spent_transaction_hash = o.transaction_hash
    AND i.spent_output_index     = o.index
WHERE o.value > 0
GROUP BY spend_day, creation_day
ORDER BY spend_day""",
    },
    'nvt': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- NVT = Market Cap / On-Chain Transaction Volume (28-day MA)
-- Transaction volume: sum of all outputs per day
SELECT
    DATE(block_timestamp)  AS day,
    SUM(value) / 1e8       AS btc_volume
FROM `bigquery-public-data.crypto_bitcoin.outputs`
WHERE value > 0
GROUP BY day
ORDER BY day""",
    },
    'nupl': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- NUPL = 1 - (1 / MVRV) = (Market Cap - Realized Cap) / Market Cap
-- Uses the same UTXO query as MVRV to compute Realized Cap
SELECT
    DATE(o.block_timestamp)  AS day,
    SUM(o.value) / 1e8       AS btc_value
FROM `bigquery-public-data.crypto_bitcoin.outputs` o
LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
    ON  o.transaction_hash = i.spent_transaction_hash
    AND o.index            = i.spent_output_index
WHERE i.transaction_hash IS NULL
GROUP BY day
ORDER BY day""",
    },
    'puell': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- Puell Multiple = Daily miner revenue / 365-day MA of miner revenue
-- Miner revenue = sum of coinbase transaction outputs per day
SELECT
    DATE(block_timestamp)       AS day,
    SUM(output_value) / 1e8     AS revenue_btc
FROM `bigquery-public-data.crypto_bitcoin.transactions`
WHERE is_coinbase = TRUE
GROUP BY day
ORDER BY day""",
    },
    'rhodl': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- RHODL = BTC unspent 1–2 years / BTC unspent 1 day–1 week
-- Uses UTXO set: outputs never spent, grouped by creation date
SELECT
    DATE(o.block_timestamp)  AS creation_day,
    SUM(o.value) / 1e8       AS btc_value
FROM `bigquery-public-data.crypto_bitcoin.outputs` o
LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
    ON  o.transaction_hash = i.spent_transaction_hash
    AND o.index            = i.spent_output_index
WHERE i.transaction_hash IS NULL
  AND o.value > 0
GROUP BY creation_day
ORDER BY creation_day""",
    },
    'supply_profit': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- Supply in Profit = % of UTXOs whose creation-day price < current price
-- Requires joining UTXO set with historical BTC/USD price series
SELECT
    DATE(o.block_timestamp)  AS creation_day,
    SUM(o.value) / 1e8       AS btc_value
FROM `bigquery-public-data.crypto_bitcoin.outputs` o
LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
    ON  o.transaction_hash = i.spent_transaction_hash
    AND o.index            = i.spent_output_index
WHERE i.transaction_hash IS NULL
  AND o.value > 0
GROUP BY creation_day
ORDER BY creation_day""",
    },
    'cdd': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- CDD = sum(BTC × days_since_creation) for all coins spent on a given day
-- Age = spend_day - creation_day (in days)
SELECT
    DATE(i.block_timestamp)  AS spend_day,
    DATE(o.block_timestamp)  AS creation_day,
    SUM(o.value) / 1e8       AS btc_amount
FROM `bigquery-public-data.crypto_bitcoin.inputs` i
JOIN `bigquery-public-data.crypto_bitcoin.outputs` o
    ON  i.spent_transaction_hash = o.transaction_hash
    AND i.spent_output_index     = o.index
WHERE o.value > 0
GROUP BY spend_day, creation_day
ORDER BY spend_day""",
    },
    'exchange_flow': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- Exchange Flow: BTC moving into/out of 761 labeled exchange addresses
-- Net flow = inflow - outflow per day
WITH inflows AS (
    SELECT DATE(o.block_timestamp) AS day, SUM(o.value) / 1e8 AS btc
    FROM `bigquery-public-data.crypto_bitcoin.outputs` o,
    UNNEST(o.addresses) AS addr
    WHERE addr IN UNNEST(@exchange_addresses)
    GROUP BY day
),
outflows AS (
    SELECT DATE(i.block_timestamp) AS day, SUM(o.value) / 1e8 AS btc
    FROM `bigquery-public-data.crypto_bitcoin.inputs` i
    JOIN `bigquery-public-data.crypto_bitcoin.outputs` o
        ON  i.spent_transaction_hash = o.transaction_hash
        AND i.spent_output_index     = o.index,
    UNNEST(o.addresses) AS addr
    WHERE addr IN UNNEST(@exchange_addresses)
    GROUP BY day
)
SELECT
    COALESCE(i.day, out.day)     AS day,
    COALESCE(i.btc,   0)         AS inflow,
    COALESCE(out.btc, 0)         AS outflow,
    COALESCE(i.btc, 0) - COALESCE(out.btc, 0) AS net_flow
FROM inflows i
FULL OUTER JOIN outflows out USING (day)
ORDER BY day""",
    },
    'active_addresses': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- Active Addresses: distinct receiving addresses per day
SELECT
    DATE(o.block_timestamp)      AS day,
    COUNT(DISTINCT addr)         AS active_addresses
FROM `bigquery-public-data.crypto_bitcoin.outputs` o,
UNNEST(o.addresses) AS addr
GROUP BY day
ORDER BY day""",
    },
    'whale_tx': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- Whale Transactions: on-chain txs moving >= 10,000,000,000 satoshi (100 BTC)
SELECT
    DATE(block_timestamp)       AS day,
    COUNT(*)                    AS whale_tx_count,
    SUM(output_value) / 1e8     AS btc_volume
FROM `bigquery-public-data.crypto_bitcoin.transactions`
WHERE NOT is_coinbase
  AND output_value >= 10000000000   -- 100 BTC in satoshi
GROUP BY day
ORDER BY day""",
    },
    'mvrv_zscore': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- MVRV Z-Score = (Market Cap - Realized Cap) / stddev(Market Cap)
-- Normalized over the full history since 2013
-- Uses the same UTXO query as MVRV for Realized Cap
SELECT
    DATE(o.block_timestamp)  AS day,
    SUM(o.value) / 1e8       AS btc_value
FROM `bigquery-public-data.crypto_bitcoin.outputs` o
LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
    ON  o.transaction_hash = i.spent_transaction_hash
    AND o.index            = i.spent_output_index
WHERE i.transaction_hash IS NULL
GROUP BY day
ORDER BY day""",
    },
    'lth': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- LTH Supply: UTXOs unspent for more than 365 days (Long-Term Holders)
SELECT
    DATE(o.block_timestamp)  AS creation_day,
    SUM(o.value) / 1e8       AS btc_value
FROM `bigquery-public-data.crypto_bitcoin.outputs` o
LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
    ON  o.transaction_hash = i.spent_transaction_hash
    AND o.index            = i.spent_output_index
WHERE i.transaction_hash IS NULL
  AND o.value > 0
  AND DATE(o.block_timestamp) <= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
GROUP BY creation_day
ORDER BY creation_day""",
    },
    'sth': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- STH Supply: UTXOs unspent for less than 365 days (Short-Term Holders)
SELECT
    DATE(o.block_timestamp)  AS creation_day,
    SUM(o.value) / 1e8       AS btc_value
FROM `bigquery-public-data.crypto_bitcoin.outputs` o
LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
    ON  o.transaction_hash = i.spent_transaction_hash
    AND o.index            = i.spent_output_index
WHERE i.transaction_hash IS NULL
  AND o.value > 0
  AND DATE(o.block_timestamp) > DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
GROUP BY creation_day
ORDER BY creation_day""",
    },
    'stf': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- Stock-to-Flow = Circulating Supply / Annual Issuance
-- Annual issuance derived from coinbase transaction outputs
SELECT
    DATE(block_timestamp)       AS day,
    SUM(output_value) / 1e8     AS daily_issuance_btc
FROM `bigquery-public-data.crypto_bitcoin.transactions`
WHERE is_coinbase = TRUE
GROUP BY day
ORDER BY day""",
    },
    'hashrate': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- Hash Rate derived from block difficulty (bits field) and block count per day
-- Formula: hashrate (H/s) = difficulty × 2^32 / 600; convert to EH/s (/1e18)
SELECT
    DATE(timestamp)    AS day,
    ANY_VALUE(bits)    AS bits,         -- difficulty bits (compact format)
    COUNT(*)           AS block_count   -- blocks mined that day
FROM `bigquery-public-data.crypto_bitcoin.blocks`
GROUP BY day
ORDER BY day""",
    },
    'hodl': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- HODL Waves: UTXO set grouped by creation age bands
-- Each band = % of circulating supply unmoved within that time window
SELECT
    DATE(o.block_timestamp)  AS creation_day,
    SUM(o.value) / 1e8       AS btc_value
FROM `bigquery-public-data.crypto_bitcoin.outputs` o
LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
    ON  o.transaction_hash = i.spent_transaction_hash
    AND o.index            = i.spent_output_index
WHERE i.transaction_hash IS NULL
  AND o.value > 0
GROUP BY creation_day
ORDER BY creation_day""",
    },
    'tx_count': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- Daily transaction count, average fee and volume
-- Excludes coinbase (miner reward) transactions
SELECT
    DATE(block_timestamp)       AS day,
    COUNT(*)                    AS tx_count,
    SUM(output_value) / 1e8     AS volume_btc,
    SUM(fee) / 1e8              AS fees_btc
FROM `bigquery-public-data.crypto_bitcoin.transactions`
WHERE NOT is_coinbase
GROUP BY day
ORDER BY day""",
    },
    'avg_fee': {
        'source': 'Google BigQuery — bigquery-public-data.crypto_bitcoin',
        'sql': """\
-- Average fee per transaction = total fees / transaction count
-- Excludes coinbase transactions; fee in BTC = fee_satoshi / 1e8
SELECT
    DATE(block_timestamp)                        AS day,
    COUNT(*)                                     AS tx_count,
    SUM(fee) / 1e8                               AS total_fees_btc,
    (SUM(fee) / 1e8) / NULLIF(COUNT(*), 0)       AS avg_fee_btc
FROM `bigquery-public-data.crypto_bitcoin.transactions`
WHERE NOT is_coinbase
GROUP BY day
ORDER BY day""",
    },
    'rsi': {
        'source': 'Kraken REST API — OHLCV data',
        'sql': """\
-- RSI is computed from BTC/USD OHLCV candles fetched from Kraken
-- RSI(14) = 100 - (100 / (1 + RS)) where RS = avg_gain / avg_loss
-- Endpoint: GET https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440
-- interval: 15 | 30 | 60 | 240 | 720 | 1440 (minutes)""",
    },
    'ema': {
        'source': 'Kraken REST API — OHLCV data',
        'sql': """\
-- EMAs computed from BTC/USD close prices fetched from Kraken
-- EMA(n) = price × k + EMA_prev × (1 - k)  where k = 2 / (n + 1)
-- Periods: 20, 50, 200
-- Endpoint: GET https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440""",
    },
    'bb': {
        'source': 'Kraken REST API — OHLCV data',
        'sql': """\
-- Bollinger Bands computed from BTC/USD close prices (Kraken)
-- Middle band = SMA(20); Upper = SMA + 2σ; Lower = SMA - 2σ
-- Bandwidth = (Upper - Lower) / Middle × 100
-- Endpoint: GET https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440""",
    },
    'price': {
        'source': 'Kraken REST API — OHLCV data',
        'sql': """\
-- BTC/USD spot price — OHLCV candles from Kraken (pair: XBTUSD)
-- Updated every 7 minutes; multiple timeframes available
-- Endpoint: GET https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440
-- interval: 15 | 30 | 60 | 240 | 720 | 1440 (minutes)
-- Response fields: time, open, high, low, close, vwap, volume, count""",
    },
    'volume': {
        'source': 'Kraken REST API — OHLCV data',
        'sql': """\
-- Trading volume from Kraken BTC/USD (XBTUSD) OHLCV candles
-- Volume = sum of BTC traded within the candle interval
-- Endpoint: GET https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440
-- interval: 15 | 30 | 60 | 240 | 720 | 1440 (minutes)""",
    },
}
