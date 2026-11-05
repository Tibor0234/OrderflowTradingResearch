import { Component, Input, OnChanges, signal } from '@angular/core';
import {
  BigTrade,
  Candle,
  formatTimeframe,
  PositionEntity,
  Timeframe,
  VolumeProfileResourceState,
} from '../../../shared/models/market-data.models';
import { CHART_PLOT_LEFT, CHART_PLOT_RIGHT, chartPointX } from '../../../shared/chart-layout';

interface CandleGlyph {
  candle: Candle;
  x: number;
  openY: number;
  highY: number;
  lowY: number;
  closeY: number;
  bodyY: number;
  bodyHeight: number;
  bodyWidth: number;
  color: string;
}

interface ChartTick {
  y: number;
  label: string;
}

interface TimeTick {
  x: number;
  label: string;
}

interface ProfileBinGlyph {
  lowY: number;
  height: number;
  x: number;
  width: number;
  low: number;
  size: number;
  volume: number;
}

interface BigTradeGlyph {
  x: number;
  y: number;
  radius: number;
  fillOpacity: number;
  trade: BigTrade;
}

interface PositionEntryGlyph {
  id: string;
  price: number;
  y: number;
  side: 'long' | 'short';
  kind: 'trade' | 'order';
}

@Component({
  selector: 'app-main-price-chart',
  standalone: true,
  styleUrl: './main-price-chart.component.scss',
  templateUrl: './main-price-chart.component.html',
})
export class MainPriceChartComponent implements OnChanges {
  @Input({ required: true }) timeframe: Timeframe = 300;
  @Input() candlesData: readonly Candle[] = [];
  @Input() volumeProfile: VolumeProfileResourceState | null = null;
  @Input() bigTrades: readonly BigTrade[] = [];
  @Input() bigTradesTopPct: number | null = null;
  @Input() positionEntities: readonly PositionEntity[] = [];
  @Input() hoveredPositionId: string | null = null;

  protected readonly hoveredIndex = signal<number | null>(null);
  protected readonly crosshairY = signal<number | null>(null);
  protected readonly indicatorLegendExpanded = signal(false);

  protected candles: readonly CandleGlyph[] = [];
  protected profileBins: readonly ProfileBinGlyph[] = [];
  protected bigTradeMarkers: readonly BigTradeGlyph[] = [];
  protected positionEntryLines: readonly PositionEntryGlyph[] = [];
  protected priceTicks: readonly ChartTick[] = [];
  protected timeTicks: readonly TimeTick[] = [];
  protected readonly plotLeft = CHART_PLOT_LEFT;
  protected readonly plotRight = CHART_PLOT_RIGHT;
  protected readonly plotTop = 12;
  protected readonly plotBottom = 430;
  private priceMin = 0;
  private priceMax = 1;

  ngOnChanges(): void {
    this.buildChart();
    this.hoveredIndex.set(null);
  }

  protected get timeframeLabel(): string {
    return formatTimeframe(this.timeframe);
  }

  protected get hoveredCandle(): Candle | null {
    const index = this.hoveredIndex();
    return index === null ? null : this.candles[index]?.candle ?? null;
  }

  protected onPointerMove(event: PointerEvent): void {
    if (!this.candles.length) return;

    const svg = event.currentTarget as SVGSVGElement;
    const bounds = svg.getBoundingClientRect();
    if (bounds.width === 0 || bounds.height === 0) return;

    const viewX = ((event.clientX - bounds.left) / bounds.width) * 1000;
    const step = (this.plotRight - this.plotLeft) / this.candles.length;
    const index = Math.max(
      0,
      Math.min(this.candles.length - 1, Math.floor((viewX - this.plotLeft) / step)),
    );
    const viewY = ((event.clientY - bounds.top) / bounds.height) * 470;
    this.hoveredIndex.set(index);
    this.crosshairY.set(Math.max(this.plotTop, Math.min(this.plotBottom, viewY)));
  }

