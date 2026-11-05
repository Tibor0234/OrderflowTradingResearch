import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { vi } from 'vitest';
import { App } from './app';
import { MarketDataSocketService } from './core/services/market-data-socket.service';
import { formatTimeframe, Timeframe } from './shared/models/market-data.models';
import { environment } from '../environments/environment';

class FakeWebSocket {
  static readonly OPEN = 1;
  static instances: FakeWebSocket[] = [];
  readonly OPEN = 1;
  readyState = 0;
  sent: Array<Record<string, unknown>> = [];
  closed = false;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: unknown }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  send(data: string): void {
    this.sent.push(JSON.parse(data));
  }

  close(): void {
    this.closed = true;
  }

  closeFromServer(): void {
    this.readyState = 3;
    this.onclose?.();
  }

  open(): void {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.();
  }

  receive(data: unknown): void {
    if (Array.isArray(data)) {
      data.forEach((message) => this.receive(message));
      return;
    }
    this.onmessage?.({ data: typeof data === 'string' ? data : JSON.stringify(data) });
  }
}

function initTarget(
  socket: FakeWebSocket,
  target = 'main_chart/0',
  candleSeconds = 60,
  length = 100,
  bigTrades = false,
  topPct = 0,
): void {
  socket.receive([
    {
      type: 'resource_init',
      data: { resource_type: 'cvd', target, length, big_trades: bigTrades, big_trades_pct: topPct },
    },
    {
      type: 'resource_init',
      data: {
        resource_type: 'volume_delta',
        target,
        length,
        big_trades: bigTrades,
        big_trades_pct: topPct,
      },
    },
    {
      type: 'resource_init',
      data: { resource_type: 'timeframe', target, candle_seconds: candleSeconds, length },
    },
  ]);
}

function initContextTarget(socket: FakeWebSocket, id: string, period: string): void {
  socket.receive({
    type: 'resource_init',
    data: { resource_type: 'ohlcv_timeframe', target: `context_chart/${id}`, period },
  });
}

function initNewsTarget(socket: FakeWebSocket): void {
  socket.receive({
    type: 'resource_init',
    data: { resource_type: 'news', target: 'news_panel' },
  });
}

function message(
  timestamp: number,
  overrides: {
    target?: string;
    open?: number | string;
    high?: number | string;
    low?: number | string;
    close?: number | string;
    volumeDelta?: number | string;
    cvd?: number | string;
  } = {},
): Record<string, unknown>[] {
  const target = overrides.target ?? 'main_chart/0';
  return [
    {
      type: 'market_update',
      data: {
        resource_type: 'timeframe',
        target,
        time: timestamp,
        open: overrides.open ?? '100.0',
        high: overrides.high ?? '110.0',
        low: overrides.low ?? '95.0',
        close: overrides.close ?? '105.0',
      },
    },
    {
      type: 'market_update',
      data: {
        resource_type: 'volume_delta',
        target,
        time: timestamp,
        value: overrides.volumeDelta ?? '3.0',
      },
    },
    {
      type: 'market_update',
      data: {
        resource_type: 'cvd',
        target,
        time: timestamp,
        value: overrides.cvd ?? '3.0',
      },
    },
  ];
}

function waitForDisplayUpdate(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 40));
}

