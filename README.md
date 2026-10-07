# Orderflow Trading Research

This project is the research and backtesting component of a larger market data pipeline.

A research and backtesting framework for processing historical market data in a reproducible and consistent way based on a custom trading strategy, with support for machine learning.

Market data is replayed from a PostgreSQL database in chronological order. Given the same input data and configuration, the strategy produces the same sequence of decisions, making backtests reproducible. Results can be exported to reports and datasets for further ML research.

## Main Components

- **Market Data Replay** – `MarketFeed` replays data from selected sessions and session pairs in chronological order, including trades, order book data, open interest, OHLCV and news.

- **Analyzers** – derived market indicators are defined in `resource_config.py`, including:
  - timeframe candles (`TimeframeAnalyzer`, `OHLCVTimeframeAnalyzer`)
  - volume delta and cumulative volume delta (`VolumeDeltaAnalyzer`, `CVDAnalyzer`)
  - volume profile (`VolumeProfileAnalyzer`, `OHLCVVolumeProfileAnalyzer`)
  - large trades (`BigTradesAnalyzer`)
  - open interest (`OpenInterestAnalyzer`)
  - microprice deviation and order book imbalance
  - AI-based news analysis (`NewsAnalyzer`) using a local Ollama model

- **Strategy** – strategies are located under `strategies/` and inherit from `BaseStrategy`. `StrategyFramework` provides access to analyzers and the order management interface, including market orders and reduce-only orders. Each strategy also requires importing `*`  from `strategies.core.essentials`, which provides access to types, modules, and classes that can be useful when implementing a strategy.

  Example: [`TestStrategy`](strategies/executable/test.py)

- **Execution Simulation** – `PositionManager` handles positions, orders, stop orders, maker/taker fees and the initial account balance.

- **Performance Analysis** – generates equity curves and statistics such as win rate, ROI, maximum drawdown, PnL, expectancy, average profit/loss and average holding time. Results are available both per session pair and cumulatively.

- **Live Dashboard** – a Dash/Plotly interface displaying price charts, context charts, trades, equity curves, statistics and news.

- **Reports** – PDF reports are generated for individual session pairs and cumulative results. Trade data can also be exported to Excel. Reports are stored in the `reports/` directory and organized by strategy and runtime.

- **ML Export** – closed real and shadow trades can be exported in Parquet format using a versioned schema for training and evaluating ML models.

## Data Source

This project uses historical market data collected and stored in PostgreSQL by a separate data collection project.

The collector is responsible for collecting and storing:
- trades
- order book data
- open interest
- OHLCV data
- market news

The database itself is not included in this repository due to the size of the historical dataset.

The data collection project is available here:

**[Orderflow Data Collector](https://github.com/Tibor0234/OrderflowDataCollector)**

## Main Data Flow

```mermaid
flowchart LR
    DB[(PostgreSQL)] --> Feed[MarketFeed]
    Feed --> Managers[Data Managers]
    Managers --> Analyzers[Analyzers]
    Analyzers --> Strategy[Strategy]
    Strategy --> Positions[PositionManager]
    Positions --> Output[Dashboard / Reports / ML Export]
```

## Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

The project requires a PostgreSQL database containing the market data used for replay.

Create a `.env` file in the project root and configure the database connection:

```env
POSTGRES_URL=postgresql://user:password@host:port/dbname
```

### News Analysis

AI-based news analysis requires a locally running [Ollama](https://ollama.com/) instance with the model specified in `config.yaml`.

## Configuration

### `config.yaml`

Contains runtime configuration such as:

- symbols
- session IDs
- initial account balance
- trading fees
- displayed statistics
- report and ML export settings
- news analysis settings

If `symbols` or `session_ids` is empty, all available data is processed.

### `resource_config.py`

Defines the strategy and analyzers used by the framework, including their names and parameters.

Analyzers automatically connect to the nearest compatible previous data source.

## Running

Start the application from the project root:

```bash
python main.py
```

## Planned Improvements

- Extend the available analyzers and their functionality.
- Import trained ML models and use them as part of the trading strategy.
- Add automated tests for the main logical modules.
- Add an interactive JavaScript-based frontend.
