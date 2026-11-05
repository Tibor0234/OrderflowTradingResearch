import { Component, computed, DestroyRef, effect, inject, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { ContextChartComponent } from './features/context/context-chart.component';
import { EquityCurveComponent } from './features/performance/equity-curve/equity-curve.component';
import { MainPriceChartComponent } from './features/charts/main-price-chart/main-price-chart.component';
import { MarketDataSocketService } from './core/services/market-data-socket.service';
import { ReplayControlService } from './core/services/replay-control.service';
import { environment } from '../environments/environment';
import {
  formatTimeframe as formatTimeframeLabel,
  Timeframe,
} from './shared/models/market-data.models';
import { OscillatorPanelComponent } from './features/charts/oscillator-panel/oscillator-panel.component';
import {
  AnalysisStatisticValue,
  LimitOrderPosition,
  PositionChild,
  TimeSeriesPoint,
  TradePosition,
} from './shared/models/market-data.models';

type OscillatorKind = 'volumeDelta' | 'cvd' | 'openInterest';

interface OscillatorPanelItem {
  title: string;
  kind: OscillatorKind;
  expanded: boolean;
  series: readonly TimeSeriesPoint[];
}

interface PositionGroup {
  trade: TradePosition;
  children: PositionChild[];
}

interface OrderGroup {
  order: LimitOrderPosition;
  children: PositionChild[];
}

const POSITION_CHILD_ORDER: Readonly<Record<PositionChild['type'], number>> = {
  increase_order: 0,
  take_profit: 1,
  stop_loss: 2,
  liquidation_order: 3,
};

const STATISTIC_LABELS: Readonly<Record<string, string>> = {
  total_trades: 'Total Trades',
  winrate: 'Win Rate',
  pnl: 'PnL',
  roi: 'ROI',
  max_drawdown: 'Max Drawdown',
  average_trade_duration: 'Average Trade Duration',
};

type AutoStopEvent = 'tradeOpen' | 'orderPlaced';

const QUOTE_ASSETS = [
  'USDT',
  'USDC',
  'FDUSD',
  'BUSD',
  'TUSD',
  'USD',
  'EUR',
  'GBP',
  'BTC',
  'ETH',
  'BNB',
  'SOL',
];

function getSymbolLogoUrl(symbol: string): string | null {
  const normalizedSymbol = symbol
    .trim()
    .toUpperCase()
    .replace(/[\s/_-]/g, '')
    .replace(/(PERP|SWAP)$/, '');
  if (!normalizedSymbol || normalizedSymbol === 'NONE' || normalizedSymbol === '—') {
    return null;
  }

  const quoteAsset = QUOTE_ASSETS.find(
    (quote) => normalizedSymbol.length > quote.length && normalizedSymbol.endsWith(quote),
  );
  const baseAsset = quoteAsset
    ? normalizedSymbol.slice(0, -quoteAsset.length)
    : normalizedSymbol;
  if (!/^[A-Z0-9]+$/.test(baseAsset)) return null;

  return `https://assets.coincap.io/assets/icons/${baseAsset.toLowerCase()}@2x.png`;
}

@Component({
  imports: [
    ContextChartComponent,
    EquityCurveComponent,
    MainPriceChartComponent,
    OscillatorPanelComponent,
  ],
  selector: 'app-root',
  templateUrl: './app.html',
  host: {
    '(document:click)': 'handleDocumentClick($event)',
    '(document:keydown.escape)': 'closeOverlays()',
  },
})
export class App {
  private readonly marketSocket = inject(MarketDataSocketService);
  private readonly replayControl = inject(ReplayControlService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly replayPlaying = signal(false);
  protected readonly replayRequestPending = signal(false);
  protected readonly replayRequestError = signal<string | null>(null);
  protected readonly autoStopSettingsExpanded = signal(false);
  protected readonly autoStopEvents = signal({ tradeOpen: false, orderPlaced: false });
  protected readonly menuExpanded = signal(false);
  protected readonly reportExportPending = signal(false);
  protected readonly reportExportError = signal<string | null>(null);
  protected readonly timeframes = this.marketSocket.timeframes;
  protected readonly connectionStatus = this.marketSocket.status;
  protected readonly connectionError = this.marketSocket.error;
  protected readonly sessionStart = this.marketSocket.sessionStart;
  protected readonly processEnded = this.marketSocket.processEnded;
  protected readonly strategyName = computed(
    () => this.sessionStart()?.strategy_name || '—',
  );
  protected readonly sessionNumber = computed(() => {
    const number = this.sessionStart()?.session_number ?? '—';
    return /^\d$/.test(number) ? `0${number}` : number;
  });
  protected readonly sessionSymbol = computed(() => {
    const session = this.sessionStart();
    return session ? session.symbol ?? 'None' : '—';
  });
  protected readonly symbolLogoUrl = computed(() =>
    getSymbolLogoUrl(this.sessionSymbol()),
  );
  protected readonly failedSymbolLogoUrl = signal<string | null>(null);
  protected readonly sessionProgress = computed(
    () => this.sessionStart()?.progress || '—',
  );
  protected readonly exportStatisticsDisabled = computed(() => {
    const progress = this.sessionStart()?.progress.trim().match(/^(\d+)(?:\s*\/\s*\d+)?$/);
    return progress === undefined || progress === null || Number(progress[1]) < 2;
  });
  protected readonly leftCollapsed = signal(false);
  protected readonly rightCollapsed = signal(false);
  protected readonly analysisEquityCurves = this.marketSocket.analysisEquityCurves;
  protected readonly analysisStatistics = this.marketSocket.analysisStatistics;
  protected readonly selectedAnalysisName = signal<string | null>(null);
  protected readonly analysisNames = computed(() => {
    const names = new Set<string>();
    this.analysisEquityCurves().forEach((curve) => names.add(curve.name));
    this.analysisStatistics().forEach((statistics) => names.add(statistics.name));
    return [...names];
  });
  protected readonly effectiveAnalysisName = computed(() => {
    const names = this.analysisNames();
    const selectedName = this.selectedAnalysisName();
    return selectedName !== null && names.includes(selectedName) ? selectedName : names[0] ?? null;
  });
  protected readonly selectedAnalysisCurve = computed(() => {
    const name = this.effectiveAnalysisName();
    return name === null
      ? null
      : this.analysisEquityCurves().find((curve) => curve.name === name) ?? null;
  });
  protected readonly selectedStatistics = computed(() => {
    const name = this.effectiveAnalysisName();
    return name === null
      ? []
      : this.analysisStatistics().find((statistics) => statistics.name === name)?.statistics ?? [];
  });
  protected readonly displayedPositionEntities = this.marketSocket.positionEntities;
  protected readonly hoveredPositionId = signal<string | null>(null);
  private previousPositionKeys = new Set<string>();
  private hasObservedPositions = false;
  private pendingReplayAction: 'start' | 'stop' | null = null;
  private stopAfterReplayStarts = false;
  private stopOnNextCandleUpdate = false;
  private candleUpdateSequenceAtStart = 0;
  private readonly positionChildrenByParent = computed(() => {
    const entities = this.displayedPositionEntities();
    const tradeIds = new Set(
      entities.filter((entity): entity is TradePosition => entity.type === 'trade').map((trade) => trade.id),
    );
    const orderIds = new Set(
      entities.filter((entity): entity is LimitOrderPosition => entity.type === 'order').map((order) => order.id),
    );
    const childrenByTrade = new Map<string, PositionChild[]>();
    const childrenByOrder = new Map<string, PositionChild[]>();

    for (const entity of entities) {
      if (entity.type === 'trade' || entity.type === 'order' || entity.source_id === null) continue;
      const parentChildren = tradeIds.has(entity.source_id)
        ? childrenByTrade
        : orderIds.has(entity.source_id)
          ? childrenByOrder
          : null;
      if (parentChildren === null) continue;
      const children = parentChildren.get(entity.source_id) ?? [];
      children.push(entity);
      parentChildren.set(entity.source_id, children);
    }

    for (const groups of [childrenByTrade, childrenByOrder]) {
      groups.forEach((children) =>
        children.sort(
          (left, right) => POSITION_CHILD_ORDER[left.type] - POSITION_CHILD_ORDER[right.type],
        ),
      );
    }

    return { byTrade: childrenByTrade, byOrder: childrenByOrder };
  });
  protected readonly positionGroups = computed(() => {
    const entities = this.displayedPositionEntities();
    const childrenByParent = this.positionChildrenByParent();
    const trades = entities.filter(
      (entity): entity is TradePosition => entity.type === 'trade',
    );
    return trades.map((trade) => ({
      trade,
      children: childrenByParent.byTrade.get(trade.id) ?? [],
    }));
  });
  protected readonly openOrders = computed(() => {
    const entities = this.displayedPositionEntities();
    const childrenByParent = this.positionChildrenByParent();
    return entities.filter(
      (entity): entity is LimitOrderPosition => entity.type === 'order',
    ).map((order) => ({
      order,
      children: childrenByParent.byOrder.get(order.id) ?? [],
    }));
  });
  protected readonly positionItemCount = computed(
    () => this.positionGroups().length + this.openOrders().length,
  );
  protected readonly selectedTimeframe = this.marketSocket.selectedTimeframe;
  protected readonly canRunUntilNextCandle = computed(
    () =>
      !this.replayPlaying() &&
      !this.replayRequestPending() &&
      !this.processEnded() &&
      this.selectedTimeframe() !== null,
  );
  protected readonly chartTimeframe = computed(() => this.selectedTimeframe() ?? 60);
  protected readonly chartData = this.marketSocket.series;
  protected readonly contextCharts = this.marketSocket.contextCharts;
  protected readonly newsPanel = this.marketSocket.newsPanel;
  protected readonly analysisViewSelection = computed(() => {
    return this.effectiveAnalysisName() ?? '';
  });
  protected readonly contextChartExpanded = signal<Record<string, boolean>>({});
  protected readonly indicatorTitles = this.marketSocket.indicatorTitles;
  protected readonly connectionLabel = computed(() => {
    const hasData = this.chartData().candles.length > 0;
    switch (this.connectionStatus()) {
      case 'connected':
        return hasData ? 'LIVE' : 'CONNECTED · WAITING FOR DATA';
      case 'connecting':
        return 'CONNECTING…';
      case 'error':
        return this.connectionError() ?? 'BACKEND UNAVAILABLE';
      case 'closed':
        return 'DISCONNECTED';
      default:
        return 'IDLE';
    }
  });
  protected readonly panelExpanded = signal<Record<string, boolean>>({
    dailyContext: true,
    weeklyContext: true,
    news: true,
    performance: true,
    positions: true,
  });
  private readonly oscillatorExpanded = signal({
    volumeDelta: true,
    cvd: true,
    openInterest: true,
  });
  protected readonly activeResources = computed(() => {
    const target = this.marketSocket.activeTarget();
    return target === null
      ? []
      : this.marketSocket.dynamicResources().filter((resource) => resource.target === target);
  });
  protected readonly volumeProfile = computed(() =>
    this.activeResources().find((resource) => resource.resource_type === 'volume_profile') ?? null,
  );
  protected readonly bigTradesResource = computed(
    () =>
      this.activeResources().find((resource) => resource.resource_type === 'big_trades') ?? null,
  );
  protected readonly bigTrades = computed(
    () => this.bigTradesResource()?.trades ?? [],
  );
  protected readonly oscillators = computed(() => {
    const titles = this.indicatorTitles();
    const expanded = this.oscillatorExpanded();
    const chartData = this.chartData();
    const target = this.marketSocket.activeTarget();
    const initialized = this.marketSocket.initializedIndicators().filter(
      (resource) => resource.target === target,
    );
    const panels: OscillatorPanelItem[] = [];
    if (initialized.some((resource) => resource.resource_type === 'volume_delta')) {
      panels.push({
        title: titles.volume_delta,
        kind: 'volumeDelta',
        expanded: expanded.volumeDelta,
        series: chartData.volumeDelta,
      });
    }
    if (initialized.some((resource) => resource.resource_type === 'cvd')) {
      panels.push({
        title: titles.cvd,
        kind: 'cvd',
        expanded: expanded.cvd,
        series: chartData.cvd,
      });
    }
    const openInterest = this.activeResources().find(
      (resource) => resource.resource_type === 'open_interest',
    );
    if (openInterest?.resource_type === 'open_interest') {
      panels.push({
        title: 'Open Interest',
        kind: 'openInterest',
        expanded: expanded.openInterest,
        series: openInterest.points,
      });
    }
    return panels;
  });
  protected readonly panelHeights = signal({ main: 60, volumeDelta: 22, cvd: 18, openInterest: 18 });
  protected readonly resizingSplit = signal<number | null>(null);
  private resizingPointerId: number | null = null;
  protected readonly mainPanelStyle = computed(() => ({
    flex: `${this.panelHeights().main} 1 0px`,
    minHeight: 'clamp(140px, 24dvh, 220px)',
  }));

  protected toggleMenu(): void {
    this.menuExpanded.update((expanded) => !expanded);
    this.reportExportError.set(null);
  }

  protected closeMenu(): void {
    this.menuExpanded.set(false);
  }

  protected closeOverlays(): void {
    this.menuExpanded.set(false);
    this.autoStopSettingsExpanded.set(false);
  }

  protected handleDocumentClick(event: MouseEvent): void {
    const target = event.target;
    if (!(target instanceof Element)) {
      this.closeOverlays();
      return;
    }

    if (!target.closest('.topbar-menu')) this.menuExpanded.set(false);
    if (!target.closest('.auto-stop-settings, .auto-stop-settings-button')) {
      this.autoStopSettingsExpanded.set(false);
    }
  }

  protected async exportStatistics(): Promise<void> {
    if (this.exportStatisticsDisabled() || this.reportExportPending()) return;

    this.reportExportPending.set(true);
    this.reportExportError.set(null);

    try {
      const response = await fetch(environment.reportExportUrl);
      if (!response.ok) {
        const payload: unknown = await response.json().catch(() => null);
        const message =
          typeof payload === 'object' &&
          payload !== null &&
          'error' in payload &&
          typeof payload.error === 'string'
            ? payload.error
            : `Export failed (${response.status})`;
        throw new Error(message);
      }

      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') ?? '';
      const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? 'reports.zip';
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      this.closeMenu();
    } catch (error: unknown) {
      this.reportExportError.set(
        error instanceof Error ? error.message : 'Export failed.',
      );
    } finally {
      this.reportExportPending.set(false);
    }
  }

  protected toggleReplay(): void {
    if (this.replayRequestPending()) return;

    const action = this.replayPlaying() ? 'stop' : 'start';
    if (action === 'stop') {
      this.stopOnNextCandleUpdate = false;
      this.stopAfterReplayStarts = false;
    }
    this.pendingReplayAction = action;
    this.replayRequestPending.set(true);
    this.replayRequestError.set(null);
    this.replayControl.setReplayState(action).subscribe({
      next: () => {
        this.replayPlaying.set(action === 'start');
        this.replayRequestPending.set(false);
        this.pendingReplayAction = null;
        if (action === 'start' && this.stopAfterReplayStarts) {
          this.stopAfterReplayStarts = false;
          this.toggleReplay();
        }
      },
      error: (error: unknown) => {
        this.replayRequestPending.set(false);
        this.pendingReplayAction = null;
        this.stopAfterReplayStarts = false;
        this.stopOnNextCandleUpdate = false;
        this.replayRequestError.set(
          error instanceof HttpErrorResponse
            ? error.status === 0
              ? 'Replay backend is unavailable.'
              : `Replay request failed (HTTP ${error.status}).`
            : 'Replay request failed.',
        );
      },
    });
  }

  protected setAutoStopEvent(event: AutoStopEvent, change: Event): void {
    if (!(change.target instanceof HTMLInputElement)) return;
    const checked = change.target.checked;
    this.autoStopEvents.update((events) => ({ ...events, [event]: checked }));
  }

  protected toggleAutoStopSettings(): void {
    this.autoStopSettingsExpanded.update((expanded) => !expanded);
  }

  protected clearAutoStopEvents(): void {
    this.autoStopEvents.set({ tradeOpen: false, orderPlaced: false });
  }

  protected handleSymbolLogoError(url: string): void {
    this.failedSymbolLogoUrl.set(url);
  }

  protected runUntilNextCandle(): void {
    if (!this.canRunUntilNextCandle()) return;
    this.candleUpdateSequenceAtStart =
      this.marketSocket.selectedCandleUpdateSequence();
    this.stopOnNextCandleUpdate = true;
    this.toggleReplay();
  }

  constructor() {
    effect(() => {
      const entities = this.displayedPositionEntities();
      untracked(() => this.handlePositionEntityChanges(entities));
    });
    this.marketSocket.selectedCandleUpdates
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((sequence) => this.handleSelectedCandleUpdate(sequence));
    this.marketSocket.start();
  }

  private handlePositionEntityChanges(
    entities: ReturnType<typeof this.displayedPositionEntities>,
  ): void {
    const currentKeys = new Set(entities.map((entity) => `${entity.type}:${entity.id}`));
    const isNewEntity = (entity: (typeof entities)[number]): boolean =>
      !this.previousPositionKeys.has(`${entity.type}:${entity.id}`);
    const newlyAddedEntities = this.hasObservedPositions
      ? entities.filter(isNewEntity)
      : [];

    this.previousPositionKeys = currentKeys;
    this.hasObservedPositions = true;

    const autoStopEvents = this.autoStopEvents();
    const shouldStop = newlyAddedEntities.some(
      (entity) =>
        (entity.type === 'trade' && autoStopEvents.tradeOpen) ||
        (entity.type === 'order' && autoStopEvents.orderPlaced),
    );
    if (!shouldStop) return;
    if (this.replayPlaying() && !this.replayRequestPending()) {
      this.toggleReplay();
    } else if (
      this.replayRequestPending() &&
      this.pendingReplayAction === 'start'
    ) {
      this.stopAfterReplayStarts = true;
    }
  }

  private handleSelectedCandleUpdate(sequence: number): void {
    if (
      !this.stopOnNextCandleUpdate ||
      sequence <= this.candleUpdateSequenceAtStart
    ) {
      return;
    }

    this.stopOnNextCandleUpdate = false;
    if (this.replayRequestPending() && this.pendingReplayAction === 'start') {
      this.stopAfterReplayStarts = true;
    } else if (this.replayPlaying() && !this.replayRequestPending()) {
      this.toggleReplay();
    }
  }

  protected selectTimeframe(timeframe: Timeframe): void {
    this.marketSocket.select(timeframe);
  }

  protected hoverPosition(id: string): void {
    this.hoveredPositionId.set(id);
  }

  protected clearHoveredPosition(id: string): void {
    if (this.hoveredPositionId() === id) this.hoveredPositionId.set(null);
  }

  protected formatTimeframe(timeframe: Timeframe): string {
    return formatTimeframeLabel(timeframe);
  }

  protected setOscillatorExpanded(kind: OscillatorKind, expanded: boolean): void {
    this.oscillatorExpanded.update((items) => ({ ...items, [kind]: expanded }));
  }

  protected isOscillatorExpanded(kind: OscillatorKind): boolean {
    return this.oscillatorExpanded()[kind];
  }

  protected oscillatorStyle(kind: OscillatorKind, expanded: boolean) {
    return expanded
      ? {
          flex: `${this.panelHeights()[kind]} 1 0px`,
          minHeight: 'clamp(80px, 13dvh, 120px)',
        }
      : { flex: '0 0 38px', minHeight: '38px' };
  }

  protected onResizePointerDown(split: number, event: PointerEvent): void {
    if (event.button !== 0 || !event.isPrimary) return;
    event.preventDefault();
    this.resizingSplit.set(split);
    this.resizingPointerId = event.pointerId;
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    document.body.classList.add('resizing-chart-panels');
  }

  protected onResizeKeydown(split: number, event: KeyboardEvent): void {
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return;
    const pair = this.resizePair(split);
    if (!pair) return;
    event.preventDefault();
    const next = { ...this.panelHeights() };
    const { upperKey, lowerKey } = pair;
    const pairWeight = next[upperKey] + next[lowerKey];
    const step = pairWeight * 0.025 * (event.key === 'ArrowUp' ? 1 : -1);
    const upperWeight = Math.max(pairWeight * 0.2, Math.min(pairWeight * 0.8, next[upperKey] + step));
    next[upperKey] = upperWeight;
    next[lowerKey] = pairWeight - upperWeight;
    this.panelHeights.set(next);
  }

  protected onResizePointerMove(event: PointerEvent): void {
    const split = this.resizingSplit();
    if (split === null || event.pointerId !== this.resizingPointerId) return;

    const handle = event.currentTarget as HTMLElement;
    const panels = handle.closest<HTMLElement>('.chart-panels');
    const main = panels?.querySelector<HTMLElement>('.main-chart-panel');
    const oscillators = panels?.querySelectorAll<HTMLElement>('app-oscillator-panel');
    const pair = this.resizePair(split);
    if (!panels || !main || !oscillators || !pair || oscillators.length <= split) return;

    const next = { ...this.panelHeights() };
    const upperElement = split === 0 ? main : oscillators[split - 1];
    const lowerElement = oscillators[split];
    const upperBounds = upperElement.getBoundingClientRect();
    const lowerBounds = lowerElement.getBoundingClientRect();
    const pairHeight = upperBounds.height + lowerBounds.height;
    const upperMinimum = parseFloat(getComputedStyle(upperElement).minHeight);
    const lowerMinimum = parseFloat(getComputedStyle(lowerElement).minHeight);
    const desiredUpper =
      event.clientY - upperBounds.top - handle.getBoundingClientRect().height / 2;
    const upperHeight = Math.max(
      upperMinimum,
      Math.min(pairHeight - lowerMinimum, desiredUpper),
    );
    const pairWeight = next[pair.upperKey] + next[pair.lowerKey];
    next[pair.upperKey] = pairWeight * (upperHeight / pairHeight);
    next[pair.lowerKey] = pairWeight - next[pair.upperKey];

    this.panelHeights.set(next);
  }

  protected resizeLabel(split: number): string {
    const panels = this.oscillators();
    if (split === 0) return `Resize Main Chart and ${panels[0]?.title ?? 'chart panel'}`;
    return `Resize ${panels[split - 1]?.title ?? 'chart panel'} and ${panels[split]?.title ?? 'chart panel'}`;
  }

  protected hasResizePair(split: number): boolean {
    const panels = this.oscillators();
    if (split === 0) return !!panels[0]?.expanded;
    return !!panels[split - 1]?.expanded && !!panels[split]?.expanded;
  }

  protected endResize(event: PointerEvent): void {
    if (event.pointerId !== this.resizingPointerId) return;
    this.resizingSplit.set(null);
    this.resizingPointerId = null;
    document.body.classList.remove('resizing-chart-panels');
    const target = event.currentTarget as HTMLElement;
    if (target.hasPointerCapture(event.pointerId)) {
      target.releasePointerCapture(event.pointerId);
    }
  }

  protected togglePanel(panel: string): void {
    this.panelExpanded.update((expanded) => ({
      ...expanded,
      [panel]: !expanded[panel],
    }));
  }

  protected positionOrderLabel(type: PositionChild['type']): string {
    switch (type) {
      case 'increase_order':
        return 'Increase Order';
      case 'take_profit':
        return 'Take Profit';
      case 'stop_loss':
        return 'Stop Loss';
      case 'liquidation_order':
        return 'Liquidation Order';
    }
  }

  protected positionOrderPrice(order: PositionChild): string {
    const price = order.type === 'increase_order'
      ? order.entry_price
      : order.stop_price ?? '—';
    return price === '—' ? price : this.formatPositionNumber(price);
  }

  protected positionSideClass(side: string | null): 'position-long' | 'position-short' | null {
    const normalizedSide = side?.toLowerCase();
    if (normalizedSide === 'long' || normalizedSide === '1') return 'position-long';
    if (normalizedSide === 'short' || normalizedSide === '-1') return 'position-short';
    return null;
  }

  protected positionSideLabel(side: string | null): string {
    const sideClass = this.positionSideClass(side);
    if (sideClass === 'position-long') return 'Long';
    if (sideClass === 'position-short') return 'Short';
    return side ?? '—';
  }

  protected formatCloseRate(value: string): string {
    const rate = Number(value.replace(/,/g, '').trim());
    if (!Number.isFinite(rate)) return value;
    return this.formatPositionNumber(String(rate * 100));
  }

  protected formatDollarValue(value: string): string {
    const amount = value.trim();
    return amount.startsWith('-')
      ? `-$${this.formatPositionNumber(amount.slice(1))}`
      : `$${this.formatPositionNumber(amount)}`;
  }

  protected formatPositionNumber(value: string): string {
    const normalized = value.replace(/,/g, '').trim();
    const number = Number(normalized);
    if (!Number.isFinite(number)) return value;
    const fractionalDigits = normalized.match(/\.(\d+)/)?.[1].length ?? 0;
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 2,
      minimumFractionDigits: Math.min(fractionalDigits, 2),
    }).format(number);
  }

  protected positionPnlClass(value: string): 'positive' | 'negative' | null {
    if (value.trim() === '') return null;
    const amount = Number(value.replace(/,/g, ''));
    if (!Number.isFinite(amount)) return null;
    return amount < 0 ? 'negative' : 'positive';
  }

  protected formatNewsMetric(value: number | undefined): string {
    return value === undefined ? '—' : value.toFixed(2);
  }

  protected formatNewsTime(timestamp: number): string {
    return new Date(timestamp).toLocaleString('en-GB', {
      timeZone: 'UTC',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  protected newsDateTime(timestamp: number): string {
    return new Date(timestamp).toISOString();
  }

  protected isContextChartExpanded(target: string): boolean {
    return this.contextChartExpanded()[target] ?? true;
  }

  protected toggleContextChart(target: string): void {
    this.contextChartExpanded.update((expanded) => ({
      ...expanded,
      [target]: !this.isContextChartExpanded(target),
    }));
  }

  protected selectAnalysisView(event: Event): void {
    if (!(event.target instanceof HTMLSelectElement)) return;
    const selectedName = event.target.value;
    if (this.analysisNames().includes(selectedName)) {
      this.selectedAnalysisName.set(selectedName);
    }
  }

  protected formatStatisticKey(key: string): string {
    return (
      STATISTIC_LABELS[key] ??
      key
        .replace(/[_-]+/g, ' ')
        .replace(/\b\w/g, (letter) => letter.toUpperCase())
    );
  }

  protected formatStatisticValue(key: string, value: AnalysisStatisticValue): string {
    if (value === null) return '—';

    const rawValue = String(value);
    const roundedValue =
      typeof value === 'boolean' ? rawValue : this.formatPositionNumber(rawValue);
    switch (key.toLowerCase()) {
      case 'pnl': {
        const numericValue = this.statisticNumber(value);
        return numericValue !== null && numericValue < 0
          ? `-$${this.formatPositionNumber(rawValue.replace(/^-/, ''))}`
          : `$${roundedValue}`;
      }
      case 'winrate':
      case 'roi':
      case 'max_drawdown': {
        const numericValue = this.statisticNumber(value);
        const percentage =
          numericValue === null
            ? roundedValue
            : this.formatPositionNumber(String(numericValue * 100));
        return `${percentage}%`;
      }
      case 'average_trade_duration': {
        const seconds = this.statisticNumber(value);
        if (seconds === null) return rawValue;
        const totalSeconds = Math.floor(Math.abs(seconds));
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const remainingSeconds = totalSeconds % 60;
        const sign = seconds < 0 ? '-' : '';
        return `${sign}${hours}:${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
      }
      default:
        return roundedValue;
    }
  }

  protected isPositiveStatistic(key: string, value: AnalysisStatisticValue): boolean {
    const numericValue = this.statisticNumber(value);
    if (numericValue === null) return false;
    const normalizedKey = key.toLowerCase();
    return (
      (normalizedKey === 'winrate' && numericValue >= 0.5) ||
      ((normalizedKey === 'pnl' || normalizedKey === 'roi') && numericValue >= 0)
    );
  }

  protected isNegativeStatistic(key: string, value: AnalysisStatisticValue): boolean {
    const numericValue = this.statisticNumber(value);
    if (numericValue === null) return false;
    const normalizedKey = key.toLowerCase();
    return (
      (normalizedKey === 'winrate' && numericValue < 0.5) ||
      ((normalizedKey === 'pnl' || normalizedKey === 'roi') && numericValue < 0)
    );
  }

  private statisticNumber(value: AnalysisStatisticValue): number | null {
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    if (typeof value !== 'string' || value.trim() === '') return null;
    const numericValue = Number(value.replace(/,/g, ''));
    return Number.isFinite(numericValue) ? numericValue : null;
  }

  protected formatPrice(value: number): string {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  private resizePair(
    split: number,
  ): { upperKey: 'main' | OscillatorKind; lowerKey: OscillatorKind } | null {
    const panels = this.oscillators();
    if (split === 0) {
      return panels[0] ? { upperKey: 'main', lowerKey: panels[0].kind } : null;
    }
    const upper = panels[split - 1];
    const lower = panels[split];
    return upper && lower ? { upperKey: upper.kind, lowerKey: lower.kind } : null;
  }

}
