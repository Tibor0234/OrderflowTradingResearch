import { Injectable, OnDestroy, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Subject } from 'rxjs';
import {
  AnalysisEquityCurveState,
  AnalysisMessage,
  AnalysisStatistic,
  AnalysisStatisticValue,
  AnalysisStatisticsState,
  BigTrade,
  Candle,
  ContextChartState,
  ContextCandle,
  ContextVolumeProfileState,
  ConnectionStatus,
  DynamicResourceState,
  IncreaseOrderPosition,
  LimitOrderPosition,
  MarketSeries,
  NewsAggregatedMetrics,
  NewsPanelState,
  NewsSnapshot,
  OpenInterestResourceState,
  PositionEntity,
  PositionInitMessage,
  PositionMessage,
  SnapshotRecord,
  StopOrderPosition,
  ProcessEndMessage,
  ResourceInitMessage,
  ResourceType,
  ServerMessage,
  SessionStartData,
  Timeframe,
  TimeSeriesPoint,
  TradePosition,
  VolumeProfileBin,
  VolumeProfileResourceState,
  VolumeProfileSnapshot,
} from '../../shared/models/market-data.models';

const EMPTY_SERIES: MarketSeries = { candles: [], volumeDelta: [], cvd: [] };
const RECONNECT_BASE_DELAY_MS = 500;
const RECONNECT_MAX_DELAY_MS = 30_000;
const DISPLAY_INTERVAL_MS = 1_000 / 60;

@Injectable({ providedIn: 'root' })
export class MarketDataSocketService implements OnDestroy {
  readonly status = signal<ConnectionStatus>('idle');
  readonly error = signal<string | null>(null);
  readonly series = signal<MarketSeries>(EMPTY_SERIES);
  readonly timeframes = signal<readonly Timeframe[]>([]);
  readonly selectedTimeframe = signal<Timeframe | null>(null);
  readonly selectedCandleUpdateSequence = signal(0);
  private readonly selectedCandleUpdateSubject = new Subject<number>();
  readonly selectedCandleUpdates = this.selectedCandleUpdateSubject.asObservable();
  readonly activeTarget = signal<string | null>(null);
  readonly dynamicResources = signal<readonly DynamicResourceState[]>([]);
  readonly contextCharts = signal<readonly ContextChartState[]>([]);
  readonly newsPanel = signal<NewsPanelState | null>(null);
  readonly analysisEquityCurves = signal<readonly AnalysisEquityCurveState[]>([]);
  readonly analysisStatistics = signal<readonly AnalysisStatisticsState[]>([]);
  readonly positionEntities = signal<readonly PositionEntity[]>([]);
  readonly sessionStart = signal<SessionStartData | null>(null);
  readonly processEnded = signal(false);
  readonly initializedIndicators = signal<
    readonly { target: string; resource_type: 'volume_delta' | 'cvd' }[]
  >([]);
  readonly indicatorTitles = signal({
    volume_delta: 'Volume Delta',
    cvd: 'CVD',
  });

  private socket: WebSocket | null = null;
  private readonly timeframeByTarget = new Map<string, Timeframe>();
  private readonly resourceLengthsByTarget = new Map<string, Map<ResourceType, number>>();
  private readonly resourceInitCache = new Map<string, ResourceInitMessage>();
  private readonly seriesByTarget = new Map<string, MarketSeries>();
  private readonly contextProfilesByTarget = new Map<string, ContextVolumeProfileState>();
  private readonly indicatorTitlesByTarget = new Map<
    string,
    { volume_delta: string; cvd: string }
  >();
  private hasUserSelectedTimeframe = false;
  private hasReceivedLiveMessage = false;
  private started = false;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private displayUpdateTimer: ReturnType<typeof setTimeout> | null = null;
  private lastDisplayUpdateAt = Number.NEGATIVE_INFINITY;

  start(): void {
    if (this.started) return;
    this.started = true;
    this.connect();
  }

  private applyAnalysisMessage(message: AnalysisMessage): void {
    if (message.type === 'analysis_init') {
      if (message.data.analysis_type === 'equity_curve') {
        this.setAnalysisEquityCurve({
          target: message.data.target,
          name: message.data.name,
          points: message.data.snapshot?.points ?? [],
          startingBalance: message.data.snapshot?.startingBalance ?? null,
        });
      } else {
        this.setAnalysisStatistics({
          target: message.data.target,
          name: message.data.name,
          statistics: message.data.snapshot?.statistics ?? [],
        });
      }
      return;
    }

    if (message.type === 'analysis_update') {
      if (message.data.analysis_type === 'equity_curve') {
        const curve = this.analysisEquityCurves().find(
          (item) => item.target === message.data.target,
        );
        if (!curve) return;
        this.setAnalysisEquityCurve({
          ...curve,
          points: this.upsertByTimestamp(curve.points, {
            timestamp: message.data.time,
            value: message.data.equity,
          }),
          startingBalance: message.data.startingBalance,
        });
      } else {
        const statistics = this.analysisStatistics().find(
          (item) => item.target === message.data.target,
        );
        if (!statistics) return;
        this.setAnalysisStatistics({
          ...statistics,
          statistics: message.data.statistics,
        });
      }
      return;
    }

    const curve = this.analysisEquityCurves().find(
      (item) => item.target === message.data.target,
    );
    if (!curve) return;
    this.setAnalysisEquityCurve({ ...curve, points: [] });
  }

  select(timeframe: Timeframe): void {
    if (!this.timeframes().includes(timeframe)) return;
    this.hasUserSelectedTimeframe = true;
    if (this.selectedTimeframe() === timeframe) return;
    this.selectedTimeframe.set(timeframe);
    this.refreshSelectedSeries();
    this.refreshSelectedIndicatorTitles();

    this.start();
  }

  ngOnDestroy(): void {
    this.started = false;
    this.clearReconnectTimer();
    this.clearDisplayUpdateTimer();
    this.disconnect();
  }

  handleMessage(message: ServerMessage): void {
    if (message.type === 'process_end') {
      this.finishInitialResourceReplay();
      this.processEnded.set(true);
      return;
    }

    if (message.type === 'session_start') {
      this.clearMarketUpdateData();
      this.sessionStart.set(message.data);
      if (this.resourceInitCache.size > 0) {
        const resourceInits = [...this.resourceInitCache.values()];
        this.resourceInitCache.clear();
        resourceInits.forEach((resourceInit) => this.registerResource(resourceInit));
      }
      return;
    }

    if (
      message.type === 'position_init' ||
      message.type === 'position_update' ||
      message.type === 'position_remove' ||
      message.type === 'position_clear'
    ) {
      if (message.type !== 'position_init') this.finishInitialResourceReplay();
      this.applyPositionMessage(message);
      return;
    }

    if (message.type === 'resource_init') {
      if (!this.hasReceivedLiveMessage) {
        const key = `${message.data.resource_type}:${message.data.target}`;
        this.resourceInitCache.set(key, message);
      }
      this.registerResource(message);
      return;
    }

    if (message.type === 'market_update') {
      this.finishInitialResourceReplay();
      this.applyMarketUpdate(message.data);
      return;
    }

    if (message.type !== 'analysis_init') this.finishInitialResourceReplay();
    this.applyAnalysisMessage(message);
  }

  private finishInitialResourceReplay(): void {
    this.hasReceivedLiveMessage = true;
    this.resourceInitCache.clear();
  }