describe('App dashboard', () => {
  beforeEach(async () => {
    FakeWebSocket.instances = [];
    vi.stubGlobal('WebSocket', FakeWebSocket);
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders the dashboard panels in their requested order', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    expect(root.querySelector('.session-count strong')?.textContent).toBe('—');
    expect(root.querySelector('.symbol-button')?.textContent?.trim()).toBe('—');
    socket.open();
    initContextTarget(socket, '1', '1D');
    initContextTarget(socket, '2', '1W');
    initNewsTarget(socket);
    fixture.detectChanges();

    expect(root.querySelector('.topbar')).toBeTruthy();
    expect(root.querySelector('app-context-chart h2')?.textContent?.trim()).toBe('1D');
    expect(root.querySelectorAll('app-context-chart h2')[1]?.textContent?.trim()).toBe('1W');
    expect(Array.from(root.querySelectorAll('app-context-chart .heading-note'), (note) => note.textContent?.trim())).toEqual(['', '']);
    expect(root.querySelector('.news-panel h2')?.textContent).toContain('News');
    expect(root.querySelector('.values-panel')).toBeNull();
    expect(root.querySelector('.main-chart-panel h1')).toBeNull();
    expect(root.querySelector('.chart-toolbar')).toBeNull();
    expect(root.querySelector('.main-chart-panel .timeframe-controls')).toBeTruthy();
    expect(root.querySelector('.main-chart-panel .chart-legend')).toBeNull();
    expect(root.querySelectorAll('app-oscillator-panel')).toHaveLength(0);
    expect(root.querySelectorAll('.chart-resize-handle')).toHaveLength(0);
    expect(root.querySelector('.performance-panel h2')?.textContent).toContain('Statistics');
    expect(root.querySelector('.equity-line')).toBeNull();
    expect(root.querySelector('.stats-grid')).toBeNull();
    expect(root.querySelector('.positions-panel h2')?.textContent).toContain('Positions');
    expect(root.querySelector('.orders-panel')).toBeNull();
    expect(root.querySelector('.stop-panel')).toBeNull();
  });

  it('renders position snapshots and applies position lifecycle messages', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();

    socket.receive({
      type: 'position_init',
      data: {
        trades: [
          {
            type: 'trade',
            id: 'trade-1',
            side: '1',
            value: '1.567',
            leverage: '10.126',
            pnl: '12.567',
            execution_price: '100.126',
          },
        ],
        orders: [
          {
            type: 'order',
            id: 'order-1',
            side: 'short',
            value: '0.567',
            leverage: '5.678',
            entry_price: '110.126',
          },
          {
            type: 'increase_order',
            id: 'increase-2',
            source_id: 'trade-1',
            side: 'long',
            value: '0.25',
            leverage: '10',
            entry_price: '98',
          },
          {
            type: 'increase_order',
            id: 'increase-1',
            source_id: 'trade-1',
            side: 'long',
            value: '0.25',
            leverage: '10',
            entry_price: '99',
          },
        ],
        stop_orders: [
          {
            type: 'liquidation_order',
            id: 'liquidation-1',
            source_id: 'trade-1',
            side: '-1',
            close_rate: '0.8',
            stop_price: null,
          },
          {
            type: 'liquidation_order',
            id: 'liquidation-long',
            source_id: 'trade-1',
            side: '1',
            close_rate: '0.75',
            stop_price: null,
          },
          {
            type: 'stop_loss',
            id: 'stop-1',
            source_id: 'trade-1',
            side: 'short',
            close_rate: '0.9',
            stop_price: '90',
          },
          {
            type: 'take_profit',
            id: 'take-2',
            source_id: 'trade-1',
            side: 'short',
            close_rate: '1.2',
            stop_price: '120',
          },
          {
            type: 'take_profit',
            id: 'take-1',
            source_id: 'trade-1',
            side: 'short',
            close_rate: '1.15567',
            stop_price: '115.345',
          },
        ],
      },
    });
    fixture.detectChanges();

    initTarget(socket);
    socket.receive(message(1_000));
    await waitForDisplayUpdate();
    fixture.detectChanges();

    expect(root.querySelector('.stop-panel')).toBeNull();
    expect(root.querySelectorAll('.position-entry-levels .order-entry-line')).toHaveLength(6);
    expect(root.querySelectorAll('.position-entry-levels .trade-entry-line')).toHaveLength(1);
    expect(root.querySelector('.current-price-label')?.textContent?.trim()).toBe('Price 105.0');
    expect(root.querySelector('.position-entry-levels [data-position-id="liquidation-1"]'))
      .toBeNull();
    expect(root.querySelector('.trade-entry-line[data-position-id="trade-1"]')?.classList.contains('long'))
      .toBe(true);
    expect(
      root.querySelector('.position-entry-price[data-position-price-id="trade-1"]')?.textContent?.trim(),
    ).toBe('Trade 100.1');
    expect(
      root.querySelector('.position-entry-price[data-position-price-id="order-1"]')?.textContent?.trim(),
    ).toBe('Order 110.1');
    const tradeCard = root.querySelector<HTMLElement>(
      '.positions-panel .position-trade[data-position-id="trade-1"]',
    )!;
    tradeCard.dispatchEvent(new Event('mouseenter'));
    fixture.detectChanges();
    expect(tradeCard.classList.contains('is-hovered')).toBe(true);
    expect(root.querySelector('.trade-entry-line[data-position-id="trade-1"]')?.classList.contains('hovered'))
      .toBe(true);
    expect(root.querySelector('.position-entry-price[data-position-price-id="trade-1"]')?.classList.contains('hovered'))
      .toBe(true);
    tradeCard.dispatchEvent(new Event('mouseleave'));
    fixture.detectChanges();
    expect(tradeCard.classList.contains('is-hovered')).toBe(false);
    expect(root.querySelector('.trade-entry-line[data-position-id="trade-1"]')?.classList.contains('hovered'))
      .toBe(false);

    const orderCard = root.querySelector<HTMLElement>(
      '.positions-panel .position-order[data-position-id="order-1"]',
    )!;
    orderCard.dispatchEvent(new Event('mouseenter'));
    fixture.detectChanges();
    expect(orderCard.classList.contains('is-hovered')).toBe(true);
    expect(root.querySelector('.order-entry-line[data-position-id="order-1"]')?.classList.contains('hovered'))
      .toBe(true);
    orderCard.dispatchEvent(new Event('mouseleave'));
    fixture.detectChanges();
    expect(orderCard.classList.contains('is-hovered')).toBe(false);
    expect(root.querySelector('.order-entry-line[data-position-id="order-1"]')?.classList.contains('hovered'))
      .toBe(false);

    const liquidationCard = root.querySelector<HTMLElement>(
      '.position-child[data-position-id="liquidation-1"]',
    )!;
    liquidationCard.dispatchEvent(new Event('mouseenter'));
    fixture.detectChanges();
    expect(liquidationCard.classList.contains('is-hovered')).toBe(false);
    expect(root.querySelector('.position-entry-levels .hovered')).toBeNull();
    liquidationCard.dispatchEvent(new Event('mouseleave'));

    expect(root.querySelectorAll('.positions-panel .position-order[data-position-id]')).toHaveLength(1);
    expect(root.querySelector('.positions-panel thead')).toBeNull();
    expect(root.querySelector('[data-position-id="trade-1"] .position-entry-details')?.textContent)
      .toContain('Size $1.57 × 10.13');
    expect(root.querySelector('[data-position-id="trade-1"] .position-entry-heading')?.textContent)
      .toContain('PnL $12.57');
    expect(root.querySelector('[data-position-id="trade-1"] .position-entry-details')?.textContent)
      .toContain('Entry 100.13');
    expect(root.querySelector('[data-position-id="trade-1"] .position-entry-heading .positive'))
      .toBeTruthy();
    expect(root.querySelector('[data-position-id="order-1"] .position-entry-details')?.textContent)
      .toContain('Size $0.57 × 5.68');
    expect(root.querySelector('[data-position-id="order-1"] .position-entry-details')?.textContent)
      .toContain('Entry 110.13');
    expect(root.querySelector('[data-position-id="take-1"] .position-entry-details')?.textContent)
      .toContain('Close Rate 115.57%');
    expect(root.querySelector('[data-position-id="take-1"] .position-entry-details')?.textContent)
      .toContain('Trigger 115.35');
    expect(root.querySelector('[data-position-id="liquidation-1"] .position-entry-details')?.textContent)
      .toContain('Trigger —');
    expect(root.querySelector('[data-position-id="liquidation-1"] .position-entry-heading > span:last-child')?.textContent)
      .toBe('Short');
    expect(root.querySelector('[data-position-id="liquidation-1"] .position-entry-heading .position-short'))
      .toBeTruthy();
    expect(root.querySelector('[data-position-id="liquidation-long"] .position-entry-heading > span:last-child')?.textContent)
      .toBe('Long');
    expect(root.querySelector('[data-position-id="trade-1"] .position-entry-heading strong')?.textContent)
      .toBe('Trade · Long');
    expect(root.querySelector('[data-position-id="trade-1"] .position-entry-heading .position-long'))
      .toBeTruthy();
    expect(
      Array.from(root.querySelectorAll('.position-child .position-entry-heading > span:first-child'), (label) =>
        label.textContent?.trim(),
      ),
    ).toEqual([
      'Increase Order',
      'Increase Order',
      'Take Profit',
      'Take Profit',
      'Stop Loss',
      'Liquidation Order',
      'Liquidation Order',
    ]);
    expect(
      Array.from(root.querySelectorAll('.position-child-kind'), (label) =>
        label.getAttribute('data-order-type'),
      ),
    ).toEqual([
      'increase_order',
      'increase_order',
      'take_profit',
      'take_profit',
      'stop_loss',
      'liquidation_order',
      'liquidation_order',
    ]);

    socket.receive([
      {
        type: 'position_update',
        data: {
          type: 'trade',
          id: 'trade-1',
          side: 'long',
          margin: '1.5',
          leverage: '10',
          pnl: '-15',
          execution_price: '100',
        },
      },
      {
        type: 'position_update',
        data: {
          type: 'increase_order',
          id: 'increase-1',
          source_id: 'trade-1',
          side: 'long',
          margin: '0.5',
          leverage: '10',
          entry_price: '97',
        },
      },
      {
        type: 'position_update',
        data: {
          type: 'order',
          id: 'order-1',
          side: 'short',
          margin: '0.3',
          leverage: '5.678',
          entry_price: '110.126',
        },
      },
      {
        type: 'position_update',
        data: {
          type: 'order',
          id: 'order-2',
          side: 'long',
          margin: '0.2',
          leverage: '5',
          entry_price: '95',
        },
      },
    ]);
    fixture.detectChanges();
    expect(root.querySelector('.positions-panel [data-position-id="trade-1"]')?.textContent)
      .toContain('PnL -$15');
    expect(root.querySelector('.positions-panel [data-position-id="trade-1"] .position-entry-heading .negative'))
      .toBeTruthy();
    expect(root.querySelector('.positions-panel [data-position-id="trade-1"]')?.textContent)
      .toContain('Size $1.5 × 10');
    expect(root.querySelector('.positions-panel [data-position-id="increase-1"]')?.textContent)
      .toContain('Size $0.5 × 10');
    expect(root.querySelector('.positions-panel [data-position-id="increase-1"]')?.textContent)
      .toContain('Entry 97');
    expect(root.querySelector('.positions-panel [data-position-id="order-2"]')?.textContent)
      .toContain('Size $0.2 × 5');
    expect(root.querySelector('.positions-panel [data-position-id="order-1"]')?.textContent)
      .toContain('Size $0.3 × 5.68');
    expect(root.querySelectorAll('.positions-panel .position-order[data-position-id]')).toHaveLength(2);

    socket.receive({ type: 'position_remove', data: { id: 'trade-1' } });
    fixture.detectChanges();
    expect(root.querySelector('.positions-panel .position-trade[data-position-id="trade-1"]'))
      .toBeNull();
    expect(root.querySelector('.trade-entry-line[data-position-id="trade-1"]')).toBeNull();

    socket.receive({
      type: 'position_remove',
      data: {
        type: 'order',
        id: 'order-1',
        side: 'short',
        margin: '0.5',
        leverage: '5',
        entry_price: '110',
      },
    });
    fixture.detectChanges();
    expect(root.querySelector('[data-position-id="order-1"]')).toBeNull();
    expect(root.querySelectorAll('.positions-panel .position-order[data-position-id]')).toHaveLength(1);

    socket.receive({ type: 'position_clear', data: {} });
    fixture.detectChanges();
    expect(root.querySelector('.position-group')).toBeNull();
    expect(root.querySelector('.position-empty')?.textContent).toContain('No active positions');
    expect(root.querySelectorAll('.positions-panel .position-order[data-position-id]')).toHaveLength(0);
  });

  it('does not render placeholder positions or orders', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];

    expect(root.querySelectorAll('.positions-panel .position-trade-group')).toHaveLength(0);
    expect(root.querySelectorAll('.positions-panel .position-order[data-position-id]')).toHaveLength(0);

    socket.open();
    socket.receive({ type: 'position_clear', data: {} });
    fixture.detectChanges();

    expect(root.querySelectorAll('.positions-panel .position-trade-group')).toHaveLength(0);
    expect(root.querySelectorAll('.positions-panel .position-order[data-position-id]')).toHaveLength(0);
  });

  it('nests child orders under standalone orders and omits them from the chart', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    socket.receive({
      type: 'position_init',
      data: {
        trades: [],
        orders: [
          {
            type: 'order',
            id: 'parent-order',
            side: '1',
            value: '1',
            leverage: '5',
            entry_price: '100',
          },
        ],
        stop_orders: [
          {
            type: 'take_profit',
            id: 'order-take-profit',
            source_id: 'parent-order',
            side: '-1',
            close_rate: '1',
            stop_price: '110',
          },
          {
            type: 'stop_loss',
            id: 'order-stop-loss',
            source_id: 'parent-order',
            side: '-1',
            close_rate: '1',
            stop_price: '90',
          },
        ],
      },
    });
    initTarget(socket);
    socket.receive(message(1_000));
    await waitForDisplayUpdate();
    fixture.detectChanges();

    const orderGroup = root.querySelector<HTMLElement>(
      '.position-order-group .position-order[data-position-id="parent-order"]',
    )?.parentElement;
    expect(orderGroup?.querySelector('[data-position-id="order-take-profit"]')).toBeTruthy();
    expect(orderGroup?.querySelector('[data-position-id="order-stop-loss"]')).toBeTruthy();
    expect(root.querySelector('.position-entry-levels [data-position-id="order-take-profit"]'))
      .toBeNull();
    expect(root.querySelector('.position-entry-levels [data-position-id="order-stop-loss"]'))
      .toBeNull();

    const takeProfit = orderGroup?.querySelector<HTMLElement>(
      '[data-position-id="order-take-profit"]',
    );
    takeProfit?.dispatchEvent(new Event('mouseenter'));
    fixture.detectChanges();
    expect(takeProfit?.classList.contains('is-hovered')).toBe(false);
    expect(orderGroup?.querySelector('.position-order')?.classList.contains('is-hovered'))
      .toBe(false);
    expect(root.querySelector('.position-entry-levels .hovered')).toBeNull();
  });

  it('converts numeric sides on standalone orders to Long and Short', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    socket.receive([
      {
        type: 'position_update',
        data: {
          type: 'order',
          id: 'long-order',
          side: '1',
          margin: '1',
          leverage: '5',
          entry_price: '100',
        },
      },
      {
        type: 'position_update',
        data: {
          type: 'order',
          id: 'short-order',
          side: '-1',
          margin: '1',
          leverage: '5',
          entry_price: '100',
        },
      },
    ]);
    fixture.detectChanges();

    expect(
      root.querySelector('[data-position-id="long-order"] .position-entry-heading')?.textContent,
    ).toContain('Order · Long');
    expect(
      root.querySelector('[data-position-id="short-order"] .position-entry-heading')?.textContent,
    ).toContain('Order · Short');
  });

  it('updates the header from session start messages and accepts a null symbol', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();

    expect(root.querySelector('.brand-name')?.textContent).toBe('—');

    socket.receive({
      type: 'session_start',
      data: {
        strategy_name: 'Momentum Strategy',
        session_number: 4,
        symbol: 'ETHUSDT',
        progress: '4/20',
      },
    });
    fixture.detectChanges();

    expect(root.querySelector('.brand-name')?.textContent).toBe('Momentum Strategy');
    expect(root.querySelector('.brand-mark')).toBeNull();
    expect(root.querySelector('.topbar-controls .play-button')).toBeTruthy();
    expect(root.querySelector('.session-meta')).toBeNull();
    expect(root.querySelectorAll('.session-summary .topbar-divider')).toHaveLength(3);
    expect(root.querySelector('.session-count')?.textContent).toContain('04');
    expect(root.querySelector('.symbol-button')?.textContent?.trim()).toBe('ETHUSDT');
    expect(root.querySelector('.symbol-button')?.getAttribute('aria-label')).toBe(
      'Selected symbol ETHUSDT',
    );
    const symbolLogo = root.querySelector<HTMLImageElement>('.symbol-logo');
    expect(symbolLogo?.getAttribute('src'))
      .toBe('https://assets.coincap.io/assets/icons/eth@2x.png');
    expect(root.querySelector('.coin-mark')).toBeNull();
    expect(root.querySelector('.chevron')).toBeNull();
    expect(root.querySelector('.market-price')).toBeNull();
    expect(root.querySelector('.market-change')).toBeNull();
    expect(root.querySelector('.session-progress strong')?.textContent).toContain('4/20');

    symbolLogo?.dispatchEvent(new Event('error'));
    fixture.detectChanges();
    expect(root.querySelector('.symbol-logo')).toBeNull();
    expect(root.querySelector('.symbol-button')?.textContent?.trim()).toBe('ETHUSDT');

    socket.receive({
      type: 'session_start',
      data: {
        strategy_name: 'Momentum Strategy',
        session_number: 5,
        symbol: null,
        progress: '5/20',
      },
    });
    fixture.detectChanges();
    expect(root.querySelector('.symbol-button')?.textContent?.trim()).toBe('None');
    expect(root.querySelector('.symbol-logo')).toBeNull();
    expect(root.querySelector('.session-count')?.textContent).toContain('05');
  });

  it('clears displayed market update data on session start while keeping resources registered', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    const mainTarget = 'main_chart/0';
    const contextTarget = 'context_chart/1';
    const newsTarget = 'news_panel';
    socket.open();
    initTarget(socket, mainTarget);
    initContextTarget(socket, '1', '1D');
    initNewsTarget(socket);

    socket.receive([
      {
        type: 'resource_init',
        data: { resource_type: 'volume_profile', target: mainTarget, price_bin_count: 12, value_area_pct: 70 },
      },
      {
        type: 'resource_init',
        data: { resource_type: 'open_interest', target: mainTarget, length: 10 },
      },
      {
        type: 'resource_init',
        data: { resource_type: 'big_trades', target: mainTarget, top_pct: 2 },
      },
      {
        type: 'resource_init',
        data: { resource_type: 'ohlcv_volume_profile', target: contextTarget, price_bin_count: 8 },
      },
    ]);

    const marketUpdates = [
      ...message(1_000),
      {
        type: 'market_update',
        data: {
          resource_type: 'volume_profile',
          target: mainTarget,
          bins: [{ low: 100, size: 1, volume: 5 }],
          poc: { price: 100.5, volume: 5 },
          value_area: { low: 100, high: 101 },
        },
      },
      {
        type: 'market_update',
        data: {
          resource_type: 'open_interest',
          target: mainTarget,
          time: 1_000,
          value: 42,
        },
      },
      {
        type: 'market_update',
        data: {
          resource_type: 'big_trades',
          target: mainTarget,
          trades: [{ time: 1_000, price: 100, quantity: 2, side: 1 }],
        },
      },
      {
        type: 'market_update',
        data: {
          resource_type: 'ohlcv_timeframe',
          target: contextTarget,
          interval: '5m',
          candles: [{ time: 1_000, open: 100, high: 105, low: 99, close: 103 }],
        },
      },
      {
        type: 'market_update',
        data: {
          resource_type: 'ohlcv_volume_profile',
          target: contextTarget,
          time: 1_000,
          bins: [{ low: 100, size: 1, volume: 5 }],
          poc: { price: 100.5, volume: 5 },
          value_area: { low: 100, high: 101 },
        },
      },
      {
        type: 'market_update',
        data: {
          resource_type: 'news',
          target: newsTarget,
          time: 1_000,
          headline: 'Market update',
          aggregated: {
            sentiment: 0.5,
            severity: 0.4,
            market_relevance: 0.7,
            symbol_relevance: 0.6,
          },
        },
      },
    ];
    socket.receive(marketUpdates);
    await waitForDisplayUpdate();

    expect(service.series().candles).toHaveLength(1);
    expect(service.series().volumeDelta).toHaveLength(1);
    expect(service.series().cvd).toHaveLength(1);
    expect(service.dynamicResources().find((item) => item.resource_type === 'volume_profile'))
      .toMatchObject({ bins: [{ low: 100, size: 1, volume: 5 }] });
    expect(service.dynamicResources().find((item) => item.resource_type === 'open_interest'))
      .toMatchObject({ points: [{ timestamp: 1_000, value: 42 }] });
    expect(service.dynamicResources().find((item) => item.resource_type === 'big_trades'))
      .toMatchObject({ trades: [{ time: 1_000, price: 100, quantity: 2, side: 1 }] });
    expect(service.contextCharts()[0]).toMatchObject({
      interval: '5m',
      candles: [{ time: 1_000, open: 100, high: 105, low: 99, close: 103 }],
      volumeProfile: { time: 1_000, bins: [{ low: 100, size: 1, volume: 5 }] },
    });
    expect(service.newsPanel()).toMatchObject({
      latestUpdateTime: 1_000,
      aggregated: { sentiment: 0.5 },
      headlines: [{ time: 1_000, headline: 'Market update' }],
    });

    socket.receive({
      type: 'session_start',
      data: {
        strategy_name: 'Momentum',
        session_number: 2,
        symbol: null,
        progress: '2/10',
      },
    });

    expect(service.series()).toEqual({ candles: [], volumeDelta: [], cvd: [] });
    expect(service.dynamicResources().find((item) => item.resource_type === 'volume_profile'))
      .toMatchObject({ bins: [], poc: null, value_area: null });
    expect(service.dynamicResources().find((item) => item.resource_type === 'open_interest'))
      .toMatchObject({ points: [] });
    expect(service.dynamicResources().find((item) => item.resource_type === 'big_trades'))
      .toMatchObject({ trades: [] });
    expect(service.contextCharts()[0]).toMatchObject({
      interval: null,
      candles: [],
      volumeProfile: { time: null, bins: [], poc: null, value_area: null },
    });
    expect(service.newsPanel()).toMatchObject({
      latestUpdateTime: null,
      aggregated: null,
      headlines: [],
    });
    expect(service.timeframes()).toEqual([60]);
    expect(service.initializedIndicators()).toHaveLength(2);
    expect(service.dynamicResources()).toHaveLength(3);

    socket.receive(marketUpdates);
    await waitForDisplayUpdate();
    expect(service.series().candles).toHaveLength(1);
    expect(service.series().volumeDelta).toHaveLength(1);
    expect(service.series().cvd).toHaveLength(1);
    expect(service.newsPanel()?.headlines).toHaveLength(1);
  });

  it('shows the news panel after init and renders aggregates with the latest three headlines', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    fixture.detectChanges();
    expect(root.querySelector('.news-panel')).toBeNull();

    initNewsTarget(socket);
    fixture.detectChanges();
    expect(root.querySelector('.news-panel h2')?.textContent).toContain('News');
    expect(Array.from(root.querySelectorAll('.news-aggregate dd'), (value) => value.textContent)).toEqual([
      '—',
      '—',
      '—',
      '—',
    ]);

    const firstTime = 1_793_064_960_000;
    const updates = [
      {
        time: firstTime,
        headline: 'Bitcoin ETF-ekbe jelentős beáramlás érkezett',
        aggregated: { sentiment: 0.65, severity: 0.8, market_relevance: 0.9, symbol_relevance: 0.75 },
      },
      {
        time: firstTime + 60_000,
        headline: 'Második hír',
        aggregated: { sentiment: 0.66, severity: 0.81, market_relevance: 0.91, symbol_relevance: 0.76 },
      },
      {
        time: firstTime + 120_000,
        headline: 'Harmadik hír',
        aggregated: { sentiment: 0.67, severity: 0.82, market_relevance: 0.92, symbol_relevance: 0.77 },
      },
      {
        time: firstTime + 180_000,
        headline: 'Negyedik, legfrissebb hír',
        aggregated: { sentiment: 0.68, severity: 0.83, market_relevance: 0.93, symbol_relevance: 0.78 },
      },
    ];
    socket.receive(
      updates.map((update) => ({
        type: 'market_update',
        data: { resource_type: 'news', target: 'news_panel', ...update },
      })),
    );
    fixture.detectChanges();

    expect(Array.from(root.querySelectorAll('.news-aggregate dd'), (value) => value.textContent)).toEqual([
      '0.68',
      '0.83',
      '0.93',
      '0.78',
    ]);
    const sentiment = root.querySelector<HTMLElement>('.news-sentiment')!;
    expect(sentiment.classList.contains('positive')).toBe(true);
    expect(sentiment.classList.contains('negative')).toBe(false);
    expect(Array.from(root.querySelectorAll('.news-item p'), (headline) => headline.textContent)).toEqual([
      'Negyedik, legfrissebb hír',
      'Harmadik hír',
      'Második hír',
    ]);
    expect(root.querySelector('.news-item time')?.getAttribute('datetime')).toBe(
      new Date(firstTime + 180_000).toISOString(),
    );

    socket.receive({
      type: 'market_update',
      data: {
        resource_type: 'news',
        target: 'news_panel',
        time: firstTime + 240_000,
        headline: 'Semleges sentiment',
        aggregated: { sentiment: 0, severity: 0.5, market_relevance: 0.5, symbol_relevance: 0.5 },
      },
    });
    fixture.detectChanges();
    expect(sentiment.textContent?.trim()).toBe('0.00');
    expect(sentiment.classList.contains('positive')).toBe(true);

    socket.receive({
      type: 'market_update',
      data: {
        resource_type: 'news',
        target: 'news_panel',
        time: firstTime + 300_000,
        headline: 'Negative sentiment',
        aggregated: { sentiment: -0.01, severity: 0.5, market_relevance: 0.5, symbol_relevance: 0.5 },
      },
    });
    fixture.detectChanges();
    expect(sentiment.textContent?.trim()).toBe('-0.01');
    expect(sentiment.classList.contains('positive')).toBe(false);
    expect(sentiment.classList.contains('negative')).toBe(true);
  });

  it('sends start and stop replay commands and changes the button only after success', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const httpTesting = TestBed.inject(HttpTestingController);
    const button = root.querySelector<HTMLButtonElement>('.play-button')!;

    expect(button.getAttribute('aria-label')).toBe('Play replay');
    button.click();
    fixture.detectChanges();

    const startRequest = httpTesting.expectOne(environment.replayControlUrl);
    expect(startRequest.request.method).toBe('POST');
    expect(startRequest.request.body).toEqual({ action: 'start' });
    expect(button.disabled).toBe(true);
    startRequest.flush({});
    fixture.detectChanges();

    expect(button.getAttribute('aria-label')).toBe('Pause replay');
    expect(button.disabled).toBe(false);
    button.click();

    const stopRequest = httpTesting.expectOne(environment.replayControlUrl);
    expect(stopRequest.request.method).toBe('POST');
    expect(stopRequest.request.body).toEqual({ action: 'stop' });
    stopRequest.flush({});
    fixture.detectChanges();

    expect(button.getAttribute('aria-label')).toBe('Play replay');
    httpTesting.verify();
  });

  it('runs until a candle update arrives on the selected timeframe', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const httpTesting = TestBed.inject(HttpTestingController);
    socket.open();
    initTarget(socket, 'main_chart/0', 60);
    initTarget(socket, 'main_chart/1', 300);
    fixture.detectChanges();

    const stepButton = root.querySelector<HTMLButtonElement>('.replay-step-button')!;
    expect(stepButton.disabled).toBe(false);
    stepButton.click();
    fixture.detectChanges();
    const startRequest = httpTesting.expectOne(environment.replayControlUrl);
    expect(startRequest.request.body).toEqual({ action: 'start' });
    expect(stepButton.disabled).toBe(true);
    startRequest.flush({});
    fixture.detectChanges();

    socket.receive({
      type: 'market_update',
      data: {
        resource_type: 'timeframe',
        target: 'main_chart/1',
        time: 1_000,
        open: '100',
        high: '101',
        low: '99',
        close: '100',
      },
    });
    fixture.detectChanges();
    httpTesting.expectNone(environment.replayControlUrl);

    socket.receive({
      type: 'market_update',
      data: {
        resource_type: 'timeframe',
        target: 'main_chart/0',
        time: 1_000,
        open: '100',
        high: '101',
        low: '99',
        close: '100',
      },
    });
    const stopRequest = httpTesting.expectOne(environment.replayControlUrl);
    expect(stopRequest.request.body).toEqual({ action: 'stop' });
    stopRequest.flush({});
    fixture.detectChanges();

    expect(root.querySelector<HTMLButtonElement>('.play-button')?.getAttribute('aria-label'))
      .toBe('Play replay');
    expect(stepButton.disabled).toBe(false);
    httpTesting.verify();
  });

  it('auto-stops replay for selected new trades and standalone orders', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const httpTesting = TestBed.inject(HttpTestingController);
    socket.open();

    root.querySelector<HTMLButtonElement>('.auto-stop-settings-button')!.click();
    fixture.detectChanges();
    const [tradeCheckbox, orderCheckbox] = Array.from(
      root.querySelectorAll<HTMLInputElement>('.auto-stop-settings input'),
    );
    expect(tradeCheckbox.checked).toBe(false);
    expect(orderCheckbox.checked).toBe(false);

    tradeCheckbox.click();
    orderCheckbox.click();
    fixture.detectChanges();
    root.querySelector<HTMLButtonElement>('.auto-stop-clear')!.click();
    fixture.detectChanges();
    expect(tradeCheckbox.checked).toBe(false);
    expect(orderCheckbox.checked).toBe(false);

    tradeCheckbox.click();
    orderCheckbox.click();
    fixture.detectChanges();
    socket.receive({
      type: 'position_init',
      data: { trades: [], orders: [], stop_orders: [] },
    });
    fixture.detectChanges();

    const replayButton = root.querySelector<HTMLButtonElement>('.play-button')!;
    replayButton.click();
    fixture.detectChanges();
    socket.receive({
      type: 'position_update',
      data: {
        type: 'trade',
        id: 'trade-auto-stop',
        side: 'long',
        margin: '1',
        leverage: '5',
        pnl: '0',
        execution_price: '100',
      },
    });
    fixture.detectChanges();
    const startRequest = httpTesting.expectOne(environment.replayControlUrl);
    expect(startRequest.request.body).toEqual({ action: 'start' });
    startRequest.flush({});
    fixture.detectChanges();
    const automaticStopRequest = httpTesting.expectOne(environment.replayControlUrl);
    expect(automaticStopRequest.request.body).toEqual({ action: 'stop' });
    automaticStopRequest.flush({});
    fixture.detectChanges();
    expect(replayButton.getAttribute('aria-label')).toBe('Play replay');

    replayButton.click();
    fixture.detectChanges();
    httpTesting.expectOne(environment.replayControlUrl).flush({});
    fixture.detectChanges();
    socket.receive({
      type: 'position_update',
      data: {
        type: 'increase_order',
        id: 'increase-auto-stop',
        source_id: 'trade-auto-stop',
        side: 'long',
        margin: '0.5',
        leverage: '5',
        entry_price: '99',
      },
    });
    fixture.detectChanges();
    httpTesting.expectNone(environment.replayControlUrl);

    socket.receive({
      type: 'position_update',
      data: {
        type: 'order',
        id: 'order-auto-stop',
        side: 'short',
        margin: '0.5',
        leverage: '5',
        entry_price: '101',
      },
    });
    fixture.detectChanges();
    httpTesting.expectOne(environment.replayControlUrl).flush({});
    fixture.detectChanges();
    expect(replayButton.getAttribute('aria-label')).toBe('Play replay');
    httpTesting.verify();
  });

  it('disables replay and shows a square after process_end', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const httpTesting = TestBed.inject(HttpTestingController);
    const button = root.querySelector<HTMLButtonElement>('.play-button')!;
    socket.open();

    socket.receive({ type: 'process_end', data: {} });
    fixture.detectChanges();

    expect(button.disabled).toBe(true);
    expect(button.querySelector('span')?.textContent).toBe('■');
    expect(TestBed.inject(MarketDataSocketService).error()).toBeNull();
    button.click();
    httpTesting.expectNone(environment.replayControlUrl);
  });

  it('creates context charts from init messages and renders OHLCV and optional volume-profile updates', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    socket.open();
    initContextTarget(socket, '1', 'daily_context');
    socket.receive([
      {
        type: 'resource_init',
        data: {
          resource_type: 'ohlcv_volume_profile',
          target: 'context_chart/1',
          price_bin_count: '12',
          value_area_pct: 70,
        },
      },
      {
        type: 'resource_init',
        data: { resource_type: 'ohlcv_timeframe', target: 'context_chart/2', period: '1W' },
      },
      {
        type: 'resource_init',
        data: { resource_type: 'timeframe', target: 'main_chart/0', candle_seconds: 60, length: 10 },
      },
    ]);
    fixture.detectChanges();

    expect(service.contextCharts().map((chart) => chart.target)).toEqual([
      'context_chart/1',
      'context_chart/2',
    ]);
    expect(service.timeframes()).toEqual([60]);
    expect(root.querySelectorAll('app-context-chart')).toHaveLength(2);

    socket.receive([
      {
        type: 'market_update',
        data: {
          resource_type: 'ohlcv_timeframe',
          target: 'context_chart/1',
          interval: '5m',
          candles: [
            { time: 1_000, open: '100.25', high: '110.5', low: '95.5', close: '105.75' },
            { time: 2_000, open: '105.75', high: '115', low: '101', close: '112.5' },
          ],
        },
      },
      {
        type: 'market_update',
        data: {
          resource_type: 'ohlcv_volume_profile',
          target: 'context_chart/1',
          time: 2_000,
          bins: [{ low: '100', size: '2.5', volume: '25.75' }],
          poc: { price: '102.56', volume: '25.75' },
          value_area: { low: '98.5', high: '108.25' },
        },
      },
    ]);
    fixture.detectChanges();

    const chart = root.querySelector<HTMLElement>('app-context-chart [data-target="context_chart/1"]')!;
    expect(chart.querySelector('h2')?.textContent?.trim()).toBe('Daily Context');
    expect(chart.querySelector('.heading-note')?.textContent?.trim()).toBe('5m');
    expect(chart.querySelector('.context-ohlc-label')).toBeNull();
    expect(chart.querySelector('.profile-metrics')).toBeNull();
    expect(chart.querySelectorAll('.context-price-axis text')).toHaveLength(5);
    expect(chart.querySelector('.context-price-axis text')?.getAttribute('x')).toBe('244');
    expect(chart.querySelector('.context-price-axis text')?.getAttribute('text-anchor')).toBe('start');
    expect(
      Array.from(chart.querySelectorAll('.context-price-axis text')).every(
        (tick) => !tick.textContent?.includes('.'),
      ),
    ).toBe(true);
    expect(chart.querySelectorAll('.context-candles rect')).toHaveLength(2);
    expect(chart.querySelector('.context-profile rect')).toBeTruthy();
    expect(chart.querySelector('.context-poc')).toBeTruthy();
    expect(chart.querySelector('svg')?.getAttribute('viewBox')).toBe('0 0 280 120');
    expect(chart.querySelectorAll('.context-time-axis text')).toHaveLength(2);
    expect(chart.querySelector('.context-time-axis text')?.getAttribute('text-anchor')).toBe('start');
    expect(chart.querySelectorAll('.context-time-axis text')[1]?.getAttribute('text-anchor')).toBe('end');
    expect(chart.querySelector('.context-poc-label')?.textContent?.trim()).toBe('POC 102.6');
    expect(chart.querySelector('.context-poc title')?.textContent).toBe('POC 102.6 · Volume 25.75');
    expect(chart.querySelector('.context-current-price')).toBeTruthy();
    expect(chart.querySelector('.context-current-price-label')?.textContent?.trim())
      .toBe('Price 112.5');
    expect(Number(chart.querySelector('.context-candles line')!.getAttribute('x1'))).toBe(66);
    expect(
      chart
        .querySelector('.context-candles')!
        .compareDocumentPosition(chart.querySelector('.context-profile')!) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(service.contextCharts()[0].candles[0].open).toBe(100.25);
    expect(service.contextCharts()[0].volumeProfile?.bins[0].volume).toBe(25.75);

    socket.receive({
      type: 'market_update',
      data: {
        resource_type: 'ohlcv_volume_profile',
        target: 'context_chart/1',
        time: 3_000,
        bins: [],
        poc: null,
        value_area: null,
      },
    });
    fixture.detectChanges();
    expect(chart.querySelector('.context-profile rect')).toBeNull();
  });

  it('renders Volume Delta and CVD only after their individual resource init messages', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    socket.receive({
      type: 'resource_init',
      data: { resource_type: 'timeframe', target: 'main_chart/0', candle_seconds: 60, length: 100 },
    });
    fixture.detectChanges();
    expect(root.querySelectorAll('app-oscillator-panel')).toHaveLength(0);

    socket.receive({
      type: 'market_update',
      data: { resource_type: 'volume_delta', target: 'main_chart/0', time: 1_000, value: '3' },
    });
    fixture.detectChanges();
    expect(root.querySelectorAll('app-oscillator-panel')).toHaveLength(0);

    socket.receive({
      type: 'resource_init',
      data: { resource_type: 'cvd', target: 'main_chart/0', length: 100 },
    });
    fixture.detectChanges();
    expect(Array.from(root.querySelectorAll('app-oscillator-panel h2'), (heading) => heading.textContent?.trim())).toEqual(['CVD']);

    socket.receive({
      type: 'resource_init',
      data: { resource_type: 'volume_delta', target: 'main_chart/0', length: 100 },
    });
    fixture.detectChanges();
    expect(Array.from(root.querySelectorAll('app-oscillator-panel h2'), (heading) => heading.textContent?.trim())).toEqual(['Volume Delta', 'CVD']);
  });

  it('closes replay settings and the dashboard menu when clicking elsewhere', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;

    root.querySelector<HTMLButtonElement>('.auto-stop-settings-button')!.click();
    fixture.detectChanges();
    expect(root.querySelector('.auto-stop-settings')).toBeTruthy();

    root.querySelector<HTMLElement>('.session-summary')!.click();
    fixture.detectChanges();
    expect(root.querySelector('.auto-stop-settings')).toBeNull();

    root.querySelector<HTMLButtonElement>('.menu-button')!.click();
    fixture.detectChanges();
    expect(root.querySelector('.dashboard-menu')).toBeTruthy();

    root.querySelector<HTMLElement>('.session-summary')!.click();
    fixture.detectChanges();
    expect(root.querySelector('.dashboard-menu')).toBeNull();
  });

  it('collapses and reopens each sidebar independently', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;

    root.querySelector<HTMLButtonElement>('[aria-label="Collapse left sidebar"]')!.click();
    fixture.detectChanges();
    expect(root.querySelector('[aria-label="Expand left sidebar"]')).toBeTruthy();
    expect(root.querySelector('[aria-label="Collapse right sidebar"]')).toBeTruthy();

    root.querySelector<HTMLButtonElement>('[aria-label="Expand left sidebar"]')!.click();
    root.querySelector<HTMLButtonElement>('[aria-label="Collapse right sidebar"]')!.click();
    fixture.detectChanges();
    expect(root.querySelector('[aria-label="Collapse left sidebar"]')).toBeTruthy();
    expect(root.querySelector('[aria-label="Expand right sidebar"]')).toBeTruthy();
  });

  it('opens the dashboard menu and enables report export at progress 2', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const menuButton = root.querySelector<HTMLButtonElement>('.menu-button')!;

    menuButton.click();
    fixture.detectChanges();

    expect(menuButton.getAttribute('aria-expanded')).toBe('true');
    expect(root.querySelector('.dashboard-menu')).toBeTruthy();
    expect(root.querySelector<HTMLButtonElement>('.dashboard-menu-item')?.disabled).toBe(true);
    expect(root.querySelector('[aria-label="Collapse left sidebar"]')).toBeTruthy();

    socket.receive({
      type: 'session_start',
      data: {
        strategy_name: 'Momentum Strategy',
        session_number: '1',
        symbol: 'ETHUSDT',
        progress: '1/20',
      },
    });
    fixture.detectChanges();
    expect(root.querySelector<HTMLButtonElement>('.dashboard-menu-item')?.disabled).toBe(true);

    socket.receive({
      type: 'session_start',
      data: {
        strategy_name: 'Momentum Strategy',
        session_number: '2',
        symbol: 'ETHUSDT',
        progress: '2/20',
      },
    });
    fixture.detectChanges();
    expect(root.querySelector<HTMLButtonElement>('.dashboard-menu-item')?.disabled).toBe(false);
  });

  it('downloads the reports ZIP and displays an export conflict error', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.receive({
      type: 'session_start',
      data: {
        strategy_name: 'Momentum Strategy',
        session_number: '2',
        symbol: 'ETHUSDT',
        progress: '2/20',
      },
    });
    fixture.detectChanges();

    const createObjectURL = vi.fn(() => 'blob:reports');
    const revokeObjectURL = vi.fn();
    const MockURL = class extends URL {
      static override createObjectURL = createObjectURL;
      static override revokeObjectURL = revokeObjectURL;
    };
    vi.stubGlobal('URL', MockURL);
    const downloadedFilenames: string[] = [];
    const linkClick = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(function (this: HTMLAnchorElement) {
        downloadedFilenames.push(this.download);
      });
    vi.stubGlobal(
      'fetch',
      vi.fn()
        .mockResolvedValueOnce(
          new Response(new Blob(['zip']), {
            headers: { 'Content-Disposition': 'attachment; filename="reports-1.zip"' },
          }),
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ error: 'Report files are not ready for export' }), {
            status: 409,
            headers: { 'Content-Type': 'application/json' },
          }),
        ),
    );

    root.querySelector<HTMLButtonElement>('.menu-button')!.click();
    fixture.detectChanges();
    root.querySelector<HTMLButtonElement>('.dashboard-menu-item')!.click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fetch).toHaveBeenNthCalledWith(1, environment.reportExportUrl);
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(linkClick).toHaveBeenCalledOnce();
    expect(downloadedFilenames).toEqual(['reports-1.zip']);
    expect(root.querySelector('.dashboard-menu')).toBeNull();

    root.querySelector<HTMLButtonElement>('.menu-button')!.click();
    fixture.detectChanges();
    root.querySelector<HTMLButtonElement>('.dashboard-menu-item')!.click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fetch).toHaveBeenNthCalledWith(2, environment.reportExportUrl);
    expect(root.querySelector('[role="alert"]')?.textContent).toBe(
      'Report files are not ready for export',
    );
    expect(revokeObjectURL).not.toHaveBeenCalled();
  });

  it('formats arbitrary backend candle intervals without rounding', () => {
    expect(formatTimeframe(60)).toBe('1m');
    expect(formatTimeframe(3_600)).toBe('1h');
    expect(formatTimeframe(30)).toBe('30s');
    expect(formatTimeframe(70)).toBe('1m-10s');
    expect(formatTimeframe(3_660)).toBe('1h-1m');
    expect(formatTimeframe(3_670)).toBe('1h-1m-10s');
  });

  it('selects the corresponding initialized target without sending client messages', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    initTarget(socket, 'main_chart/0', 60);
    initTarget(socket, 'main_chart/1', 300);
    const chart = root.querySelector<SVGSVGElement>('.price-chart-svg')!;
    socket.receive(message(1_000));
    fixture.detectChanges();
    expect(root.querySelectorAll('.timeframe-controls button')).toHaveLength(2);
    expect(root.querySelectorAll('app-oscillator-panel h2')[0]?.textContent).toBe('Volume Delta');
    expect(root.querySelectorAll('app-oscillator-panel h2')[1]?.textContent).toBe('CVD');
    expect(root.querySelectorAll('.candles > g').length).toBe(1);

    for (const [index, timeframe] of ([60, 300] as Timeframe[]).entries()) {
      root.querySelector<HTMLButtonElement>(`.timeframe-controls button:nth-child(${index + 1})`)!.click();
      fixture.detectChanges();
      expect(chart.getAttribute('data-timeframe')).toBe(String(timeframe));
      expect(
        root.querySelector(`.timeframe-controls button:nth-child(${index + 1})`)?.getAttribute('aria-pressed'),
      ).toBe('true');
    }

    await waitForDisplayUpdate();
    fixture.detectChanges();
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(root.querySelectorAll('.candles > g').length).toBe(0);
    expect(socket.sent).toEqual([]);
  });

  it('creates timeframe choices dynamically from non-standard init intervals', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    initTarget(socket, 'main_chart/0', 30);
    initTarget(socket, 'main_chart/1', 70);
    initTarget(socket, 'main_chart/2', 3_670);
    fixture.detectChanges();

    expect(
      Array.from(root.querySelectorAll('.timeframe-controls button'), (button) =>
        button.textContent?.trim(),
      ),
    ).toEqual(['30s', '1m-10s', '1h-1m-10s']);
    root.querySelector<HTMLButtonElement>('.timeframe-controls button:nth-child(3)')!.click();
    fixture.detectChanges();
    expect(root.querySelector('.chart-symbol')).toBeNull();
    expect(
      root.querySelector('.timeframe-controls button:nth-child(3)')?.getAttribute('aria-pressed'),
    ).toBe('true');
    expect(root.querySelector<SVGSVGElement>('.price-chart-svg')?.getAttribute('data-timeframe')).toBe(
      '3670',
    );
  });

  it('uses indicator analyzer settings in the panel names', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    initTarget(socket, 'main_chart/0', 60, 100, true, 5.25);
    socket.receive({
      type: 'resource_init',
      data: {
        resource_type: 'cvd',
        target: 'main_chart/0',
        length: 100,
        big_trades: true,
        big_trades_pct: 2.5,
      },
    });
    await waitForDisplayUpdate();
    fixture.detectChanges();

    expect(root.querySelectorAll('app-oscillator-panel h2')[0]?.textContent).toContain(
      'Volume Delta (Big Trades 5.25%)',
    );
    expect(root.querySelectorAll('app-oscillator-panel h2')[1]?.textContent).toContain(
      'CVD (Big Trades 2.5%)',
    );
  });

  it('keeps separate candle and indicator series for each configured target', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    socket.open();
    initTarget(socket, 'main_chart/0', 60);
    initTarget(socket, 'main_chart/1', 300);
    fixture.detectChanges();

    root.querySelector<HTMLButtonElement>('.timeframe-controls button:nth-child(2)')!.click();
    fixture.detectChanges();
    socket.receive(message(1_000, { target: 'main_chart/1' }));
    socket.receive(message(2_000, { target: 'main_chart/1', close: 106, volumeDelta: 4, cvd: 7 }));

    root.querySelector<HTMLButtonElement>('.timeframe-controls button:nth-child(1)')!.click();
    fixture.detectChanges();
    socket.receive(message(3_000));
    socket.receive(message(4_000, { close: 108 }));

    root.querySelector<HTMLButtonElement>('.timeframe-controls button:nth-child(2)')!.click();
    fixture.detectChanges();
    await waitForDisplayUpdate();
    fixture.detectChanges();
    expect(service.series().candles.map((candle) => candle.timestamp)).toEqual([1_000, 2_000]);
    expect(root.querySelectorAll('.candles > g')).toHaveLength(2);
    expect(service.series().volumeDelta.map((point) => point.timestamp)).toEqual([1_000, 2_000]);
    expect(service.series().cvd.map((point) => point.timestamp)).toEqual([1_000, 2_000]);

    socket.receive(message(2_000, { target: 'main_chart/1', close: 111, volumeDelta: -2, cvd: 9 }));
    socket.receive(message(5_000, { target: 'main_chart/1', close: 112, volumeDelta: 6, cvd: 15 }));
    await waitForDisplayUpdate();
    fixture.detectChanges();
    expect(service.series().candles).toHaveLength(3);
    expect(service.series().candles[1].close).toBe(111);
    expect(service.series().volumeDelta.map((point) => point.value)).toEqual([3, -2, 6]);
    expect(service.series().cvd.map((point) => point.value)).toEqual([3, 9, 15]);

    expect(service.series().candles.map((candle) => candle.close)).toEqual([105, 111, 112]);
    expect(root.querySelectorAll('.candles > g')).toHaveLength(3);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it('coalesces rapid market updates to 30 display updates per second', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    socket.open();
    initTarget(socket);
    socket.receive(message(1_000));
    const firstDisplayedSeries = service.series();

    socket.receive(message(2_000));
    socket.receive(message(3_000));
    expect(service.series()).toBe(firstDisplayedSeries);

    await waitForDisplayUpdate();
    expect(service.series().candles.map((candle) => candle.timestamp)).toEqual([
      1_000, 2_000, 3_000,
    ]);
    expect(service.series().volumeDelta.map((point) => point.timestamp)).toEqual([
      1_000, 2_000, 3_000,
    ]);
    fixture.destroy();
    TestBed.resetTestingModule();
  });

  it('parses decimal strings and upserts independent market updates by timestamp', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    socket.open();
    initTarget(socket, 'main_chart/0', 60, 2);

    expect(root.querySelectorAll('.candles > g').length).toBe(0);
    expect(root.textContent).toContain('Waiting for market data');

    socket.receive(message(1_000));
    await waitForDisplayUpdate();
    fixture.detectChanges();
    expect(service.series().candles).toHaveLength(1);
    expect(service.series().volumeDelta).toEqual([{ timestamp: 1_000, value: 3 }]);
    expect(service.series().cvd).toEqual([{ timestamp: 1_000, value: 3 }]);
    expect(root.querySelectorAll('.candles > g').length).toBe(1);
    expect(root.querySelectorAll('.delta-bars rect').length).toBe(1);

    // Same timestamps replace their existing candle and indicator points.
    socket.receive(message(1_000, { high: 120, close: 118, volumeDelta: 5, cvd: 5 }));
    await waitForDisplayUpdate();
    fixture.detectChanges();
    expect(service.series().candles).toEqual([
      { timestamp: 1_000, open: 100, high: 120, low: 95, close: 118, volume: 0 },
    ]);
    expect(service.series().cvd).toEqual([{ timestamp: 1_000, value: 5 }]);

    // A new opening timestamp appends and leaves the previous candle untouched.
    socket.receive(message(2_000, { open: 118, close: 112, volumeDelta: -2, cvd: 3 }));
    await waitForDisplayUpdate();
    fixture.detectChanges();
    expect(service.series().candles).toHaveLength(2);
    expect(service.series().candles[0].close).toBe(118);
    expect(service.series().volumeDelta.map((point) => point.timestamp)).toEqual([1_000, 2_000]);
    expect(service.series().cvd.map((point) => point.value)).toEqual([5, 3]);
    expect(root.querySelectorAll('.candles > g').length).toBe(2);

    // Out-of-order updates are sorted, and new updates roll the oldest points out of the window.
    socket.receive(message(500, { close: 99 }));
    await waitForDisplayUpdate();
    fixture.detectChanges();
    expect(service.series().candles.map((candle) => candle.timestamp)).toEqual([1_000, 2_000]);
    socket.receive(message(3_000));
    await waitForDisplayUpdate();
    fixture.detectChanges();
    expect(service.series().candles.map((candle) => candle.timestamp)).toEqual([2_000, 3_000]);
    expect(service.series().volumeDelta.map((point) => point.timestamp)).toEqual([2_000, 3_000]);
    expect(service.series().cvd.map((point) => point.timestamp)).toEqual([2_000, 3_000]);
    expect(service.series().volumeDelta).toHaveLength(2);
    expect(service.series().cvd).toHaveLength(2);
  });

  it('maps initialization and market updates by target and resource type', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    socket.open();

    socket.receive([
      { type: 'resource_init', data: { resource_type: 'volume_delta', target: 'main_chart/1', length: 100, big_trades: false, big_trades_pct: 0 } },
      { type: 'resource_init', data: { resource_type: 'cvd', target: 'main_chart/1', length: 100, big_trades: false, big_trades_pct: 0 } },
      { type: 'resource_init', data: { resource_type: 'timeframe', target: 'main_chart/1', candle_seconds: 300, length: 100 } },
      { type: 'resource_init', data: { resource_type: 'cvd', target: 'main_chart/0', length: 100, big_trades: false, big_trades_pct: 0 } },
      { type: 'resource_init', data: { resource_type: 'timeframe', target: 'main_chart/0', candle_seconds: 60, length: 100 } },
      { type: 'resource_init', data: { resource_type: 'volume_delta', target: 'main_chart/0', length: 100, big_trades: false, big_trades_pct: 0 } },
    ]);
    socket.receive([
      { type: 'market_update', data: { resource_type: 'cvd', target: 'main_chart/0', time: 1_700_000_000_000, value: '1.25' } },
      { type: 'market_update', data: { resource_type: 'volume_delta', target: 'main_chart/0', time: 1_700_000_000_000, value: '1.25' } },
    ]);
    socket.receive({
      type: 'market_update',
      data: {
        resource_type: 'timeframe',
        target: 'main_chart/0',
        time: 1_700_000_000_000,
        open: '100.2500',
        high: '101.0000',
        low: '99.7500',
        close: '100.5000',
      },
    });
    await waitForDisplayUpdate();
    fixture.detectChanges();

    expect(service.series().candles).toEqual([
      {
        timestamp: 1_700_000_000_000,
        open: 100.25,
        high: 101,
        low: 99.75,
        close: 100.5,
        volume: 0,
      },
    ]);
    expect(service.series().volumeDelta).toEqual([
      { timestamp: 1_700_000_000_000, value: 1.25 },
    ]);
    expect(service.series().cvd).toEqual([{ timestamp: 1_700_000_000_000, value: 1.25 }]);
    expect(root.querySelectorAll('.candles > g')).toHaveLength(1);
    expect(root.querySelector('.chart-tooltip')).toBeNull();
    root.querySelector<HTMLButtonElement>('.chart-indicator-toggle')!.click();
    fixture.detectChanges();
    expect(root.querySelector('.chart-tooltip')?.textContent).toContain('OHLC');
    expect(root.querySelector('.chart-tooltip')?.textContent).not.toMatch(/Bullish|Bearish/);
    expect(root.querySelectorAll('.delta-bars rect')).toHaveLength(1);
    expect(root.querySelector('.oscillator-chart')).toBeTruthy();
    expect(service.error()).toBeNull();
  });

  it('rejects malformed messages without changing the series', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    socket.open();
    initTarget(socket);

    socket.receive({
      type: 'market_update',
      data: {
        resource_type: 'timeframe',
        target: 'main_chart/0',
        time: 1_000,
        open: '1',
        high: '2',
        low: '0',
        close: '3',
      },
    });
    await waitForDisplayUpdate();
    socket.receive('not json');
    socket.receive({
      type: 'market_update',
      data: { resource_type: 'cvd', target: 'main_chart/0', time: 1_000, value: 'x' },
    });
    expect(service.series().candles).toHaveLength(1);
    expect(service.error()).toContain('invalid');
  });

  it('shows connection state and never falls back to synthetic data', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];

    expect(root.querySelector('.topbar .connection-indicator .connection-status')?.textContent).toContain('CONNECTING');
    expect(root.querySelector('.chart-toolbar')).toBeNull();
    socket.onerror?.();
    fixture.detectChanges();
    expect(root.querySelector('.topbar .connection-indicator .connection-status')?.textContent).toContain('unavailable');
    expect(root.querySelectorAll('.candles > g').length).toBe(0);
  });

  it('reconnects after a disconnect and keeps the in-memory chart while waiting', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const firstSocket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    firstSocket.open();
    initTarget(firstSocket);
    firstSocket.receive(message(1_000));

    firstSocket.closeFromServer();
    expect(service.status()).toBe('closed');
    await new Promise((resolve) => setTimeout(resolve, 550));

    expect(FakeWebSocket.instances).toHaveLength(2);
    const secondSocket = FakeWebSocket.instances[1];
    expect(service.status()).toBe('connecting');
    secondSocket.open();
    expect(service.status()).toBe('connected');
    expect(service.series().candles.map((candle) => candle.timestamp)).toEqual([1_000]);

    fixture.destroy();
    TestBed.resetTestingModule();
  });

  it('closes the socket and detaches listeners when the service is destroyed', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const socket = FakeWebSocket.instances[0];

    fixture.destroy();
    TestBed.resetTestingModule();

    expect(socket.closed).toBe(true);
    expect(socket.onmessage).toBeNull();
    expect(socket.onopen).toBeNull();
  });

  it('keeps Play/Pause visible and inert', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    socket.open();
    initTarget(socket);
    socket.receive(message(1_000));
    const button = root.querySelector<HTMLButtonElement>('.play-button')!;
    const before = service.series();
    const sentBefore = socket.sent.length;

    button.click();
    fixture.detectChanges();
    socket.receive(message(2_000));
    await waitForDisplayUpdate();

    expect(button).toBeTruthy();
    expect(service.series()).not.toBe(before);
    expect(service.series().candles).toHaveLength(2);
    expect(socket.sent).toHaveLength(sentBefore);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
  it('collapses each oscillator independently', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    initTarget(socket);
    fixture.detectChanges();

    root.querySelector<HTMLButtonElement>('[aria-label="Collapse Volume Delta"]')!.click();
    fixture.detectChanges();

    expect(root.querySelector('[aria-label="Expand Volume Delta"]')).toBeTruthy();
    expect(root.querySelector('[aria-label="Collapse CVD"]')).toBeTruthy();
    expect(root.querySelectorAll('.oscillator-chart').length).toBe(1);
  });

  it('does not show default equity curves or statistics before an analysis is initialized', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const select = root.querySelector<HTMLSelectElement>('.performance-view-select')!;

    expect(select.value).toBe('');
    expect(select.options).toHaveLength(0);
    expect(root.querySelector('.equity-line')).toBeNull();
    expect(root.querySelector('.stats-grid')).toBeNull();
    expect(root.querySelector('.scope-switch')).toBeNull();
    expect(root.querySelector('.performance-panel h2')?.textContent?.trim()).toBe('Statistics');
    expect(root.querySelector('.performance-panel .panel-heading')?.contains(select)).toBe(true);
  });

  it('registers, updates, and resets analysis equity curves by target', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    const firstTarget = 'equity_curve/backtest_None';
    const secondTarget = 'equity_curve/live_ETHUSDT';
    socket.open();
    initTarget(socket);

    socket.receive([
      {
        type: 'market_update',
        data: {
          analysis_type: 'equity_curve',
          target: firstTarget,
          time: 1_700_000_000_000,
          equity: '999',
          starting_balance: '950.25',
        },
      },
      {
        type: 'analysis_init',
        data: { analysis_type: 'equity_curve', target: firstTarget, name: 'BTC Backtest' },
      },
      {
        type: 'analysis_init',
        data: { analysis_type: 'equity_curve', target: secondTarget, name: 'ETH Live' },
      },
      {
        type: 'analysis_update',
        data: {
          analysis_type: 'equity_curve',
          target: firstTarget,
          time: 1_700_000_000_000,
          equity: '1000.5',
          starting_balance: '950.25',
        },
      },
      {
        type: 'analysis_update',
        data: {
          analysis_type: 'equity_curve',
          target: firstTarget,
          time: 1_700_000_060_000,
          equity: '1010',
          starting_balance: '950.25',
        },
      },
      {
        type: 'analysis_update',
        data: {
          analysis_type: 'equity_curve',
          target: secondTarget,
          time: 1_700_000_000_000,
          equity: '500',
          starting_balance: '500',
        },
      },
    ]);
    fixture.detectChanges();

    const select = root.querySelector<HTMLSelectElement>('.performance-view-select')!;
    expect(Array.from(select.options, (option) => option.textContent?.trim())).toEqual([
      'BTC Backtest',
      'ETH Live',
    ]);
    expect(select.value).toBe('BTC Backtest');
    expect(service.analysisEquityCurves().map((curve) => curve.name)).toEqual([
      'BTC Backtest',
      'ETH Live',
    ]);
    expect(service.analysisEquityCurves()[0].points).toEqual([
      { timestamp: 1_700_000_000_000, value: 1000.5 },
      { timestamp: 1_700_000_060_000, value: 1010 },
    ]);

    select.value = 'ETH Live';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(select.value).toBe('ETH Live');

    select.value = 'BTC Backtest';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(root.querySelector('.equity-line')?.getAttribute('d')).toContain('L');
    expect(root.querySelector('.equity-grid text')?.getAttribute('x')).toBe('461');
    expect(root.querySelector('.equity-grid text')?.getAttribute('text-anchor')).toBe('start');
    const equityPath = root.querySelector('.equity-line')?.getAttribute('d') ?? '';
    const coordinates = [...equityPath.matchAll(/(?:M|L)([\d.]+) ([\d.]+)/g)];
    expect(coordinates[0][1]).toBe('0.00');
    expect(coordinates[coordinates.length - 1][1]).toBe('455.00');
    const startingLine = root.querySelector('.starting-equity-line');
    const currentLine = root.querySelector('.current-equity-line');
    expect(Number(startingLine?.getAttribute('y1'))).toBeCloseTo(124.73, 1);
    expect(currentLine?.getAttribute('y1')).toBe(coordinates[coordinates.length - 1][2]);
    expect(root.querySelector('.starting-equity-label')?.textContent?.trim())
      .toBe('Starting Balance $950.3');
    expect(root.querySelector('.current-equity-label')?.textContent?.trim())
      .toBe('Equity $1,010.0');
    const startingEquityLabel = root.querySelector<HTMLElement>('.starting-equity-label');
    expect(Number.parseFloat(startingEquityLabel?.style.top ?? '0'))
      .toBeCloseTo(((6 + (Number(startingLine?.getAttribute('y1')) / 184) * 180.3) / 190.3) * 100);
    const currentEquityLabel = root.querySelector<HTMLElement>('.current-equity-label');
    expect(currentEquityLabel?.tagName).toBe('SPAN');
    expect(Number.parseFloat(currentEquityLabel?.style.top ?? '0'))
      .toBeCloseTo(((6 + (Number(currentLine?.getAttribute('y1')) / 184) * 180.3) / 190.3) * 100);

    socket.receive({
      type: 'analysis_update',
      data: {
        analysis_type: 'equity_curve',
        target: firstTarget,
        time: 1_700_000_060_000,
        equity: '1010',
        starting_balance: null,
      },
    });
    fixture.detectChanges();
    expect(root.querySelector('.starting-equity-line')).toBeNull();
    expect(root.querySelector('.starting-equity-label')).toBeNull();

    socket.receive({
      type: 'analysis_session_start',
      data: { analysis_type: 'equity_curve', target: firstTarget },
    });
    fixture.detectChanges();
    expect(service.analysisEquityCurves()[0].points).toEqual([]);
    expect(root.querySelector('.equity-line')?.getAttribute('d')).toBe('');
    expect(root.querySelector('.starting-equity-line')).toBeNull();
    expect(root.querySelector('.current-equity-line')).toBeNull();
    expect(root.querySelector('.current-equity-label')).toBeNull();
    expect(service.analysisEquityCurves()[1].points).toEqual([
      { timestamp: 1_700_000_000_000, value: 500 },
    ]);
  });

  it('registers statistics and links them to equity curves by name', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const statisticsTarget = 'statistics/session_None';
    const equityTarget = 'equity_curve/session_None';
    const pairedStatisticsTarget = 'statistics/full_run_None';
    const pairedEquityTarget = 'equity_curve/full_run_None';
    socket.open();

    socket.receive([
      {
        type: 'analysis_init',
        data: { analysis_type: 'statistics', target: statisticsTarget, name: 'Session Pair' },
      },
      {
        type: 'analysis_update',
        data: {
          analysis_type: 'statistics',
          target: statisticsTarget,
          statistics: {
            total_trades: 12,
            winrate: 0.5,
            pnl: 42.109,
            roi: 0,
            max_drawdown: 0.01234,
            average_trade_duration: 3661,
          },
        },
      },
    ]);
    fixture.detectChanges();

    const select = root.querySelector<HTMLSelectElement>('.performance-view-select')!;
    const statisticRow = (label: string): HTMLElement =>
      Array.from(root.querySelectorAll<HTMLElement>('.stats-grid div')).find(
        (row) => row.querySelector('dt')?.textContent?.trim() === label,
      )!;
    expect(Array.from(select.options, (option) => option.textContent?.trim())).toEqual([
      'Session Pair',
    ]);
    expect(select.value).toBe('Session Pair');
    expect(root.querySelector('.stats-grid')?.textContent).toContain('Total Trades');
    expect(statisticRow('Win Rate').querySelector('dd')?.textContent).toBe('50%');
    expect(statisticRow('Win Rate').querySelector('dd')?.classList.contains('positive')).toBe(true);
    expect(statisticRow('PnL').querySelector('dd')?.textContent).toBe('$42.11');
    expect(statisticRow('PnL').querySelector('dd')?.classList.contains('positive')).toBe(true);
    expect(statisticRow('ROI').querySelector('dd')?.textContent).toBe('0%');
    expect(statisticRow('ROI').querySelector('dd')?.classList.contains('positive')).toBe(true);
    expect(statisticRow('Max Drawdown').querySelector('dd')?.textContent).toBe('1.23%');
    expect(statisticRow('Average Trade Duration').querySelector('dd')?.textContent).toBe(
      '1:01:01',
    );
    expect(root.querySelector('app-equity-curve')).toBeNull();

    socket.receive({
      type: 'analysis_update',
      data: {
        analysis_type: 'statistics',
        target: statisticsTarget,
        statistics: {
          winrate: null,
          average_trade_duration: null,
        },
      },
    });
    fixture.detectChanges();
    expect(statisticRow('Win Rate').querySelector('dd')?.textContent).toBe('—');
    expect(statisticRow('Average Trade Duration').querySelector('dd')?.textContent).toBe('—');

    socket.receive({
      type: 'analysis_init',
      data: { analysis_type: 'equity_curve', target: equityTarget, name: 'Session Pair' },
    });
    socket.receive({
      type: 'analysis_update',
      data: {
        analysis_type: 'equity_curve',
        target: equityTarget,
        time: 1_700_000_000_000,
        equity: '100',
        starting_balance: '100',
      },
    });
    fixture.detectChanges();

    expect(Array.from(select.options, (option) => option.textContent?.trim())).toEqual([
      'Session Pair',
    ]);
    expect(root.querySelector('app-equity-curve')).toBeTruthy();
    expect(root.querySelector('.stats-grid')?.textContent).toContain('Win Rate');

    socket.receive([
      {
        type: 'analysis_init',
        data: { analysis_type: 'equity_curve', target: pairedEquityTarget, name: 'Full Run' },
      },
      {
        type: 'analysis_init',
        data: { analysis_type: 'statistics', target: pairedStatisticsTarget, name: 'Full Run' },
      },
      {
        type: 'analysis_update',
        data: {
          analysis_type: 'statistics',
          target: pairedStatisticsTarget,
          statistics: {
            total_trades: 3,
            winrate: 0.499,
            pnl: -5.006,
            roi: -0.01556,
            max_drawdown: 0.03456,
            average_trade_duration: 90061,
          },
        },
      },
    ]);
    fixture.detectChanges();

    expect(Array.from(select.options, (option) => option.textContent?.trim())).toEqual([
      'Session Pair',
      'Full Run',
    ]);
    expect(select.value).toBe('Session Pair');

    select.value = 'Full Run';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(root.querySelector('.stats-grid')?.textContent).toContain('Total Trades');
    expect(root.querySelector('.stats-grid')?.textContent).toContain('3');
    expect(statisticRow('Win Rate').querySelector('dd')?.textContent).toBe('49.9%');
    expect(statisticRow('Win Rate').querySelector('dd')?.classList.contains('negative')).toBe(true);
    expect(statisticRow('PnL').querySelector('dd')?.textContent).toBe('-$5.01');
    expect(statisticRow('PnL').querySelector('dd')?.classList.contains('negative')).toBe(true);
    expect(statisticRow('ROI').querySelector('dd')?.textContent).toBe('-1.56%');
    expect(statisticRow('ROI').querySelector('dd')?.classList.contains('negative')).toBe(true);
    expect(statisticRow('Max Drawdown').querySelector('dd')?.textContent).toBe('3.46%');
    expect(statisticRow('Average Trade Duration').querySelector('dd')?.textContent).toBe(
      '25:01:01',
    );
    expect(root.querySelector('app-equity-curve')).toBeTruthy();
  });

  it('logs accepted and rejected statistics init and update messages', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const socket = FakeWebSocket.instances[0];
    const acceptedLog = vi.spyOn(console, 'info').mockImplementation(() => undefined);
    const rejectedLog = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    const acceptedInit = {
      type: 'analysis_init',
      data: { analysis_type: 'statistics', target: 'statistics/session_None', name: 'Session Pair' },
    };
    const rejectedInit = {
      type: 'analysis_init',
      data: { analysis_type: 'statistics', target: '', name: 'Rejected' },
    };
    const acceptedUpdate = {
      type: 'analysis_update',
      data: {
        analysis_type: 'statistics',
        target: 'statistics/session_None',
        statistics: { total_trades: 10, pnl: '12.5' },
      },
    };
    const rejectedUpdate = {
      type: 'analysis_update',
      data: {
        analysis_type: 'statistics',
        target: 'statistics/session_None',
        statistics: { total_trades: [] },
      },
    };

    try {
      socket.open();
      socket.receive([acceptedInit, rejectedInit, acceptedUpdate, rejectedUpdate]);

      expect(acceptedLog).toHaveBeenCalledWith(
        '[MarketDataSocketService] Accepted statistics init message',
        acceptedInit,
      );
      expect(rejectedLog).toHaveBeenCalledWith(
        '[MarketDataSocketService] Rejected statistics init message',
        rejectedInit,
        'target must be a non-empty string',
      );
      expect(acceptedLog).toHaveBeenCalledWith(
        '[MarketDataSocketService] Accepted statistics update message',
        acceptedUpdate,
      );
      expect(rejectedLog).toHaveBeenCalledWith(
        '[MarketDataSocketService] Rejected statistics update message',
        rejectedUpdate,
        'statistics must contain only scalar values',
      );
    } finally {
      acceptedLog.mockRestore();
      rejectedLog.mockRestore();
    }
  });

  it('renders OHLC candles without a main-chart volume indicator and aligns all chart plots', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const chart = root.querySelector<SVGSVGElement>('.price-chart-svg')!;
    socket.open();
    initTarget(socket);
    socket.receive(message(1_000));
    socket.receive(message(2_000, { open: 105, close: 98, low: 90 }));
    await waitForDisplayUpdate();
    fixture.detectChanges();

    expect(root.querySelectorAll('.candles .candle-body').length).toBe(2);
    expect(root.querySelectorAll('.candles .candle-wick').length).toBe(2);
    expect(root.querySelector('.volume-bars, .volume-grid')).toBeNull();
    expect(root.querySelectorAll('app-oscillator-panel .delta-bars rect')).toHaveLength(2);
    expect(root.querySelectorAll('app-oscillator-panel .cvd-line')).toHaveLength(1);

    const mainBounds = root.querySelector<SVGLineElement>('.price-grid line')!;
    const deltaBounds = root.querySelector<SVGLineElement>('app-oscillator-panel .oscillator-grid line')!;
    const cvdBounds = root.querySelectorAll<SVGLineElement>('app-oscillator-panel .oscillator-grid line')[3];
    expect([mainBounds.getAttribute('x1'), mainBounds.getAttribute('x2')]).toEqual([
      deltaBounds.getAttribute('x1'),
      deltaBounds.getAttribute('x2'),
    ]);
    expect([mainBounds.getAttribute('x1'), mainBounds.getAttribute('x2')]).toEqual([
      cvdBounds.getAttribute('x1'),
      cvdBounds.getAttribute('x2'),
    ]);

    const candleX = Number(root.querySelector<SVGLineElement>('.candles .candle-wick')!.getAttribute('x1'));
    const deltaBar = root.querySelector<SVGRectElement>('.delta-bars rect')!;
    const deltaX = Number(deltaBar.getAttribute('x')) + Number(deltaBar.getAttribute('width')) / 2;
    const cvdLine = root.querySelector<SVGLineElement>('.cvd-line')!;
    const cvdX = Number(cvdLine.getAttribute('x1'));
    expect(deltaX).toBeCloseTo(candleX);
    expect(cvdX).toBeCloseTo(candleX);

    Object.defineProperty(chart, 'getBoundingClientRect', {
      value: () => ({ left: 0, top: 0, width: 1000, height: 470 }),
    });
    root.querySelector<HTMLButtonElement>('.chart-indicator-toggle')!.click();
    fixture.detectChanges();
    const originalTooltip = root.querySelector('.chart-tooltip')?.textContent;

    chart.dispatchEvent(new PointerEvent('pointermove', { clientX: 300, clientY: 120, bubbles: true }));
    fixture.detectChanges();
    expect(root.querySelector('.crosshair')).toBeTruthy();
    expect(originalTooltip?.trim()).toBe('OHLC');
    expect(root.querySelector('.chart-tooltip')?.textContent?.replace(/\s+/g, ' ').trim()).toBe(
      'O 100.0 H 110.0 L 95.0 C 105.0',
    );
  });

  it('keeps candle bodies separated when many candles are shown', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    initTarget(socket, 'main_chart/0', 60, 150);
    socket.receive(
      Array.from({ length: 150 }, (_, index) => message(1_000 + index * 60_000)[0]),
    );
    await waitForDisplayUpdate();
    fixture.detectChanges();

    const bodies = root.querySelectorAll<SVGRectElement>('.candles .candle-body');
    expect(bodies).toHaveLength(150);
    const firstBody = bodies[0];
    const secondBody = bodies[1];
    const firstRight = Number(firstBody.getAttribute('x')) + Number(firstBody.getAttribute('width'));
    expect(Number(firstBody.getAttribute('width'))).toBeLessThan(8);
    expect(Number(secondBody.getAttribute('x'))).toBeGreaterThan(firstRight);
  });

  it('renders backend Volume Delta and CVD values without recalculating them', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    initTarget(socket);
    // CVD is deliberately not the running sum of the deltas: it must be displayed as received.
    socket.receive(message(1_000, { volumeDelta: 4, cvd: 40 }));
    socket.receive(message(2_000, { volumeDelta: -6, cvd: -7 }));
    await waitForDisplayUpdate();
    fixture.detectChanges();

    const deltaBars = root.querySelectorAll<SVGRectElement>('.delta-bars rect');
    expect(Array.from(deltaBars, (bar) => Number(bar.getAttribute('data-value')))).toEqual([4, -6]);
    expect(root.querySelectorAll('.cvd-line')).toHaveLength(2);
    expect(root.querySelectorAll('.cvd-line.positive')).toHaveLength(1);
    expect(root.querySelectorAll('.cvd-line.negative')).toHaveLength(1);
    expect(root.querySelector('.cvd-points')).toBeNull();
  });

  it('resizes adjacent chart panels independently and preserves sizes across sidebar toggles', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const socket = FakeWebSocket.instances[0];
    socket.open();
    initTarget(socket);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const main = root.querySelector<HTMLElement>('.main-chart-panel')!;
    const [volumeDelta, cvd] = Array.from(root.querySelectorAll<HTMLElement>('app-oscillator-panel'));
    const initialCvdFlex = cvd.style.flex;

    expect(root.querySelectorAll('.chart-resize-handle').length).toBe(2);
    expect(main.style.flex).toBe('60 1 0px');
    expect(volumeDelta.style.flex).toBe('22 1 0px');
    expect(cvd.style.flex).toBe('18 1 0px');

    root.querySelector<HTMLElement>('.chart-resize-handle[aria-label^="Resize Main"]')!
      .dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }));
    fixture.detectChanges();
    expect(main.style.flex).not.toBe('60 1 0px');
    expect(volumeDelta.style.flex).not.toBe('22 1 0px');
    expect(cvd.style.flex).toBe(initialCvdFlex);

    const resizedMainFlex = main.style.flex;
    root.querySelector<HTMLElement>('.chart-resize-handle[aria-label^="Resize Volume"]')!
      .dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }));
    fixture.detectChanges();
    expect(main.style.flex).toBe(resizedMainFlex);
    expect(cvd.style.flex).not.toBe(initialCvdFlex);

    root.querySelector<HTMLButtonElement>('[aria-label="Collapse Volume Delta"]')!.click();
    fixture.detectChanges();
    expect(root.querySelectorAll('.chart-resize-handle').length).toBe(0);
    expect(volumeDelta.style.flex).toBe('0 0 38px');
    root.querySelector<HTMLButtonElement>('[aria-label="Expand Volume Delta"]')!.click();
    fixture.detectChanges();
    expect(root.querySelectorAll('.chart-resize-handle').length).toBe(2);
    expect(main.style.flex).toBe(resizedMainFlex);

    root.querySelector<HTMLButtonElement>('[aria-label="Collapse CVD"]')!.click();
    fixture.detectChanges();
    expect(root.querySelectorAll('.chart-resize-handle').length).toBe(1);
    root.querySelector<HTMLButtonElement>('[aria-label="Expand CVD"]')!.click();
    fixture.detectChanges();
    expect(root.querySelectorAll('.chart-resize-handle').length).toBe(2);

    const selectedFlex = [main.style.flex, volumeDelta.style.flex, cvd.style.flex];
    root.querySelector<HTMLButtonElement>('[aria-label="Collapse left sidebar"]')!.click();
    fixture.detectChanges();
    expect([main.style.flex, volumeDelta.style.flex, cvd.style.flex]).toEqual(selectedFlex);
  });

  it('collapses every sidebar panel independently', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    socket.open();
    initContextTarget(socket, '1', '1D');
    initContextTarget(socket, '2', '1W');
    initNewsTarget(socket);
    fixture.detectChanges();
    const panels = [
      { label: '1D context chart', content: 'app-context-chart:nth-of-type(1) .context-chart' },
      { label: '1W context chart', content: 'app-context-chart:nth-of-type(2) .context-chart' },
      { label: 'News', content: '.news-list' },
      { label: 'Statistics', content: '.performance-content' },
      { label: 'Positions', content: '.positions-panel .position-list' },
    ];

    for (const { label, content } of panels) {
      const collapseButton = root.querySelector<HTMLButtonElement>(`[aria-label="Collapse ${label} panel"]`)!;
      collapseButton.click();
      fixture.detectChanges();

      expect(collapseButton.getAttribute('aria-expanded')).toBe('false');
      expect(root.querySelector(`[aria-label="Expand ${label} panel"]`)).toBeTruthy();
      expect(root.querySelector(content)).toBeNull();
      for (const otherPanel of panels.filter((candidate) => candidate.label !== label)) {
        expect(root.querySelector(`[aria-label="Collapse ${otherPanel.label} panel"]`)?.getAttribute('aria-expanded')).toBe('true');
      }

      root.querySelector<HTMLButtonElement>(`[aria-label="Expand ${label} panel"]`)!.click();
      fixture.detectChanges();
      expect(root.querySelector(`[aria-label="Collapse ${label} panel"]`)?.getAttribute('aria-expanded')).toBe('true');
      expect(root.querySelector(content)).toBeTruthy();
    }
  });

  it('creates optional resource displays from init messages and renders their updates', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    socket.open();
    initTarget(socket);

    socket.receive([
      {
        type: 'market_update',
        data: { resource_type: 'volume_profile', target: 'main_chart/0', bins: [], poc: null, value_area: null },
      },
      { type: 'market_update', data: { resource_type: 'open_interest', target: 'main_chart/0', time: 1_000, value: '99' } },
      { type: 'market_update', data: { resource_type: 'big_trades', target: 'main_chart/0', trades: [] } },
    ]);
    fixture.detectChanges();
    expect(root.querySelector('app-oscillator-panel h2')?.textContent).not.toContain('Open Interest');
    expect(root.querySelector('.volume-profile')).toBeNull();
    expect(root.querySelector('.chart-indicators')).toBeTruthy();
    expect(root.querySelector('.chart-indicator-toggle')?.getAttribute('aria-expanded')).toBe('false');
    expect(root.querySelector('.chart-tooltip')).toBeNull();
    expect(service.dynamicResources()).toEqual([]);

    socket.receive([
      { type: 'resource_init', data: { resource_type: 'volume_profile', target: 'main_chart/0', price_bin_count: 24, value_area_pct: 70 } },
      { type: 'resource_init', data: { resource_type: 'open_interest', target: 'main_chart/0', length: 100 } },
      { type: 'resource_init', data: { resource_type: 'big_trades', target: 'main_chart/0', top_pct: 5 } },
    ]);
    fixture.detectChanges();
    expect(root.querySelectorAll('app-oscillator-panel h2')).toHaveLength(3);
    expect(root.querySelectorAll('app-oscillator-panel h2')[2]?.textContent).toContain('Open Interest');
    const indicatorToggle = root.querySelector<HTMLButtonElement>('.chart-indicator-toggle')!;
    expect(indicatorToggle.getAttribute('aria-expanded')).toBe('false');
    expect(root.querySelector('.chart-tooltip')).toBeNull();
    expect(root.querySelectorAll('.chart-indicator')).toHaveLength(0);
    indicatorToggle.click();
    fixture.detectChanges();
    expect(indicatorToggle.getAttribute('aria-expanded')).toBe('true');
    const ohlcTooltip = root.querySelector('.chart-tooltip')!;
    const indicatorTooltip = root.querySelector('.chart-indicators')!;
    expect(ohlcTooltip.parentElement).toBe(root.querySelector('.chart-indicator-list'));
    expect(ohlcTooltip.contains(indicatorTooltip)).toBe(false);
    const indicatorBoxes = root.querySelectorAll('.chart-indicator');
    expect(Array.from(indicatorBoxes, (box) => box.textContent?.trim())).toEqual([
      'Volume Profile (24 Bars, 70% Value Area)',
      'Big Trades (5%)',
    ]);
    expect(indicatorTooltip.textContent).toContain('Volume Profile (24 Bars, 70% Value Area)');
    expect(indicatorTooltip.textContent).toContain('Big Trades (5%)');
    expect(indicatorTooltip.textContent!.indexOf('Volume Profile')).toBeLessThan(
      indicatorTooltip.textContent!.indexOf('Big Trades'),
    );
    indicatorToggle.click();
    fixture.detectChanges();
    expect(indicatorToggle.getAttribute('aria-expanded')).toBe('false');
    expect(root.querySelector('.chart-tooltip')).toBeNull();
    expect(root.querySelectorAll('.chart-indicator')).toHaveLength(0);
    socket.receive({
      type: 'resource_init',
      data: { resource_type: 'volume_profile', target: 'main_chart/0', price_bin_count: 16, value_area_pct: 68 },
    });
    fixture.detectChanges();
    expect(service.dynamicResources()).toHaveLength(3);
    const reconfiguredProfile = service.dynamicResources().find(
      (resource) => resource.resource_type === 'volume_profile',
    );
    expect(
      reconfiguredProfile?.resource_type === 'volume_profile'
        ? reconfiguredProfile.price_bin_count
        : null,
    ).toBe(16);

    socket.receive([
      ...message(1_000),
      {
        type: 'market_update',
        data: {
          resource_type: 'volume_profile',
          target: 'main_chart/0',
          bins: [
            { low: '100.0', size: '1.0', volume: '12.5' },
            { low: '101.0', size: '1.0', volume: '6.25' },
          ],
          poc: { price: '100.5', volume: '12.5' },
          value_area: { low: '100.0', high: '102.0' },
        },
      },
      { type: 'market_update', data: { resource_type: 'open_interest', target: 'main_chart/0', time: 1_000, value: '1234.5' } },
      {
        type: 'market_update',
        data: {
          resource_type: 'big_trades',
          target: 'main_chart/0',
          trades: [{ time: 1_000, price: '105.5', quantity: '12.0', side: 1 }],
        },
      },
    ]);
    await waitForDisplayUpdate();
    fixture.detectChanges();

    expect(root.querySelectorAll('.volume-profile rect')).toHaveLength(2);
    expect(root.querySelector('.volume-profile rect')?.getAttribute('x')).toBe('30');
    expect(root.querySelector('.last-price-line')?.getAttribute('x2')).toBe('952');
    expect(root.querySelector('.oscillator-grid line')?.getAttribute('x1')).toBe('30');
    expect(root.querySelector('.oscillator-grid line')?.getAttribute('x2')).toBe('952');
    expect(root.querySelector('.price-grid text')?.getAttribute('x')).toBe('998');
    expect(root.querySelector('.oscillator-grid text')?.getAttribute('x')).toBe('998');
    expect(root.querySelector('.oscillator-grid text')?.getAttribute('text-anchor')).toBe('end');
    expect(root.querySelector('.point-of-control')).toBeTruthy();
    expect(root.querySelector('.value-area-band')).toBeTruthy();
    expect(root.querySelectorAll('.big-trades circle')).toHaveLength(1);
    expect(root.querySelector('.big-trades circle')?.getAttribute('data-side')).toBe('BUY');
    expect(root.querySelector('.open-interest-line')?.getAttribute('d')).toContain('M');
    const profile = service.dynamicResources().find((resource) => resource.resource_type === 'volume_profile');
    expect(profile?.resource_type === 'volume_profile' ? profile.bins[0].volume : null).toBe(12.5);
    const oi = service.dynamicResources().find((resource) => resource.resource_type === 'open_interest');
    expect(oi?.resource_type === 'open_interest' ? oi.points[0].value : null).toBe(1234.5);
  });

  it('replaces complete volume-profile and big-trade snapshots and upserts OI points by time', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    socket.open();
    initTarget(socket);
    socket.receive([
      { type: 'resource_init', data: { resource_type: 'volume_profile', target: 'main_chart/0', price_bin_count: 24, value_area_pct: 70 } },
      { type: 'resource_init', data: { resource_type: 'open_interest', target: 'main_chart/0', length: 2 } },
      { type: 'resource_init', data: { resource_type: 'big_trades', target: 'main_chart/0', top_pct: 5 } },
      ...message(1_000),
    ]);
    socket.receive([
      {
        type: 'market_update',
        data: { resource_type: 'volume_profile', target: 'main_chart/0', bins: [{ low: '100', size: '1', volume: '2' }, { low: '101', size: '1', volume: '3' }], poc: null, value_area: null },
      },
      { type: 'market_update', data: { resource_type: 'open_interest', target: 'main_chart/0', time: 2_000, value: '20' } },
      { type: 'market_update', data: { resource_type: 'open_interest', target: 'main_chart/0', time: 1_000, value: '10' } },
      {
        type: 'market_update',
        data: { resource_type: 'big_trades', target: 'main_chart/0', trades: [{ time: 1_000, price: '100', quantity: '1', side: 1 }, { time: 1_100, price: '101', quantity: '2', side: -1 }] },
      },
    ]);
    fixture.detectChanges();
    const firstTradeMarkers = root.querySelectorAll<SVGCircleElement>('.big-trades circle');
    expect(firstTradeMarkers).toHaveLength(2);
    expect(Number(firstTradeMarkers[1].getAttribute('r')))
      .toBeGreaterThan(Number(firstTradeMarkers[0].getAttribute('r')));
    expect(Number(firstTradeMarkers[1].getAttribute('fill-opacity')))
      .toBeGreaterThan(Number(firstTradeMarkers[0].getAttribute('fill-opacity')));

    socket.receive([
      {
        type: 'market_update',
        data: { resource_type: 'volume_profile', target: 'main_chart/0', bins: [{ low: '110', size: '2', volume: '8' }], poc: { price: '111', volume: '8' }, value_area: { low: '110', high: '112' } },
      },
      { type: 'market_update', data: { resource_type: 'open_interest', target: 'main_chart/0', time: 2_000, value: '25' } },
      {
        type: 'market_update',
        data: { resource_type: 'big_trades', target: 'main_chart/0', trades: [{ time: 1_200, price: '110', quantity: '3', side: -1 }] },
      },
    ]);
    fixture.detectChanges();

    expect(root.querySelectorAll('.volume-profile rect')).toHaveLength(1);
    expect(root.querySelectorAll('.big-trades circle')).toHaveLength(1);
    expect(root.querySelector('.big-trades circle')?.getAttribute('data-side')).toBe('SELL');
    let profile = service.dynamicResources().find((resource) => resource.resource_type === 'volume_profile');
    expect(profile?.resource_type === 'volume_profile' ? profile.bins.map((bin) => bin.low) : []).toEqual([110]);
    let oi = service.dynamicResources().find((resource) => resource.resource_type === 'open_interest');
    expect(oi?.resource_type === 'open_interest' ? oi.points : []).toEqual([
      { timestamp: 1_000, value: 10 },
      { timestamp: 2_000, value: 25 },
    ]);

    socket.receive({ type: 'market_update', data: { resource_type: 'big_trades', target: 'main_chart/0', trades: [] } });
    fixture.detectChanges();
    expect(root.querySelectorAll('.big-trades circle')).toHaveLength(0);

    socket.receive({ type: 'market_update', data: { resource_type: 'open_interest', target: 'main_chart/0', time: 3_000, value: '30' } });
    oi = service.dynamicResources().find((resource) => resource.resource_type === 'open_interest');
    expect(oi?.resource_type === 'open_interest' ? oi.points : []).toEqual([
      { timestamp: 2_000, value: 25 },
      { timestamp: 3_000, value: 30 },
    ]);
  });

  it('keeps dynamic resource state separate by target and reconnects from a fresh init snapshot', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const service = TestBed.inject(MarketDataSocketService);
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket.open();
    initTarget(firstSocket, 'main_chart/0', 60);
    initTarget(firstSocket, 'main_chart/1', 300);
    firstSocket.receive([
      { type: 'resource_init', data: { resource_type: 'volume_profile', target: 'main_chart/0', price_bin_count: 24, value_area_pct: 70 } },
      { type: 'resource_init', data: { resource_type: 'volume_profile', target: 'main_chart/1', price_bin_count: 12, value_area_pct: 80 } },
      { type: 'market_update', data: { resource_type: 'volume_profile', target: 'main_chart/0', bins: [{ low: '100', size: '1', volume: '2' }], poc: null, value_area: null } },
      { type: 'market_update', data: { resource_type: 'volume_profile', target: 'main_chart/1', bins: [{ low: '200', size: '1', volume: '3' }, { low: '201', size: '1', volume: '4' }], poc: null, value_area: null } },
    ]);
    fixture.detectChanges();
    expect(root.querySelectorAll('.volume-profile rect')).toHaveLength(1);
    root.querySelector<HTMLButtonElement>('.timeframe-controls button:nth-child(2)')!.click();
    fixture.detectChanges();
    expect(root.querySelectorAll('.volume-profile rect')).toHaveLength(2);
    expect(service.activeTarget()).toBe('main_chart/1');

    firstSocket.closeFromServer();
    await new Promise((resolve) => setTimeout(resolve, 550));
    expect(FakeWebSocket.instances).toHaveLength(2);
    expect(service.dynamicResources()).toEqual([]);
    const secondSocket = FakeWebSocket.instances[1];
    secondSocket.open();
    secondSocket.receive({
      type: 'market_update',
      data: { resource_type: 'volume_profile', target: 'main_chart/1', bins: [{ low: '300', size: '1', volume: '5' }], poc: null, value_area: null },
    });
    expect(service.dynamicResources()).toEqual([]);

    initTarget(secondSocket, 'main_chart/1', 300);
    secondSocket.receive([
      { type: 'resource_init', data: { resource_type: 'volume_profile', target: 'main_chart/1', price_bin_count: 8, value_area_pct: 65 } },
      { type: 'resource_init', data: { resource_type: 'open_interest', target: 'main_chart/1', length: 20 } },
      { type: 'resource_init', data: { resource_type: 'big_trades', target: 'main_chart/1', top_pct: 2 } },
      { type: 'market_update', data: { resource_type: 'volume_profile', target: 'main_chart/1', bins: [{ low: '300', size: '1', volume: '5' }], poc: null, value_area: null } },
      { type: 'market_update', data: { resource_type: 'open_interest', target: 'main_chart/1', time: 1_000, value: '45.5' } },
      { type: 'market_update', data: { resource_type: 'big_trades', target: 'main_chart/1', trades: [] } },
    ]);
    fixture.detectChanges();
    expect(service.dynamicResources()).toHaveLength(3);
    expect(service.activeTarget()).toBe('main_chart/1');
    expect(root.querySelectorAll('.volume-profile rect')).toHaveLength(1);
    expect(root.querySelectorAll('app-oscillator-panel h2').length).toBe(3);
  });

  it('keeps resources registered when their optional init snapshots are malformed', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    const warning = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    socket.open();
    initTarget(socket);
    socket.receive([
      {
        type: 'resource_init',
        data: {
          resource_type: 'ohlcv_timeframe',
          target: 'context_chart/1',
          period: '1D',
          snapshot: { interval: null, candles: [] },
        },
      },
      {
        type: 'resource_init',
        data: {
          resource_type: 'volume_profile',
          target: 'main_chart/0',
          price_bin_count: 12,
          value_area_pct: 70,
          snapshot: { time: 1_000, bins: [], poc: null, value_area: 'invalid' },
        },
      },
    ]);
    fixture.detectChanges();

    expect(root.querySelector('app-context-chart')).toBeTruthy();
    expect(service.contextCharts()[0]).toMatchObject({ target: 'context_chart/1', period: '1D' });
    expect(service.dynamicResources()).toContainEqual(
      expect.objectContaining({ resource_type: 'volume_profile', target: 'main_chart/0' }),
    );
    expect(warning).toHaveBeenCalledTimes(2);
    warning.mockRestore();
  });

  it('hydrates resource and analysis state from init snapshots before applying live updates', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const socket = FakeWebSocket.instances[0];
    const service = TestBed.inject(MarketDataSocketService);
    socket.open();
    socket.receive([
      {
        type: 'resource_init',
        data: {
          resource_type: 'timeframe',
          target: 'main_chart/0',
          candle_seconds: 60,
          length: 10,
          snapshot: {
            candles: [{ time: 1_000, open: '100', high: '105', low: '99', close: '103' }],
          },
        },
      },
      {
        type: 'resource_init',
        data: {
          resource_type: 'volume_delta',
          target: 'main_chart/0',
          length: 10,
          snapshot: { records: [{ time: 1_000, value: '12.5' }] },
        },
      },
      {
        type: 'resource_init',
        data: {
          resource_type: 'cvd',
          target: 'main_chart/0',
          length: 10,
          snapshot: { records: [{ time: 1_000, value: '25' }] },
        },
      },
      {
        type: 'resource_init',
        data: {
          resource_type: 'volume_profile',
          target: 'main_chart/0',
          price_bin_count: 12,
          value_area_pct: 70,
          snapshot: {
            time: 1_000,
            bins: [{ low: '100', size: '1', volume: '12.5' }],
            poc: { price: '100.5', volume: '12.5' },
            value_area: { low: '100', high: '101' },
          },
        },
      },
      {
        type: 'resource_init',
        data: {
          resource_type: 'open_interest',
          target: 'main_chart/0',
          length: 10,
          snapshot: { records: [{ time: 1_000, value: '300' }] },
        },
      },
      {
        type: 'resource_init',
        data: {
          resource_type: 'big_trades',
          target: 'main_chart/0',
          top_pct: 5,
          snapshot: { trades: [{ time: 1_000, price: '102', quantity: '2', side: 1 }] },
        },
      },
      {
        type: 'resource_init',
        data: {
          resource_type: 'ohlcv_timeframe',
          target: 'context_chart/1',
          period: '1D',
          snapshot: {
            interval: '1d',
            candles: [{ time: 1_000, open: '100', high: '105', low: '99', close: '103' }],
          },
        },
      },
      {
        type: 'resource_init',
        data: {
          resource_type: 'ohlcv_volume_profile',
          target: 'context_chart/1',
          price_bin_count: 8,
          snapshot: {
            time: 1_000,
            bins: [{ low: '100', size: '1', volume: '8' }],
            poc: null,
            value_area: null,
          },
        },
      },
      {
        type: 'resource_init',
        data: {
          resource_type: 'news',
          target: 'news_panel',
          snapshot: {
            items: [
              {
                time: 1_000,
                category: 'macro',
                headline: 'Snapshot headline',
                summary: 'Snapshot summary',
                features: {
                  sentiment: '0.5',
                  severity: '0.2',
                  market_relevance: '0.8',
                  symbol_relevance: '0.9',
                },
              },
            ],
            aggregated: {
              sentiment: '0.5',
              severity: '0.2',
              market_relevance: '0.8',
              symbol_relevance: '0.9',
            },
          },
        },
      },
      {
        type: 'analysis_init',
        data: {
          analysis_type: 'equity_curve',
          target: 'equity_curve/cumulative_BTCUSDT',
          name: 'BTCUSDT',
          snapshot: {
            points: [{ time: 1_000, equity: '1010.50' }],
            starting_balance: '1000.00',
          },
        },
      },
      {
        type: 'analysis_init',
        data: {
          analysis_type: 'statistics',
          target: 'statistics/cumulative_BTCUSDT',
          name: 'BTCUSDT',
          snapshot: {
            total_trades: 12,
            winrate: null,
            pnl: 42.109,
            roi: 0.042,
            max_drawdown: 0.012,
            average_trade_duration: null,
          },
        },
      },
      {
        type: 'session_start',
        data: {
          strategy_name: 'Snapshot Strategy',
          session_number: 42,
          symbol: 'BTCUSDT',
          progress: '7/42',
        },
      },
    ]);

    await waitForDisplayUpdate();
    expect(service.sessionStart()?.session_number).toBe('42');
    expect(service.series()).toMatchObject({
      candles: [{ timestamp: 1_000, open: 100, close: 103, volume: 0 }],
      volumeDelta: [{ timestamp: 1_000, value: 12.5 }],
      cvd: [{ timestamp: 1_000, value: 25 }],
    });
    expect(service.dynamicResources()).toContainEqual(
      expect.objectContaining({
        resource_type: 'volume_profile',
        time: 1_000,
        bins: [{ low: 100, size: 1, volume: 12.5 }],
      }),
    );
    expect(service.dynamicResources()).toContainEqual(
      expect.objectContaining({
        resource_type: 'open_interest',
        points: [{ timestamp: 1_000, value: 300 }],
      }),
    );
    expect(service.dynamicResources()).toContainEqual(
      expect.objectContaining({
        resource_type: 'big_trades',
        trades: [{ time: 1_000, price: 102, quantity: 2, side: 1 }],
      }),
    );
    expect(service.contextCharts()[0]).toMatchObject({
      interval: '1d',
      candles: [{ time: 1_000, open: 100, close: 103 }],
      volumeProfile: { time: 1_000, bins: [{ low: 100, size: 1, volume: 8 }] },
    });
    expect(service.newsPanel()).toMatchObject({
      latestUpdateTime: 1_000,
      aggregated: { sentiment: 0.5 },
      headlines: [
        {
          time: 1_000,
          headline: 'Snapshot headline',
          category: 'macro',
          summary: 'Snapshot summary',
          features: { symbol_relevance: 0.9 },
        },
      ],
    });
    expect(service.analysisEquityCurves()[0].points).toEqual([
      { timestamp: 1_000, value: 1010.5 },
    ]);
    expect(service.analysisEquityCurves()[0].startingBalance).toBe(1000);
    expect(service.analysisStatistics()[0].statistics).toEqual([
      { key: 'total_trades', value: 12 },
      { key: 'winrate', value: null },
      { key: 'pnl', value: 42.109 },
      { key: 'roi', value: 0.042 },
      { key: 'max_drawdown', value: 0.012 },
      { key: 'average_trade_duration', value: null },
    ]);

    socket.receive([
      {
        type: 'market_update',
        data: {
          resource_type: 'timeframe',
          target: 'main_chart/0',
          time: 2_000,
          open: '103',
          high: '106',
          low: '102',
          close: '105',
        },
      },
      {
        type: 'analysis_update',
        data: {
          analysis_type: 'equity_curve',
          target: 'equity_curve/cumulative_BTCUSDT',
          time: 2_000,
          equity: '1020',
          starting_balance: '1000.00',
        },
      },
    ]);
    await waitForDisplayUpdate();
    expect(service.series().candles.map((candle) => candle.timestamp)).toEqual([1_000, 2_000]);
    expect(service.analysisEquityCurves()[0].points).toEqual([
      { timestamp: 1_000, value: 1010.5 },
      { timestamp: 2_000, value: 1020 },
    ]);
    expect(
      service.parseMessage(
        JSON.stringify({
          type: 'resource_init',
          data: {
            resource_type: 'timeframe',
            target: 'main_chart/0',
            candle_seconds: 60,
            length: 10,
            snapshot: { candles: [{ time: 1_000, open: '100', high: '99', low: '101', close: '100' }] },
          },
        }),
      ),
    ).toMatchObject({
      type: 'resource_init',
      data: { resource_type: 'timeframe', target: 'main_chart/0', candle_seconds: 60, length: 10 },
    });
  });
});
