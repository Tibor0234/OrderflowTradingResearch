export type Timeframe = number;

export function formatTimeframe(seconds: Timeframe): string {
  if (!Number.isSafeInteger(seconds) || seconds <= 0) return '';

  const units: readonly [number, string][] = [
    [86_400, 'd'],
    [3_600, 'h'],
    [60, 'm'],
    [1, 's'],
  ];
  let remaining = seconds;
  const parts: string[] = [];

  for (const [unitSeconds, unitName] of units) {
    const count = Math.floor(remaining / unitSeconds);
    if (count > 0) {
      parts.push(`${count}${unitName}`);
      remaining %= unitSeconds;
    }
  }

  return parts.join('-');
}

export interface Candle {
  /** Candle opening time, epoch milliseconds. Stable identifier within a symbol/timeframe series. */
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TimeSeriesPoint {
  timestamp: number;
  value: number;
}

export interface SnapshotRecord {
  time: number;
  value: number;
}

export interface VolumeProfileSnapshot {
  time: number;
  bins: readonly VolumeProfileBin[];
  poc: { price: number; volume: number } | null;
  value_area: { low: number; high: number } | null;
}

export interface NewsSnapshotItem {
  time: number;
  category: string;
  headline: string;
  summary: string;
  features: NewsAggregatedMetrics;
}

export interface NewsSnapshot {
  items: readonly NewsSnapshotItem[];
  aggregated: NewsAggregatedMetrics;
}

export type ResourceType =
  | 'timeframe'
  | 'ohlcv_timeframe'
  | 'ohlcv_volume_profile'
  | 'volume_delta'
  | 'cvd'
  | 'volume_profile'
  | 'open_interest'
  | 'big_trades'
  | 'news';

export interface TimeframeResourceInit {
  resource_type: 'timeframe';
  target: string;
  candle_seconds: number;
  length: number;
  snapshot?: { candles: readonly ContextCandle[] };
}

export interface IndicatorResourceInit {
  resource_type: 'volume_delta' | 'cvd';
  target: string;
  length: number;
  big_trades?: boolean;
  big_trades_pct?: number;
  snapshot?: { records: readonly SnapshotRecord[] };
}

export interface VolumeProfileResourceInit {
  resource_type: 'volume_profile';
  target: string;
  price_bin_count: number;
  value_area_pct: number;
  snapshot?: VolumeProfileSnapshot;
}

export interface OpenInterestResourceInit {
  resource_type: 'open_interest';
  target: string;
  length: number;
  snapshot?: { records: readonly SnapshotRecord[] };
}

export interface BigTradesResourceInit {
  resource_type: 'big_trades';
  target: string;
  top_pct: number;
  snapshot?: { trades: readonly BigTrade[] };
}

export interface NewsResourceInit {
  resource_type: 'news';
  target: string;
  snapshot?: NewsSnapshot;
}

export interface ContextTimeframeResourceInit {
  resource_type: 'ohlcv_timeframe';
  target: string;
  period: string;
  snapshot?: { interval: string; candles: readonly ContextCandle[] };
}

export interface ContextVolumeProfileResourceInit {
  resource_type: 'ohlcv_volume_profile';
  target: string;
  price_bin_count: number;
  snapshot?: VolumeProfileSnapshot;
}

export interface ResourceInitMessage {
  type: 'resource_init';
  data:
    | TimeframeResourceInit
    | ContextTimeframeResourceInit
    | ContextVolumeProfileResourceInit
    | IndicatorResourceInit
    | VolumeProfileResourceInit
    | OpenInterestResourceInit
    | BigTradesResourceInit
    | NewsResourceInit;
}

export interface TimeframeMarketUpdate {
  resource_type: 'timeframe';
  target: string;
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface IndicatorMarketUpdate {
  resource_type: 'volume_delta' | 'cvd';
  target: string;
  time: number;
  value: number;
}

export interface VolumeProfileBin {
  low: number;
  size: number;
  volume: number;
}

export interface VolumeProfileMarketUpdate {
  resource_type: 'volume_profile';
  target: string;
  bins: readonly VolumeProfileBin[];
  poc: { price: number; volume: number } | null;
  value_area: { low: number; high: number } | null;
}

export interface OpenInterestMarketUpdate {
  resource_type: 'open_interest';
  target: string;
  time: number;
  value: number;
}

export interface BigTrade {
  time: number;
  price: number;
  quantity: number;
  side: 1 | -1;
}

export interface BigTradesMarketUpdate {
  resource_type: 'big_trades';
  target: string;
  trades: readonly BigTrade[];
}

export interface NewsAggregatedMetrics {
  sentiment: number;
  severity: number;
  market_relevance: number;
  symbol_relevance: number;
}

export interface NewsMarketUpdate {
  resource_type: 'news';
  target: string;
  time: number;
  headline: string;
  aggregated: NewsAggregatedMetrics;
}

export interface NewsHeadline {
  time: number;
  headline: string;
  category?: string;
  summary?: string;
  features?: NewsAggregatedMetrics;
}

export interface NewsPanelState {
  target: string;
  latestUpdateTime: number | null;
  aggregated: NewsAggregatedMetrics | null;
  headlines: readonly NewsHeadline[];
}

export interface AnalysisEquityCurveState {
  target: string;
  name: string;
  points: readonly TimeSeriesPoint[];
  startingBalance: number | null;
}

export type AnalysisStatisticValue = string | number | boolean | null;

export interface AnalysisStatistic {
  key: string;
  value: AnalysisStatisticValue;
}

export interface AnalysisStatisticsState {
  target: string;
  name: string;
  statistics: readonly AnalysisStatistic[];
}

export interface AnalysisEquityCurveInitMessage {
  type: 'analysis_init';
  data: {
    analysis_type: 'equity_curve';
    target: string;
    name: string;
    snapshot?: {
      points: readonly TimeSeriesPoint[];
      startingBalance: number | null;
    };
  };
}

export interface AnalysisStatisticsInitMessage {
  type: 'analysis_init';
  data: {
    analysis_type: 'statistics';
    target: string;
    name: string;
    snapshot?: { statistics: readonly AnalysisStatistic[] };
  };
}

export interface AnalysisEquityCurveUpdateMessage {
  type: 'analysis_update';
  data: {
    analysis_type: 'equity_curve';
    target: string;
    time: number;
    equity: number;
    startingBalance: number | null;
  };
}

export interface AnalysisStatisticsUpdateMessage {
  type: 'analysis_update';
  data: {
    analysis_type: 'statistics';
    target: string;
    statistics: readonly AnalysisStatistic[];
  };
}

export interface AnalysisEquityCurveSessionStartMessage {
  type: 'analysis_session_start';
  data: {
    analysis_type: 'equity_curve';
    target: string;
  };
}

export type AnalysisMessage =
  | AnalysisEquityCurveInitMessage
  | AnalysisStatisticsInitMessage
  | AnalysisEquityCurveUpdateMessage
  | AnalysisStatisticsUpdateMessage
  | AnalysisEquityCurveSessionStartMessage;

export interface TradePosition {
  type: 'trade';
  id: string;
  side: string;
  value: string;
  leverage: string;
  pnl: string;
  execution_price: string;
}

export interface IncreaseOrderPosition {
  type: 'increase_order';
  id: string;
  source_id: string | null;
  side: string | null;
  value: string;
  leverage: string;
  entry_price: string;
}

export interface LimitOrderPosition {
  type: 'order';
  id: string;
  side: string;
  value: string;
  leverage: string;
  entry_price: string;
}

export interface StopOrderPosition {
  type: 'take_profit' | 'stop_loss' | 'liquidation_order';
  id: string;
  source_id: string | null;
  side: string | null;
  close_rate: string;
  stop_price: string | null;
}

export type PositionChild = IncreaseOrderPosition | StopOrderPosition;
export type PositionEntity =
  | TradePosition
  | IncreaseOrderPosition
  | LimitOrderPosition
  | StopOrderPosition;

export interface PositionInitMessage {
  type: 'position_init';
  data: {
    trades: TradePosition[];
    orders: (LimitOrderPosition | IncreaseOrderPosition)[];
    stop_orders: StopOrderPosition[];
  };
}

export interface PositionUpdateMessage {
  type: 'position_update';
  data: PositionEntity;
}

export interface PositionRemoveMessage {
  type: 'position_remove';
  data: { id: string };
}

export interface PositionClearMessage {
  type: 'position_clear';
  data: Record<string, never>;
}

export type PositionMessage =
  | PositionInitMessage
  | PositionUpdateMessage
  | PositionRemoveMessage
  | PositionClearMessage;

export interface SessionStartData {
  strategy_name: string;
  session_number: string;
  symbol: string | null;
  progress: string;
}

export interface SessionStartMessage {
  type: 'session_start';
  data: SessionStartData;
}

export interface ProcessEndMessage {
  type: 'process_end';
  data: Record<string, never>;
}

export interface ContextCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface ContextTimeframeMarketUpdate {
  resource_type: 'ohlcv_timeframe';
  target: string;
  interval: string;
  candles: readonly ContextCandle[];
}

export interface ContextVolumeProfileMarketUpdate {
  resource_type: 'ohlcv_volume_profile';
  target: string;
  time: number;
  bins: readonly VolumeProfileBin[];
  poc: { price: number; volume: number } | null;
  value_area: { low: number; high: number } | null;
}

export interface MarketUpdateMessage {
  type: 'market_update';
  data:
    | TimeframeMarketUpdate
    | ContextTimeframeMarketUpdate
    | ContextVolumeProfileMarketUpdate
    | IndicatorMarketUpdate
    | VolumeProfileMarketUpdate
    | OpenInterestMarketUpdate
    | BigTradesMarketUpdate
    | NewsMarketUpdate;
}

export type ServerMessage =
  | ResourceInitMessage
  | MarketUpdateMessage
  | AnalysisMessage
  | SessionStartMessage
  | ProcessEndMessage
  | PositionMessage;

export interface ContextVolumeProfileState extends ContextVolumeProfileResourceInit {
  time: number | null;
  bins: readonly VolumeProfileBin[];
  poc: { price: number; volume: number } | null;
  value_area: { low: number; high: number } | null;
}

export interface ContextChartState {
  target: string;
  id: string;
  period: string;
  interval: string | null;
  candles: readonly ContextCandle[];
  volumeProfile: ContextVolumeProfileState | null;
}

export interface VolumeProfileResourceState extends VolumeProfileResourceInit {
  time: number | null;
  bins: readonly VolumeProfileBin[];
  poc: { price: number; volume: number } | null;
  value_area: { low: number; high: number } | null;
}

export interface OpenInterestResourceState extends OpenInterestResourceInit {
  points: readonly TimeSeriesPoint[];
}

export interface BigTradesResourceState extends BigTradesResourceInit {
  trades: readonly BigTrade[];
}

export type DynamicResourceState =
  | VolumeProfileResourceState
  | OpenInterestResourceState
  | BigTradesResourceState;

export interface MarketSeries {
  candles: readonly Candle[];
  volumeDelta: readonly TimeSeriesPoint[];
  cvd: readonly TimeSeriesPoint[];
}

export type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'closed' | 'error';