  private applyPositionMessage(message: PositionMessage): void {
    if (message.type === 'position_init') {
      this.positionEntities.set([
        ...message.data.trades,
        ...message.data.orders,
        ...message.data.stop_orders,
      ]);
      return;
    }

    if (message.type === 'position_update') {
      this.positionEntities.update((entities) => {
        const index = entities.findIndex((entity) => entity.id === message.data.id);
        if (index === -1) return [...entities, message.data];
        const updated = [...entities];
        updated[index] = message.data;
        return updated;
      });
      return;
    }

    if (message.type === 'position_remove') {
      this.positionEntities.update((entities) =>
        entities.filter((entity) => entity.id !== message.data.id),
      );
      return;
    }

    this.positionEntities.set([]);
  }

  private parseAnalysisInitMessage(parsed: Record<string, unknown>): ServerMessage | null {
    const data = parsed['data'];
    if (!this.isRecord(data)) return null;
    if (data['analysis_type'] === 'statistics') {
      const target = data['target'];
      const name = data['name'];
      if (typeof target !== 'string' || target.length === 0) {
        console.warn(
          '[MarketDataSocketService] Rejected statistics init message',
          parsed,
          'target must be a non-empty string',
        );
        return null;
      }
      if (typeof name !== 'string' || name.trim() === '') {
        console.warn(
          '[MarketDataSocketService] Rejected statistics init message',
          parsed,
          'name must be a non-empty string',
        );
        return null;
      }
      let snapshot: { statistics: readonly AnalysisStatistic[] } | undefined;
      if (data['snapshot'] !== undefined) {
        const snapshotStatistics = data['snapshot'];
        if (!this.isRecord(snapshotStatistics)) return null;
        const requiredKeys = [
          'total_trades',
          'winrate',
          'pnl',
          'roi',
          'max_drawdown',
          'average_trade_duration',
        ];
        if (!this.isRecord(snapshotStatistics)) return null;
        const statistics: AnalysisStatistic[] = [];
        for (const key of requiredKeys) {
          const rawValue = snapshotStatistics[key];
          if (
            rawValue === null &&
            (key === 'winrate' || key === 'average_trade_duration')
          ) {
            statistics.push({ key, value: null });
            continue;
          }
          const value = this.toFiniteNumber(rawValue);
          if (value === null) return null;
          statistics.push({ key, value });
        }
        snapshot = { statistics };
      }
      console.info('[MarketDataSocketService] Accepted statistics init message', parsed);
      return {
        type: 'analysis_init',
        data: { analysis_type: 'statistics', target, name, ...(snapshot ? { snapshot } : {}) },
      };
    }
    if (data['analysis_type'] !== 'equity_curve') return null;

    const target = data['target'];
    if (typeof target !== 'string' || target.length === 0) return null;

    const name = data['name'];
    if (typeof name !== 'string' || name.trim() === '') return null;

    let snapshot:
      | { points: readonly TimeSeriesPoint[]; startingBalance: number | null }
      | undefined;
    if (data['snapshot'] !== undefined) {
      if (!this.isRecord(data['snapshot']) || !Array.isArray(data['snapshot']['points'])) {
        return null;
      }
      const startingBalance = this.parseNullableFiniteNumber(
        data['snapshot']['starting_balance'],
      );
      if (startingBalance === undefined) return null;
      const points: TimeSeriesPoint[] = [];
      for (const rawPoint of data['snapshot']['points']) {
        if (!this.isRecord(rawPoint)) return null;
        const timestamp = this.toFiniteNumber(rawPoint['time']);
        const value = this.toFiniteNumber(rawPoint['equity']);
        if (timestamp === null || !Number.isSafeInteger(timestamp) || value === null) return null;
        points.push({ timestamp, value });
      }
      snapshot = { points, startingBalance };
    }

    return {
      type: 'analysis_init',
      data: { analysis_type: 'equity_curve', target, name, ...(snapshot ? { snapshot } : {}) },
    };
  }

  private parseSnapshotCandles(raw: unknown): ContextCandle[] | null {
    if (!Array.isArray(raw)) return null;
    const candles: ContextCandle[] = [];
    for (const rawCandle of raw) {
      if (!this.isRecord(rawCandle)) return null;
      const time = this.toFiniteNumber(rawCandle['time']);
      const open = this.toFiniteNumber(rawCandle['open']);
      const high = this.toFiniteNumber(rawCandle['high']);
      const low = this.toFiniteNumber(rawCandle['low']);
      const close = this.toFiniteNumber(rawCandle['close']);
      if (
        time === null ||
        !Number.isSafeInteger(time) ||
        open === null ||
        high === null ||
        low === null ||
        close === null ||
        low > high
      ) {
        return null;
      }
      candles.push({ time, open, high, low, close });
    }
    return candles;
  }

  private parseSnapshotRecords(raw: unknown): SnapshotRecord[] | null {
    if (!Array.isArray(raw)) return null;
    const records: SnapshotRecord[] = [];
    for (const rawRecord of raw) {
      if (!this.isRecord(rawRecord)) return null;
      const time = this.toFiniteNumber(rawRecord['time']);
      const value = this.toFiniteNumber(rawRecord['value']);
      if (time === null || !Number.isSafeInteger(time) || value === null) return null;
      records.push({ time, value });
    }
    return records;
  }

  private parseSnapshotBigTrades(raw: unknown): BigTrade[] | null {
    if (!Array.isArray(raw)) return null;
    const trades: BigTrade[] = [];
    for (const rawTrade of raw) {
      if (!this.isRecord(rawTrade)) return null;
      const time = this.toFiniteNumber(rawTrade['time']);
      const price = this.toFiniteNumber(rawTrade['price']);
      const quantity = this.toFiniteNumber(rawTrade['quantity']);
      const side = rawTrade['side'];
      if (
        time === null ||
        !Number.isSafeInteger(time) ||
        price === null ||
        quantity === null ||
        quantity < 0 ||
        (side !== 1 && side !== -1)
      ) {
        return null;
      }
      trades.push({ time, price, quantity, side });
    }
    return trades;
  }

  private warnInvalidResourceSnapshot(resourceType: ResourceType, target: string): void {
    console.warn('[MarketDataSocketService] Ignored invalid resource init snapshot', {
      resource_type: resourceType,
      target,
    });
  }

  private parseVolumeProfileSnapshot(raw: unknown): VolumeProfileSnapshot | null {
    if (!this.isRecord(raw)) return null;
    const time = this.toFiniteNumber(raw['time']);
    if (time === null || !Number.isSafeInteger(time) || !Array.isArray(raw['bins'])) return null;
    const bins: VolumeProfileBin[] = [];
    for (const rawBin of raw['bins']) {
      if (!this.isRecord(rawBin)) return null;
      const low = this.toFiniteNumber(rawBin['low']);
      const size = this.toFiniteNumber(rawBin['size']);
      const volume = this.toFiniteNumber(rawBin['volume']);
      if (low === null || size === null || size <= 0 || volume === null || volume < 0) return null;
      bins.push({ low, size, volume });
    }
    const rawPoc = raw['poc'];
    let poc: VolumeProfileSnapshot['poc'] = null;
    if (rawPoc !== null) {
      if (!this.isRecord(rawPoc)) return null;
      const price = this.toFiniteNumber(rawPoc['price']);
      const volume = this.toFiniteNumber(rawPoc['volume']);
      if (price === null || volume === null || volume < 0) return null;
      poc = { price, volume };
    }
    const rawValueArea = raw['value_area'];
    let valueArea: VolumeProfileSnapshot['value_area'] = null;
    if (rawValueArea !== null) {
      if (!this.isRecord(rawValueArea)) return null;
      const low = this.toFiniteNumber(rawValueArea['low']);
      const high = this.toFiniteNumber(rawValueArea['high']);
      if (low === null || high === null || low > high) return null;
      valueArea = { low, high };
    }
    return { time, bins, poc, value_area: valueArea };
  }