  protected clearPointer(): void {
    this.hoveredIndex.set(null);
    this.crosshairY.set(null);
  }

  protected toggleIndicatorLegend(): void {
    this.indicatorLegendExpanded.update((expanded) => !expanded);
  }

  protected formatPrice(value: number): string {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    });
  }

  protected formatTime(timestamp: number, includeDate = false): string {
    return new Date(timestamp).toLocaleString('en-GB', {
      timeZone: 'UTC',
      ...(includeDate ? { day: '2-digit', month: 'short' } : {}),
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  protected formatAxisTime(timestamp: number): string {
    if (this.timeframe >= 14_400) {
      return new Date(timestamp).toLocaleDateString('en-GB', {
        timeZone: 'UTC',
        day: '2-digit',
        month: 'short',
      });
    }
    return this.formatTime(timestamp, this.timeframe >= 3_600);
  }

  protected get currentPriceY(): number {
    const last = this.candles[this.candles.length - 1];
    return last ? this.priceToY(last.candle.close) : this.plotBottom;
  }

  protected priceToY(price: number): number {
    return (
      this.plotBottom -
      ((price - this.priceMin) / (this.priceMax - this.priceMin)) *
        (this.plotBottom - this.plotTop)
    );
  }

  protected isHovered(index: number): boolean {
    return this.hoveredIndex() === index;
  }

  private buildChart(): void {
    const candles = this.candlesData;
    const positionEntryLevels = this.buildPositionEntryLevels();
    const profilePrices = this.volumeProfile?.bins.flatMap((bin) => [bin.low, bin.low + bin.size]) ?? [];
    const overlayPrices = [
      ...(this.volumeProfile?.poc ? [this.volumeProfile.poc.price] : []),
      ...(this.volumeProfile?.value_area
        ? [this.volumeProfile.value_area.low, this.volumeProfile.value_area.high]
        : []),
      ...this.bigTrades.map((trade) => trade.price),
    ];
    const allPrices = [
      ...candles.flatMap((candle) => [candle.low, candle.high]),
      ...profilePrices,
      ...overlayPrices,
      ...positionEntryLevels.map((level) => level.price),
    ];
    if (!allPrices.length) {
      this.candles = [];
      this.profileBins = [];
      this.bigTradeMarkers = [];
      this.positionEntryLines = [];
      this.priceTicks = [];
      this.timeTicks = [];
      return;
    }
    const rawMin = Math.min(...allPrices);
    const rawMax = Math.max(...allPrices);
    const padding = rawMax > rawMin ? (rawMax - rawMin) * 0.07 : Math.max(Math.abs(rawMax) * 0.001, 1);
    this.priceMin = rawMin - padding;
    this.priceMax = rawMax + padding;
    const candleStep = (this.plotRight - this.plotLeft) / Math.max(candles.length, 1);
    const candleBodyWidth = Math.min(8, candleStep * 0.8);

    this.candles = candles.map((candle, index) => {
      const openY = this.priceToY(candle.open);
      const closeY = this.priceToY(candle.close);
      return {
        candle,
        x: chartPointX(index, candles.length),
        openY,
        highY: this.priceToY(candle.high),
        lowY: this.priceToY(candle.low),
        closeY,
        bodyY: Math.min(openY, closeY),
        bodyHeight: Math.max(Math.abs(closeY - openY), 1.5),
        bodyWidth: candleBodyWidth,
        color: candle.close >= candle.open ? 'up' : 'down',
      };
    });
    this.positionEntryLines = positionEntryLevels.map((level) => ({
      ...level,
      y: this.priceToY(level.price),
    }));

    const maximumVolume = Math.max(...(this.volumeProfile?.bins.map((bin) => bin.volume) ?? [0]), 1);
    const maximumProfileWidth = (this.plotRight - this.plotLeft) * 0.2;
    this.profileBins = (this.volumeProfile?.bins ?? []).map((bin) => {
      const top = this.priceToY(bin.low + bin.size);
      const bottom = this.priceToY(bin.low);
      const width = (bin.volume / maximumVolume) * maximumProfileWidth;
      return {
        lowY: Math.min(top, bottom),
        height: Math.max(Math.abs(bottom - top), 1),
        x: this.plotLeft,
        width,
        low: bin.low,
        size: bin.size,
        volume: bin.volume,
      };
    });

    const firstCandle = candles[0];
    const lastCandle = candles[candles.length - 1];
    const maximumQuantity = Math.max(...this.bigTrades.map((trade) => trade.quantity), 1);
    this.bigTradeMarkers =
      firstCandle && lastCandle
        ? this.bigTrades.map((trade) => {
            const timeRatio =
              firstCandle.timestamp === lastCandle.timestamp
                ? 0.5
                : (trade.time - firstCandle.timestamp) /
                  (lastCandle.timestamp - firstCandle.timestamp);
            const quantityRatio = Math.max(
              0,
              Math.min(1, trade.quantity / maximumQuantity),
            );
            return {
              x: this.plotLeft + Math.max(0, Math.min(1, timeRatio)) * (this.plotRight - this.plotLeft),
              y: this.priceToY(trade.price),
              radius: 2.5 + quantityRatio * 6.5,
              fillOpacity: 0.25 + quantityRatio * 0.65,
              trade,
            };
          })
        : [];

    this.priceTicks = Array.from({ length: 6 }, (_, index) => {
      const ratio = index / 5;
      const price = this.priceMax - ratio * (this.priceMax - this.priceMin);
      return {
        y: this.plotTop + ratio * (this.plotBottom - this.plotTop),
        label: Math.round(price).toLocaleString('en-US'),
      };
    });

    const tickIndices = candles.length
      ? [
          ...new Set(
            Array.from({ length: 6 }, (_, index) =>
              Math.round((index * (candles.length - 1)) / 5),
            ),
          ),
        ]
      : [];
    this.timeTicks = tickIndices.map((index) => ({
      x: this.candles[index].x,
      label: this.formatAxisTime(this.candles[index].candle.timestamp),
    }));
  }

  private buildPositionEntryLevels(): Omit<PositionEntryGlyph, 'y'>[] {
    const levels: Omit<PositionEntryGlyph, 'y'>[] = [];
    const tradeIds = new Set(
      this.positionEntities
        .filter((entity): entity is Extract<PositionEntity, { type: 'trade' }> => entity.type === 'trade')
        .map((trade) => trade.id),
    );
    const orderIds = new Set(
      this.positionEntities
        .filter((entity): entity is Extract<PositionEntity, { type: 'order' }> => entity.type === 'order')
        .map((order) => order.id),
    );
    for (const entity of this.positionEntities) {
      if (
        entity.type !== 'trade' &&
        entity.type !== 'order' &&
        entity.source_id !== null &&
        !tradeIds.has(entity.source_id) &&
        orderIds.has(entity.source_id)
      ) {
        continue;
      }

      let rawPrice: string | null;
      let kind: PositionEntryGlyph['kind'];
      if (entity.type === 'trade') {
        rawPrice = entity.execution_price;
        kind = 'trade';
      } else if (entity.type === 'liquidation_order') {
        continue;
      } else if (entity.type === 'order' || entity.type === 'increase_order') {
        rawPrice = entity.entry_price;
        kind = 'order';
      } else {
        rawPrice = entity.stop_price;
        kind = 'order';
      }

      const rawSide = entity.side?.toLowerCase();
      const side =
        rawSide === 'long' || rawSide === '1'
          ? 'long'
          : rawSide === 'short' || rawSide === '-1'
            ? 'short'
            : null;
      const price = rawPrice === null ? null : Number(rawPrice.replace(/,/g, '').trim());
      if (
        side === null ||
        price === null ||
        !Number.isFinite(price)
      ) {
        continue;
      }
      levels.push({ id: entity.id, price, side, kind });
    }
    return levels;
  }
}
