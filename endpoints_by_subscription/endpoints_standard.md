# API Endpoints Standard Tier

#### Stock Endpoints

- `/stock/at_time/quote` - Quote
- `/stock/at_time/trade` - Trade
- `/stock/history/eod` - End of Day
- `/stock/history/ohlc` - Open High Low Close
- `/stock/history/quote` - Quote
- `/stock/history/trade` - Trade
- `/stock/history/trade_quote` - Trade Quote
- `/stock/list/dates/{request_type}` - Dates
- `/stock/list/symbols` - Symbols
- `/stock/snapshot/market_value` - Market Value
- `/stock/snapshot/ohlc` - Open High Low Close
- `/stock/snapshot/quote` - Quote
- `/stock/snapshot/trade` - Trade

#### Option Endpoints

- `/option/at_time/quote` - Quote
- `/option/at_time/trade` - Trade
- `/option/history/eod` - End of Day
- `/option/history/greeks/eod` - End of Day Greeks
- `/option/history/greeks/first_order` - First Order Greeks
- `/option/history/greeks/implied_volatility` - Implied Volatility
- `/option/history/ohlc` - Open High Low Close
- `/option/history/open_interest` - Open Interest
- `/option/history/quote` - Quote
- `/option/history/trade` - Trade
- `/option/history/trade_quote` - Trade Quote
- `/option/list/contracts/{request_type}` - Contracts
- `/option/list/dates/{request_type}` - Dates
- `/option/list/expirations` - Expirations
- `/option/list/strikes` - Strikes
- `/option/list/symbols` - Symbols
- `/option/snapshot/greeks/first_order` - First Order Greeks
- `/option/snapshot/greeks/implied_volatility` - Implied Volatility
- `/option/snapshot/market_value` - Market Value
- `/option/snapshot/ohlc` - Open High Low Close
- `/option/snapshot/open_interest` - Open Interest
- `/option/snapshot/quote` - Quote
- `/option/snapshot/trade` - Trade

#### Index Endpoints

- `/index/at_time/price` - Price
- `/index/history/eod` - End of Day
- `/index/history/ohlc` - Open High Low Close
- `/index/history/price` - Price
- `/index/list/dates` - Dates
- `/index/list/symbols` - Symbols
- `/index/snapshot/market_value` - Market Value
- `/index/snapshot/ohlc` - Open High Low Close
- `/index/snapshot/price` - Price

#### Calendar Endpoints

- `/calendar/on_date` - On Date
- `/calendar/today` - Today
- `/calendar/year_holidays` - Year Holidays