  private parseNewsMetrics(raw: unknown): NewsAggregatedMetrics | null {
    if (!this.isRecord(raw)) return null;
    const sentiment = this.toFiniteNumber(raw['sentiment']);
    const severity = this.toFiniteNumber(raw['severity']);
    const marketRelevance = this.toFiniteNumber(raw['market_relevance']);
    const symbolRelevance = this.toFiniteNumber(raw['symbol_relevance']);
    if (
      sentiment === null ||
      severity === null ||
      marketRelevance === null ||
      symbolRelevance === null
    ) {
      return null;
    }
    return {
      sentiment,
      severity,
      market_relevance: marketRelevance,
      symbol_relevance: symbolRelevance,
    };
  }

  private parseNewsSnapshot(raw: unknown): NewsSnapshot | null {
    if (!this.isRecord(raw) || !Array.isArray(raw['items'])) return null;
    const items: NewsSnapshot['items'][number][] = [];
    for (const rawItem of raw['items']) {
      if (!this.isRecord(rawItem)) return null;
      const time = this.toFiniteNumber(rawItem['time']);
      const category = rawItem['category'];
      const headline = rawItem['headline'];
      const summary = rawItem['summary'];
      const features = this.parseNewsMetrics(rawItem['features']);
      if (
        time === null ||
        !Number.isSafeInteger(time) ||
        typeof category !== 'string' ||
        typeof headline !== 'string' ||
        typeof summary !== 'string' ||
        features === null
      ) {
        return null;
      }
      items.push({ time, category, headline, summary, features });
    }
    const aggregated = this.parseNewsMetrics(raw['aggregated']);
    if (aggregated === null) return null;
    return { items, aggregated };
  }

  private parseAnalysisStatisticsUpdateMessage(
    parsed: Record<string, unknown>,
  ): ServerMessage | null {
    const reject = (reason: string): null => {
      console.warn(
        '[MarketDataSocketService] Rejected statistics update message',
        parsed,
        reason,
      );
      return null;
    };
    const data = parsed['data'];
    if (!this.isRecord(data)) return reject('data must be an object');

    const target = data['target'];
    if (typeof target !== 'string' || target.length === 0) {
      return reject('target must be a non-empty string');
    }

    const statistics = this.parseAnalysisStatistics(data['statistics']);
    if (statistics === null) {
      return reject('statistics must contain only scalar values');
    }

    console.info('[MarketDataSocketService] Accepted statistics update message', parsed);
    return {
      type: 'analysis_update',
      data: { analysis_type: 'statistics', target, statistics },
    };
  }

  private parsePositionEntity(
    raw: unknown,
    valueField: 'value' | 'margin' = 'value',
  ): PositionEntity | null {
    if (!this.isRecord(raw)) return null;
    const type = raw['type'];
    const id = this.toText(raw['id']);
    if (id === null) return null;

    const optionalText = (key: string): string | null => {
      const value = raw[key];
      return value === null || value === undefined ? null : this.toText(value);
    };

    if (type === 'trade') {
      const side = this.toText(raw['side']);
      const value = this.toText(raw[valueField]);
      const leverage = this.toText(raw['leverage']);
      const pnl = this.toText(raw['pnl']);
      const executionPrice = this.toText(raw['execution_price']);
      if (
        side === null ||
        value === null ||
        leverage === null ||
        pnl === null ||
        executionPrice === null
      ) {
        return null;
      }
      return {
        type,
        id,
        side,
        value,
        leverage,
        pnl,
        execution_price: executionPrice,
      };
    }

    if (type === 'order' || type === 'increase_order') {
      const side = optionalText('side');
      const value = this.toText(raw[valueField]);
      const leverage = this.toText(raw['leverage']);
      const entryPrice = this.toText(raw['entry_price']);
      const sourceId = optionalText('source_id');
      if (
        (raw['side'] !== null && raw['side'] !== undefined && side === null) ||
        (raw['source_id'] !== null && raw['source_id'] !== undefined && sourceId === null) ||
        value === null ||
        leverage === null ||
        entryPrice === null ||
        (type === 'order' && side === null)
      ) {
        return null;
      }
      if (type === 'order') {
        if (side === null) return null;
        return { type, id, side, value, leverage, entry_price: entryPrice };
      }
      return { type, id, source_id: sourceId, side, value, leverage, entry_price: entryPrice };
    }

    if (type === 'take_profit' || type === 'stop_loss' || type === 'liquidation_order') {
      const sourceId = optionalText('source_id');
      const side = optionalText('side');
      const closeRate = this.toText(raw['close_rate']);
      const stopPrice = optionalText('stop_price');
      if (
        (raw['source_id'] !== null && raw['source_id'] !== undefined && sourceId === null) ||
        (raw['side'] !== null && raw['side'] !== undefined && side === null) ||
        (raw['stop_price'] !== null && raw['stop_price'] !== undefined && stopPrice === null) ||
        closeRate === null
      ) {
        return null;
      }
      return { type, id, source_id: sourceId, side, close_rate: closeRate, stop_price: stopPrice };
    }

    return null;
  }

  private parsePositionEntities<T extends PositionEntity>(
    raw: unknown,
    isExpected: (entity: PositionEntity) => entity is T,
  ): T[] | null {
    if (!Array.isArray(raw)) return null;
    const entities: T[] = [];
    for (const rawEntity of raw) {
      const entity = this.parsePositionEntity(rawEntity);
      if (entity === null || !isExpected(entity)) return null;
      entities.push(entity);
    }
    return entities;
  }

  private parsePositionInitMessage(parsed: Record<string, unknown>): PositionInitMessage | null {
    const data = parsed['data'];
    if (!this.isRecord(data)) return null;
    const trades = this.parsePositionEntities(
      data['trades'],
      (entity): entity is TradePosition => entity.type === 'trade',
    );
    const orders = this.parsePositionEntities(
      data['orders'],
      (entity): entity is LimitOrderPosition | IncreaseOrderPosition =>
        entity.type === 'order' || entity.type === 'increase_order',
    );
    const stopOrders = this.parsePositionEntities(
      data['stop_orders'],
      (entity): entity is StopOrderPosition =>
        entity.type === 'take_profit' ||
        entity.type === 'stop_loss' ||
        entity.type === 'liquidation_order',
    );
    if (trades === null || orders === null || stopOrders === null) return null;
    return {
      type: 'position_init',
      data: { trades, orders, stop_orders: stopOrders },
    };
  }

  parseMessage(raw: unknown): ServerMessage | null {
    if (typeof raw !== 'string') return null;

    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      return null;
    }
    if (!this.isRecord(parsed)) return null;
    if (parsed['type'] === 'process_end') {
      const data = parsed['data'];
      if (!this.isRecord(data) || Object.keys(data).length !== 0) return null;
      return { type: 'process_end', data: {} } satisfies ProcessEndMessage;
    }
    if (parsed['type'] === 'position_init') return this.parsePositionInitMessage(parsed);
    if (parsed['type'] === 'position_update') {
      const entity = this.parsePositionEntity(parsed['data'], 'margin');
      return entity === null ? null : { type: 'position_update', data: entity };
    }
    if (parsed['type'] === 'position_remove') {
      const data = parsed['data'];
      if (!this.isRecord(data)) return null;
      const id = this.toText(data['id']);
      return id === null ? null : { type: 'position_remove', data: { id } };
    }
    if (parsed['type'] === 'position_clear') {
      const data = parsed['data'];
      return this.isRecord(data) && Object.keys(data).length === 0
        ? { type: 'position_clear', data: {} }
        : null;
    }
    if (parsed['type'] === 'session_start') return this.parseSessionStartMessage(parsed);
    if (parsed['type'] === 'analysis_init') return this.parseAnalysisInitMessage(parsed);
    if (
      parsed['type'] === 'analysis_update' &&
      this.isRecord(parsed['data']) &&
      parsed['data']['analysis_type'] === 'statistics'
    ) {
      return this.parseAnalysisStatisticsUpdateMessage(parsed);
    }
    if (!this.isRecord(parsed['data'])) return null;

    const data = parsed['data'];
    const type = parsed['type'];
    const target = data['target'];
    if (type === 'analysis_update') {
      const time = this.toFiniteNumber(data['time']);
      const equity = this.toFiniteNumber(data['equity']);
      const startingBalance = this.parseNullableFiniteNumber(data['starting_balance']);
      if (
        data['analysis_type'] !== 'equity_curve' ||
        typeof target !== 'string' ||
        target.length === 0 ||
        time === null ||
        !Number.isSafeInteger(time) ||
        equity === null ||
        startingBalance === undefined
      ) {
        return null;
      }
      return {
        type,
        data: { analysis_type: 'equity_curve', target, time, equity, startingBalance },
      };
    }
    if (type === 'analysis_session_start') {
      if (
        data['analysis_type'] !== 'equity_curve' ||
        typeof target !== 'string' ||
        target.length === 0
      ) {
        return null;
      }
      return { type, data: { analysis_type: 'equity_curve', target } };
    }

    const resourceType = data['resource_type'];
    if (
      typeof target !== 'string' ||
      target.length === 0 ||
      (resourceType !== 'timeframe' &&
        resourceType !== 'ohlcv_timeframe' &&
        resourceType !== 'ohlcv_volume_profile' &&
        resourceType !== 'volume_delta' &&
        resourceType !== 'cvd' &&
        resourceType !== 'volume_profile' &&
        resourceType !== 'open_interest' &&
        resourceType !== 'big_trades' &&
        resourceType !== 'news')
    ) {
      return null;
    }

    if (type === 'resource_init') {
      if (resourceType === 'news') {
        const snapshot =
          data['snapshot'] === undefined ? undefined : this.parseNewsSnapshot(data['snapshot']);
        if (data['snapshot'] !== undefined && snapshot === null) {
          this.warnInvalidResourceSnapshot(resourceType, target);
        }
        return {
          type,
          data: { resource_type: resourceType, target, ...(snapshot ? { snapshot } : {}) },
        };
      }
      if (
        (resourceType === 'ohlcv_timeframe' || resourceType === 'ohlcv_volume_profile') &&
        !this.isContextTarget(target)
      ) {
        return null;
      }
      if (resourceType === 'ohlcv_timeframe') {
        const period = this.toText(data['period']);
        if (period === null) return null;
        let snapshot: { interval: string; candles: readonly ContextCandle[] } | undefined;
        if (data['snapshot'] !== undefined) {
          if (this.isRecord(data['snapshot'])) {
            const interval = this.toText(data['snapshot']['interval']);
            const candles = this.parseSnapshotCandles(data['snapshot']['candles']);
            if (interval !== null && candles !== null) snapshot = { interval, candles };
          }
          if (snapshot === undefined) this.warnInvalidResourceSnapshot(resourceType, target);
        }
        return {
          type,
          data: { resource_type: resourceType, target, period, ...(snapshot ? { snapshot } : {}) },
        };
      }
      if (resourceType === 'ohlcv_volume_profile') {
        const priceBinCount = this.toFiniteNumber(data['price_bin_count']);
        if (priceBinCount === null || !Number.isSafeInteger(priceBinCount) || priceBinCount < 1) {
          return null;
        }
        const snapshot =
          data['snapshot'] === undefined
            ? undefined
            : this.parseVolumeProfileSnapshot(data['snapshot']);
        if (data['snapshot'] !== undefined && snapshot === null) {
          this.warnInvalidResourceSnapshot(resourceType, target);
        }
        return {
          type,
          data: {
            resource_type: resourceType,
            target,
            price_bin_count: priceBinCount,
            ...(snapshot ? { snapshot } : {}),
          },
        };
      }
      if (resourceType === 'volume_profile') {
        const priceBinCount = this.toFiniteNumber(data['price_bin_count']);
        const valueAreaPct = this.toFiniteNumber(data['value_area_pct']);
        if (
          priceBinCount === null ||
          !Number.isSafeInteger(priceBinCount) ||
          priceBinCount < 1 ||
          valueAreaPct === null ||
          valueAreaPct <= 0 ||
          valueAreaPct > 100
        ) {
          return null;
        }
        const snapshot =
          data['snapshot'] === undefined
            ? undefined
            : this.parseVolumeProfileSnapshot(data['snapshot']);
        if (data['snapshot'] !== undefined && snapshot === null) {
          this.warnInvalidResourceSnapshot(resourceType, target);
        }
        return {
          type,
          data: {
            resource_type: resourceType,
            target,
            price_bin_count: priceBinCount,
            value_area_pct: valueAreaPct,
            ...(snapshot ? { snapshot } : {}),
          },
        };
      }
      if (resourceType === 'big_trades') {
        const topPct = this.toFiniteNumber(data['top_pct']);
        if (topPct === null || topPct <= 0 || topPct > 100) return null;
        let snapshot: { trades: readonly BigTrade[] } | undefined;
        if (data['snapshot'] !== undefined) {
          const trades = this.isRecord(data['snapshot'])
            ? this.parseSnapshotBigTrades(data['snapshot']['trades'])
            : null;
          if (trades !== null) snapshot = { trades };
          else this.warnInvalidResourceSnapshot(resourceType, target);
        }
        return {
          type,
          data: { resource_type: resourceType, target, top_pct: topPct, ...(snapshot ? { snapshot } : {}) },
        };
      }
      if (resourceType === 'timeframe' || resourceType === 'volume_delta' || resourceType === 'cvd' || resourceType === 'open_interest') {
        const length = this.toFiniteNumber(data['length']);
        if (length === null || !Number.isSafeInteger(length) || length < 1) return null;

        if (resourceType === 'open_interest') {
          let snapshot: { records: readonly SnapshotRecord[] } | undefined;
          if (data['snapshot'] !== undefined) {
            const records = this.isRecord(data['snapshot'])
              ? this.parseSnapshotRecords(data['snapshot']['records'])
              : null;
            if (records !== null) snapshot = { records };
            else this.warnInvalidResourceSnapshot(resourceType, target);
          }
          return {
            type,
            data: {
              resource_type: resourceType,
              target,
              length,
              ...(snapshot ? { snapshot } : {}),
            },
          };
        }
        if (resourceType === 'timeframe') {
          const candleSeconds = this.toFiniteNumber(data['candle_seconds']);
          if (
            candleSeconds === null ||
            !Number.isSafeInteger(candleSeconds) ||
            candleSeconds <= 0
          ) {
            return null;
          }
          let snapshot: { candles: readonly ContextCandle[] } | undefined;
          if (data['snapshot'] !== undefined) {
            const candles = this.isRecord(data['snapshot'])
              ? this.parseSnapshotCandles(data['snapshot']['candles'])
              : null;
            if (candles !== null) snapshot = { candles };
            else this.warnInvalidResourceSnapshot(resourceType, target);
          }
          return {
            type,
            data: {
              resource_type: resourceType,
              target,
              candle_seconds: candleSeconds,
              length,
              ...(snapshot ? { snapshot } : {}),
            },
          };
        }

        const bigTrades = data['big_trades'];
        if (bigTrades !== undefined && typeof bigTrades !== 'boolean') return null;
        const bigTradesPct =
          data['big_trades_pct'] === undefined
            ? null
            : this.toFiniteNumber(data['big_trades_pct']);
        if (data['big_trades_pct'] !== undefined && bigTradesPct === null) return null;
        let snapshot: { records: readonly SnapshotRecord[] } | undefined;
        if (data['snapshot'] !== undefined) {
          const records = this.isRecord(data['snapshot'])
            ? this.parseSnapshotRecords(data['snapshot']['records'])
            : null;
          if (records !== null) snapshot = { records };
          else this.warnInvalidResourceSnapshot(resourceType, target);
        }
        return {
          type,
          data: {
            resource_type: resourceType,
            target,
            length,
            ...(bigTrades === undefined ? {} : { big_trades: bigTrades }),
            ...(bigTradesPct === null ? {} : { big_trades_pct: bigTradesPct }),
            ...(snapshot ? { snapshot } : {}),
          },
        };
      }
    }

    if (type !== 'market_update') return null;
    if (resourceType === 'news') {
      const time = this.toFiniteNumber(data['time']);
      const headline = data['headline'];
      const rawAggregated = data['aggregated'];
      if (
        time === null ||
        !Number.isSafeInteger(time) ||
        !Number.isFinite(new Date(time).getTime()) ||
        typeof headline !== 'string' ||
        headline.trim() === '' ||
        !this.isRecord(rawAggregated)
      ) {
        return null;
      }
      const sentiment = this.toFiniteNumber(rawAggregated['sentiment']);
      const severity = this.toFiniteNumber(rawAggregated['severity']);
      const marketRelevance = this.toFiniteNumber(rawAggregated['market_relevance']);
      const symbolRelevance = this.toFiniteNumber(rawAggregated['symbol_relevance']);
      if (
        sentiment === null ||
        severity === null ||
        marketRelevance === null ||
        symbolRelevance === null
      ) {
        return null;
      }
      return {
        type,
        data: {
          resource_type: resourceType,
          target,
          time,
          headline,
          aggregated: {
            sentiment,
            severity,
            market_relevance: marketRelevance,
            symbol_relevance: symbolRelevance,
          },
        },
      };
    }
    if (resourceType === 'ohlcv_timeframe') {
      if (!this.isContextTarget(target) || !Array.isArray(data['candles'])) return null;
      const interval = this.toText(data['interval']);
      if (interval === null) return null;
      const candles: ContextCandle[] = [];
      for (const rawCandle of data['candles']) {
        if (!this.isRecord(rawCandle)) return null;
        const time = this.toFiniteNumber(rawCandle['time']);
        const open = this.toFiniteNumber(rawCandle['open']);
        const high = this.toFiniteNumber(rawCandle['high']);
        const low = this.toFiniteNumber(rawCandle['low']);
        const close = this.toFiniteNumber(rawCandle['close']);
        if (
          time === null ||
          !Number.isSafeInteger(time) ||
          open === null ||
          high === null ||
          low === null ||
          close === null ||
          low > high
        ) {
          return null;
        }
        candles.push({ time, open, high, low, close });
      }
      return {
        type,
        data: { resource_type: resourceType, target, interval, candles },
      };
    }
    if (resourceType === 'ohlcv_volume_profile') {
      if (!this.isContextTarget(target) || !Array.isArray(data['bins'])) return null;
      const time = this.toFiniteNumber(data['time']);
      if (time === null || !Number.isSafeInteger(time)) return null;
      const bins: VolumeProfileBin[] = [];
      for (const rawBin of data['bins']) {
        if (!this.isRecord(rawBin)) return null;
        const low = this.toFiniteNumber(rawBin['low']);
        const size = this.toFiniteNumber(rawBin['size']);
        const volume = this.toFiniteNumber(rawBin['volume']);
        if (low === null || size === null || size <= 0 || volume === null || volume < 0) return null;
        bins.push({ low, size, volume });
      }
      const rawPoc = data['poc'];
      let poc: { price: number; volume: number } | null = null;
      if (rawPoc !== null) {
        if (!this.isRecord(rawPoc)) return null;
        const price = this.toFiniteNumber(rawPoc['price']);
        const volume = this.toFiniteNumber(rawPoc['volume']);
        if (price === null || volume === null || volume < 0) return null;
        poc = { price, volume };
      }
      const rawValueArea = data['value_area'];
      let valueArea: { low: number; high: number } | null = null;
      if (rawValueArea !== null) {
        if (!this.isRecord(rawValueArea)) return null;
        const low = this.toFiniteNumber(rawValueArea['low']);
        const high = this.toFiniteNumber(rawValueArea['high']);
        if (low === null || high === null || low > high) return null;
        valueArea = { low, high };
      }
      return {
        type,
        data: { resource_type: resourceType, target, time, bins, poc, value_area: valueArea },
      };
    }
    if (resourceType === 'volume_profile') {
      if (!Array.isArray(data['bins'])) return null;
      const bins: VolumeProfileBin[] = [];
      for (const rawBin of data['bins']) {
        if (!this.isRecord(rawBin)) return null;
        const low = this.toFiniteNumber(rawBin['low']);
        const size = this.toFiniteNumber(rawBin['size']);
        const volume = this.toFiniteNumber(rawBin['volume']);
        if (low === null || size === null || size <= 0 || volume === null || volume < 0) return null;
        bins.push({ low, size, volume });
      }
      const rawPoc = data['poc'];
      let poc: { price: number; volume: number } | null = null;
      if (rawPoc !== null && rawPoc !== undefined) {
        if (!this.isRecord(rawPoc)) return null;
        const price = this.toFiniteNumber(rawPoc['price']);
        const volume = this.toFiniteNumber(rawPoc['volume']);
        if (price === null || volume === null || volume < 0) return null;
        poc = { price, volume };
      }
      const rawValueArea = data['value_area'];
      let valueArea: { low: number; high: number } | null = null;
      if (rawValueArea !== null && rawValueArea !== undefined) {
        if (!this.isRecord(rawValueArea)) return null;
        const low = this.toFiniteNumber(rawValueArea['low']);
        const high = this.toFiniteNumber(rawValueArea['high']);
        if (low === null || high === null || low > high) return null;
        valueArea = { low, high };
      }
      return {
        type,
        data: {
          resource_type: resourceType,
          target,
          bins,
          poc,
          value_area: valueArea,
        },
      };
    }
    if (resourceType === 'big_trades') {
      if (!Array.isArray(data['trades'])) return null;
      const trades: BigTrade[] = [];
      for (const rawTrade of data['trades']) {
        if (!this.isRecord(rawTrade)) return null;
        const time = this.toFiniteNumber(rawTrade['time']);
        const price = this.toFiniteNumber(rawTrade['price']);
        const quantity = this.toFiniteNumber(rawTrade['quantity']);
        const side = rawTrade['side'];
        if (
          time === null ||
          !Number.isSafeInteger(time) ||
          price === null ||
          quantity === null ||
          quantity < 0 ||
          (side !== 1 && side !== -1)
        ) {
          return null;
        }
        trades.push({ time, price, quantity, side });
      }
      return { type, data: { resource_type: resourceType, target, trades } };
    }
    const time = this.toFiniteNumber(data['time']);
    if (time === null || !Number.isSafeInteger(time)) return null;

    if (resourceType === 'timeframe') {
      const open = this.toFiniteNumber(data['open']);
      const high = this.toFiniteNumber(data['high']);
      const low = this.toFiniteNumber(data['low']);
      const close = this.toFiniteNumber(data['close']);
      if (open === null || high === null || low === null || close === null) return null;
      return {
        type,
        data: { resource_type: resourceType, target, time, open, high, low, close },
      };
    }

    const value = this.toFiniteNumber(data['value']);
    if (value === null) return null;
    return { type, data: { resource_type: resourceType, target, time, value } };
  }

  private parseSessionStartMessage(
    parsed: Record<string, unknown>,
  ): ServerMessage | null {
    const data = parsed['data'];
    if (!this.isRecord(data)) return null;

    const strategyName = data['strategy_name'];
    const sessionNumber = this.toText(data['session_number']);
    const symbol = data['symbol'];
    const progress = data['progress'];
    if (
      typeof strategyName !== 'string' ||
      strategyName.trim() === '' ||
      sessionNumber === null ||
      (symbol !== null && typeof symbol !== 'string') ||
      typeof progress !== 'string' ||
      progress.trim() === ''
    ) {
      return null;
    }

    return {
      type: 'session_start',
      data: { strategy_name: strategyName, session_number: sessionNumber, symbol, progress },
    };
  }

  private parseAnalysisStatistics(raw: unknown): readonly AnalysisStatistic[] | null {
    if (!this.isRecord(raw)) return null;
    const statistics: AnalysisStatistic[] = [];
    for (const [key, value] of Object.entries(raw)) {
      if (key.trim() === '' || !this.isAnalysisStatisticValue(value)) return null;
      statistics.push({ key, value });
    }
    return statistics;
  }

  private isAnalysisStatisticValue(value: unknown): value is AnalysisStatisticValue {
    return (
      value === null ||
      typeof value === 'string' ||
      typeof value === 'boolean' ||
      (typeof value === 'number' && Number.isFinite(value))
    );
  }

  private clearMarketUpdateData(): void {
    this.clearDisplayUpdateTimer();
    for (const target of this.seriesByTarget.keys()) {
      this.seriesByTarget.set(target, EMPTY_SERIES);
    }
    this.series.set(EMPTY_SERIES);
    this.lastDisplayUpdateAt = Number.NEGATIVE_INFINITY;

    this.dynamicResources.update((resources) =>
      resources.map((resource) => {
        if (resource.resource_type === 'volume_profile') {
          return { ...resource, time: null, bins: [], poc: null, value_area: null };
        }
        if (resource.resource_type === 'open_interest') {
          return { ...resource, points: [] };
        }
        return { ...resource, trades: [] };
      }),
    );

    for (const [target, profile] of this.contextProfilesByTarget) {
      this.contextProfilesByTarget.set(target, {
        ...profile,
        time: null,
        bins: [],
        poc: null,
        value_area: null,
      });
    }
    this.contextCharts.update((charts) =>
      charts.map((chart) => ({
        ...chart,
        interval: null,
        candles: [],
        volumeProfile: this.contextProfilesByTarget.get(chart.target) ?? null,
      })),
    );

    const news = this.newsPanel();
    if (news) {
      this.newsPanel.set({
        ...news,
        latestUpdateTime: null,
        aggregated: null,
        headlines: [],
      });
    }
  }

  private registerResource(message: ResourceInitMessage): void {
    const config = message.data;
    const { resource_type: resourceType, target } = config;
    if (config.resource_type === 'news') {
      this.newsPanel.set({
        target,
        latestUpdateTime: null,
        aggregated: null,
        headlines: [],
      });
    } else if (config.resource_type === 'ohlcv_timeframe') {
      const previous = this.contextChart(target);
      this.setContextChart({
        target,
        id: target.slice('context_chart/'.length),
        period: config.period,
        interval: previous?.interval ?? null,
        candles: previous?.candles ?? [],
        volumeProfile: this.contextProfilesByTarget.get(target) ?? null,
      });
    } else if (config.resource_type === 'ohlcv_volume_profile') {
      const profile: ContextVolumeProfileState = {
        ...config,
        time: null,
        bins: [],
        poc: null,
        value_area: null,
      };
      this.contextProfilesByTarget.set(target, profile);
      const chart = this.contextChart(target);
      if (chart) this.setContextChart({ ...chart, volumeProfile: profile });
    } else if ('length' in config) {
      let resources = this.resourceLengthsByTarget.get(target);
      if (!resources) {
        resources = new Map<ResourceType, number>();
        this.resourceLengthsByTarget.set(target, resources);
      }
      resources.set(resourceType, config.length);
    }

    if (resourceType === 'timeframe') {
      const timeframe = config.candle_seconds;
      this.timeframeByTarget.set(target, timeframe);
      if (!this.seriesByTarget.has(target)) this.seriesByTarget.set(target, EMPTY_SERIES);
      const timeframes = [...new Set(this.timeframeByTarget.values())].sort((a, b) => a - b);
      this.timeframes.set(timeframes);
      if (
        !this.hasUserSelectedTimeframe ||
        !timeframes.includes(this.selectedTimeframe() ?? 0)
      ) {
        this.selectedTimeframe.set(timeframes[0] ?? null);
      }
      this.refreshSelectedSeries();
      this.refreshSelectedIndicatorTitles();
    } else if (resourceType === 'volume_delta' || resourceType === 'cvd') {
      const titles = this.indicatorTitlesByTarget.get(target) ?? {
        volume_delta: 'Volume Delta',
        cvd: 'CVD',
      };
      titles[resourceType] = this.indicatorTitle(config);
      this.indicatorTitlesByTarget.set(target, titles);
      if (
        !this.initializedIndicators().some(
          (resource) => resource.target === target && resource.resource_type === resourceType,
        )
      ) {
        this.initializedIndicators.update((resources) => [
          ...resources,
          { target, resource_type: resourceType },
        ]);
      }
      if (this.selectedTarget() === target) {
        this.indicatorTitles.set({ ...titles });
      }
    } else if (resourceType === 'volume_profile') {
      this.setDynamicResource({
        ...config,
        time: null,
        bins: [],
        poc: null,
        value_area: null,
      });
    } else if (resourceType === 'open_interest') {
      this.setDynamicResource({ ...config, points: [] });
    } else if (config.resource_type === 'big_trades') {
      this.setDynamicResource({ ...config, trades: [] });
    }

    this.applyResourceSnapshot(config);
  }

  private applyResourceSnapshot(config: ResourceInitMessage['data']): void {
    if (config.resource_type === 'timeframe' && config.snapshot) {
      const current = this.seriesByTarget.get(config.target) ?? EMPTY_SERIES;
      const candles = config.snapshot.candles.map((candle) => ({
        timestamp: candle.time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
        volume: 0,
      }));
      this.seriesByTarget.set(config.target, {
        ...current,
        candles: this.trimToLength(candles, config.length),
      });
      if (this.timeframeByTarget.get(config.target) === this.selectedTimeframe()) {
        this.refreshSelectedSeries();
      }
      return;
    }

    if (
      (config.resource_type === 'volume_delta' || config.resource_type === 'cvd') &&
      config.snapshot
    ) {
      const current = this.seriesByTarget.get(config.target) ?? EMPTY_SERIES;
      const points = config.snapshot.records.map((record) => ({
        timestamp: record.time,
        value: record.value,
      }));
      const maximumLength = this.resourceLengthsByTarget.get(config.target)?.get(config.resource_type);
      this.seriesByTarget.set(config.target, {
        ...current,
        [config.resource_type === 'volume_delta' ? 'volumeDelta' : 'cvd']:
          this.trimToLength(points, maximumLength ?? Number.POSITIVE_INFINITY),
      });
      if (this.timeframeByTarget.get(config.target) === this.selectedTimeframe()) {
        this.refreshSelectedSeries();
      }
      return;
    }

    if (config.resource_type === 'volume_profile' && config.snapshot) {
      this.setDynamicResource({
        ...config,
        time: config.snapshot.time,
        bins: config.snapshot.bins,
        poc: config.snapshot.poc,
        value_area: config.snapshot.value_area,
      });
      return;
    }

    if (config.resource_type === 'open_interest' && config.snapshot) {
      const points = config.snapshot.records.map((record) => ({
        timestamp: record.time,
        value: record.value,
      }));
      this.setDynamicResource({
        ...config,
        points: this.trimToLength(points, config.length),
      });
      return;
    }

    if (config.resource_type === 'big_trades' && config.snapshot) {
      this.setDynamicResource({ ...config, trades: config.snapshot.trades });
      return;
    }

    if (config.resource_type === 'ohlcv_timeframe' && config.snapshot) {
      const chart = this.contextChart(config.target);
      if (!chart) return;
      this.setContextChart({
        ...chart,
        interval: config.snapshot.interval,
        candles: config.snapshot.candles,
      });
      return;
    }

    if (config.resource_type === 'ohlcv_volume_profile' && config.snapshot) {
      const profile = this.contextProfilesByTarget.get(config.target);
      if (!profile) return;
      const updatedProfile: ContextVolumeProfileState = {
        ...profile,
        time: config.snapshot.time,
        bins: config.snapshot.bins,
        poc: config.snapshot.poc,
        value_area: config.snapshot.value_area,
      };
      this.contextProfilesByTarget.set(config.target, updatedProfile);
      const chart = this.contextChart(config.target);
      if (chart) this.setContextChart({ ...chart, volumeProfile: updatedProfile });
      return;
    }

    if (config.resource_type === 'news' && config.snapshot) {
      const items = [...config.snapshot.items].sort((first, second) => second.time - first.time);
      this.newsPanel.set({
        target: config.target,
        latestUpdateTime: items[0]?.time ?? null,
        aggregated: config.snapshot.aggregated,
        headlines: items.slice(0, 3).map((item) => ({
          time: item.time,
          headline: item.headline,
          category: item.category,
          summary: item.summary,
          features: item.features,
        })),
      });
    }
  }

  private trimToLength<T>(values: readonly T[], maximumLength: number): readonly T[] {
    return values.length > maximumLength ? values.slice(-maximumLength) : values;
  }

  private applyMarketUpdate(
    update: Extract<ServerMessage, { type: 'market_update' }>['data'],
  ): void {
    if (update.resource_type === 'news') {
      const current = this.newsPanel();
      if (!current || current.target !== update.target) return;
      const latestUpdateTime = current.latestUpdateTime;
      const isLatest = latestUpdateTime === null || update.time >= latestUpdateTime;
      const headlines = [
        ...current.headlines.filter((item) => item.time !== update.time),
        { time: update.time, headline: update.headline },
      ]
        .sort((first, second) => second.time - first.time)
        .slice(0, 3);
      this.newsPanel.set({
        ...current,
        latestUpdateTime: isLatest ? update.time : latestUpdateTime,
        aggregated: isLatest ? update.aggregated : current.aggregated,
        headlines,
      });
      return;
    }
    if (update.resource_type === 'ohlcv_timeframe') {
      const chart = this.contextChart(update.target);
      if (!chart) return;
      this.setContextChart({
        ...chart,
        interval: update.interval,
        candles: update.candles,
      });
      return;
    }
    if (update.resource_type === 'ohlcv_volume_profile') {
      const profile = this.contextProfilesByTarget.get(update.target);
      if (!profile) return;
      const updatedProfile: ContextVolumeProfileState = {
        ...profile,
        time: update.time,
        bins: update.bins,
        poc: update.poc,
        value_area: update.value_area,
      };
      this.contextProfilesByTarget.set(update.target, updatedProfile);
      const chart = this.contextChart(update.target);
      if (chart) this.setContextChart({ ...chart, volumeProfile: updatedProfile });
      return;
    }
    const resources = this.resourceLengthsByTarget.get(update.target);
    if (update.resource_type === 'volume_profile') {
      const resource = this.findDynamicResource(update.target, update.resource_type);
      if (!resource) return;
      this.setDynamicResource({
        ...resource,
        bins: update.bins,
        poc: update.poc,
        value_area: update.value_area,
      });
      return;
    }
    if (update.resource_type === 'big_trades') {
      const resource = this.findDynamicResource(update.target, update.resource_type);
      if (!resource) return;
      this.setDynamicResource({ ...resource, trades: update.trades });
      return;
    }
    if (!resources?.has(update.resource_type)) return;
    const current = this.seriesByTarget.get(update.target) ?? EMPTY_SERIES;
    const maximumLength = resources.get(update.resource_type)!;
    if (update.resource_type === 'open_interest') {
      const resource = this.findDynamicResource(update.target, update.resource_type);
      if (!resource) return;
      this.setDynamicResource({
        ...resource,
        points: this.upsertByTimestamp(resource.points, {
          timestamp: update.time,
          value: update.value,
        }, maximumLength),
      });
      return;
    }
    let next: MarketSeries;

    if (update.resource_type === 'timeframe') {
      const candle: Candle = {
        timestamp: update.time,
        open: update.open,
        high: update.high,
        low: update.low,
        close: update.close,
        volume: 0,
      };
      next = {
        ...current,
        candles: this.upsertByTimestamp(current.candles, candle, maximumLength),
      };
    } else {
      const point: TimeSeriesPoint = { timestamp: update.time, value: update.value };
      if (update.resource_type === 'volume_delta') {
        next = {
          ...current,
          volumeDelta: this.upsertByTimestamp(current.volumeDelta, point, maximumLength),
        };
      } else {
        next = { ...current, cvd: this.upsertByTimestamp(current.cvd, point, maximumLength) };
      }
    }

    this.seriesByTarget.set(update.target, next);
    if (this.timeframeByTarget.get(update.target) === this.selectedTimeframe()) {
      if (update.resource_type === 'timeframe') {
        const sequence = this.selectedCandleUpdateSequence() + 1;
        this.selectedCandleUpdateSequence.set(sequence);
        this.selectedCandleUpdateSubject.next(sequence);
      }
      this.scheduleSelectedSeriesUpdate();
    }
  }

  private upsertByTimestamp<T extends { timestamp: number }>(
    values: readonly T[],
    update: T,
    maximumLength = Number.POSITIVE_INFINITY,
  ): readonly T[] {
    const index = values.findIndex((value) => value.timestamp >= update.timestamp);
    let updated: T[];
    if (index !== -1 && values[index].timestamp === update.timestamp) {
      updated = [...values.slice(0, index), update, ...values.slice(index + 1)];
    } else if (index === -1) {
      updated = [...values, update];
    } else {
      updated = [...values.slice(0, index), update, ...values.slice(index)];
    }
    return updated.length > maximumLength ? updated.slice(-maximumLength) : updated;
  }

  private refreshSelectedSeries(): void {
    this.activeTarget.set(this.selectedTarget() ?? null);
    this.scheduleSelectedSeriesUpdate();
  }

  private scheduleSelectedSeriesUpdate(): void {
    const elapsed = performance.now() - this.lastDisplayUpdateAt;
    const remaining = DISPLAY_INTERVAL_MS - elapsed;
    if (remaining <= 0) {
      this.clearDisplayUpdateTimer();
      this.publishSelectedSeries();
      return;
    }
    if (this.displayUpdateTimer !== null) return;

    this.displayUpdateTimer = setTimeout(() => {
      this.displayUpdateTimer = null;
      this.publishSelectedSeries();
    }, remaining);
  }

  private publishSelectedSeries(): void {
    const target = this.selectedTarget();
    const selectedSeries = target ? (this.seriesByTarget.get(target) ?? EMPTY_SERIES) : EMPTY_SERIES;
    if (selectedSeries === this.series()) return;
    this.series.set(selectedSeries);
    this.lastDisplayUpdateAt = performance.now();
  }

  private refreshSelectedIndicatorTitles(): void {
    const target = this.selectedTarget();
    const titles = target ? this.indicatorTitlesByTarget.get(target) : undefined;
    this.indicatorTitles.set({
      volume_delta: titles?.volume_delta ?? 'Volume Delta',
      cvd: titles?.cvd ?? 'CVD',
    });
  }

  private selectedTarget(): string | undefined {
    const selectedTimeframe = this.selectedTimeframe();
    return [...this.timeframeByTarget].find(
      ([, timeframe]) => timeframe === selectedTimeframe,
    )?.[0];
  }

  private setDynamicResource(resource: DynamicResourceState): void {
    const resources = this.dynamicResources();
    const index = resources.findIndex(
      (item) => item.resource_type === resource.resource_type && item.target === resource.target,
    );
    if (index === -1) {
      this.dynamicResources.set([...resources, resource]);
      return;
    }
    this.dynamicResources.set([
      ...resources.slice(0, index),
      resource,
      ...resources.slice(index + 1),
    ]);
  }

  private contextChart(target: string): ContextChartState | undefined {
    return this.contextCharts().find((chart) => chart.target === target);
  }

  private setAnalysisEquityCurve(curve: AnalysisEquityCurveState): void {
    const curves = this.analysisEquityCurves();
    const index = curves.findIndex((item) => item.target === curve.target);
    this.analysisEquityCurves.set(
      index === -1
        ? [...curves, curve]
        : [...curves.slice(0, index), curve, ...curves.slice(index + 1)],
    );
  }

  private setAnalysisStatistics(statistics: AnalysisStatisticsState): void {
    const allStatistics = this.analysisStatistics();
    const index = allStatistics.findIndex((item) => item.target === statistics.target);
    this.analysisStatistics.set(
      index === -1
        ? [...allStatistics, statistics]
        : [
            ...allStatistics.slice(0, index),
            statistics,
            ...allStatistics.slice(index + 1),
          ],
    );
  }

  private setContextChart(chart: ContextChartState): void {
    const charts = this.contextCharts();
    const index = charts.findIndex((item) => item.target === chart.target);
    this.contextCharts.set(
      index === -1
        ? [...charts, chart]
        : [...charts.slice(0, index), chart, ...charts.slice(index + 1)],
    );
  }

  private findDynamicResource(
    target: string,
    resourceType: 'volume_profile',
  ): VolumeProfileResourceState | undefined;
  private findDynamicResource(
    target: string,
    resourceType: 'open_interest',
  ): OpenInterestResourceState | undefined;
  private findDynamicResource(
    target: string,
    resourceType: 'big_trades',
  ): Extract<DynamicResourceState, { resource_type: 'big_trades' }> | undefined;
  private findDynamicResource(
    target: string,
    resourceType: 'volume_profile' | 'open_interest' | 'big_trades',
  ): DynamicResourceState | undefined {
    return this.dynamicResources().find(
      (resource) => resource.resource_type === resourceType && resource.target === target,
    );
  }

  private resetConnectionResources(): void {
    this.resourceLengthsByTarget.clear();
    this.resourceInitCache.clear();
    this.timeframeByTarget.clear();
    this.indicatorTitlesByTarget.clear();
    this.dynamicResources.set([]);
    this.contextCharts.set([]);
    this.newsPanel.set(null);
    this.analysisEquityCurves.set([]);
    this.analysisStatistics.set([]);
    this.positionEntities.set([]);
    this.sessionStart.set(null);
    this.contextProfilesByTarget.clear();
    this.initializedIndicators.set([]);
    this.timeframes.set([]);
    this.activeTarget.set(null);
    this.indicatorTitles.set({ volume_delta: 'Volume Delta', cvd: 'CVD' });
    this.hasReceivedLiveMessage = false;
  }

  private indicatorTitle(
    config: Extract<ResourceInitMessage['data'], { resource_type: 'volume_delta' | 'cvd' }>,
  ): string {
    const title = config.resource_type === 'volume_delta' ? 'Volume Delta' : 'CVD';
    if (!config.big_trades) return title;
    return config.big_trades_pct === undefined
      ? `${title} (Big Trades)`
      : `${title} (Big Trades ${config.big_trades_pct}%)`;
  }

  private toFiniteNumber(value: unknown): number | null {
    if (typeof value !== 'number' && typeof value !== 'string') return null;
    if (typeof value === 'string' && value.trim() === '') return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  private parseNullableFiniteNumber(value: unknown): number | null | undefined {
    if (value === null) return null;
    return this.toFiniteNumber(value) ?? undefined;
  }

  private toText(value: unknown): string | null {
    if (typeof value === 'string' && value.trim() !== '') return value;
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
    return null;
  }

  private isContextTarget(target: string): boolean {
    return target.startsWith('context_chart/') && target.length > 'context_chart/'.length;
  }

  private isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }

  private connect(): void {
    if (!this.started || this.socket) return;
    this.resetConnectionResources();
    this.status.set('connecting');
    this.error.set(null);

    let socket: WebSocket;
    try {
      socket = new WebSocket(environment.marketDataWsUrl);
    } catch {
      this.status.set('error');
      this.error.set('Invalid market-data WebSocket URL.');
      this.scheduleReconnect();
      return;
    }

    this.socket = socket;
    socket.onopen = () => {
      if (this.socket !== socket) return;
      this.reconnectAttempts = 0;
      this.status.set('connected');
      this.error.set(null);
    };
    socket.onmessage = (event: MessageEvent) => {
      if (this.socket !== socket) return;
      const message = this.parseMessage(event.data);
      if (message) {
        this.error.set(null);
        this.handleMessage(message);
      } else {
        this.error.set('Received an invalid market-data message.');
      }
    };
    socket.onerror = () => {
      if (this.socket !== socket) return;
      this.status.set('error');
      this.error.set('Market-data backend unavailable.');
      this.retireSocket(socket);
      this.scheduleReconnect();
    };
    socket.onclose = () => {
      if (this.socket !== socket) return;
      this.socket = null;
      if (this.status() !== 'error') this.status.set('closed');
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    if (!this.started || this.reconnectTimer !== null) return;
    const delay = Math.min(
      RECONNECT_BASE_DELAY_MS * 2 ** this.reconnectAttempts,
      RECONNECT_MAX_DELAY_MS,
    );
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private retireSocket(socket: WebSocket): void {
    if (this.socket !== socket) return;
    this.socket = null;
    socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null;
    socket.close();
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer === null) return;
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
  }

  private clearDisplayUpdateTimer(): void {
    if (this.displayUpdateTimer === null) return;
    clearTimeout(this.displayUpdateTimer);
    this.displayUpdateTimer = null;
  }

  private disconnect(): void {
    const socket = this.socket;
    this.socket = null;
    if (!socket) return;
    socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null;
    socket.close();
  }
}
