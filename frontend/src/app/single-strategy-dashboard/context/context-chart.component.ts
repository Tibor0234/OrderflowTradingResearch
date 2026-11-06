import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { ContextChartState } from '../../shared/models/market-data.models';

interface CandleGlyph {
  x: number;
  highY: number;
  lowY: number;
  bodyY: number;
  bodyHeight: number;
  bodyWidth: number;
  color: 'up' | 'down';
  candle: ContextChartState['candles'][number];
}

interface ProfileBinGlyph {
  x: number;
  y: number;
  width: number;
  height: number;
  low: number;
  size: number;
  volume: number;
}

interface PriceTick {
  y: number;
  label: string;
}

interface TimeTick {
  x: number;
  label: string;
  anchor: 'start' | 'middle' | 'end';
}

@Component({
  selector: 'app-context-chart',
  standalone: true,
  styleUrl: './context-chart.component.scss',
  templateUrl: './context-chart.component.html',
})
export class ContextChartComponent implements OnChanges {
  @Input({ required: true }) chart!: ContextChartState;
  @Input() expanded = true;
  @Output() expandedChange = new EventEmitter<void>();

  protected candles: readonly CandleGlyph[] = [];
  protected profileBins: readonly ProfileBinGlyph[] = [];
  protected priceTicks: readonly PriceTick[] = [];
  protected timeTicks: readonly TimeTick[] = [];
  protected readonly plotTop = 8;
  protected readonly plotBottom = 94;
  protected readonly plotLeft = 8;
  protected readonly plotRight = 240;
  private readonly profileMaxWidth = (this.plotRight - this.plotLeft) * 0.2;
  private priceMin = 0;
  private priceMax = 1;

  ngOnChanges(): void {
    this.buildChart();
  }

  protected priceToY(price: number): number {
    return (
      this.plotBottom -
      ((price - this.priceMin) / (this.priceMax - this.priceMin)) *
        (this.plotBottom - this.plotTop)
    );
  }

  protected formatPrice(value: number): string {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 4,
    });
  }

  protected formatPocPrice(value: number): string {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    });
  }

  protected formatAxisPrice(value: number): string {
    return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
  }

  protected formatPeriod(period: string): string {
    return period.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  protected get currentPrice(): number | null {
    const candles = this.chart?.candles ?? [];
    return candles.length ? candles[candles.length - 1].close : null;
  }

  private buildChart(): void {
    const chart = this.chart;
    const profile = chart?.volumeProfile;
    const prices = [
      ...(chart?.candles.flatMap((candle) => [candle.high, candle.low]) ?? []),
      ...(profile?.bins.flatMap((bin) => [bin.low, bin.low + bin.size]) ?? []),
      ...(profile?.poc ? [profile.poc.price] : []),
      ...(profile?.value_area ? [profile.value_area.low, profile.value_area.high] : []),
    ];
    if (!prices.length) {
      this.candles = [];
      this.profileBins = [];
      this.priceTicks = [];
      this.timeTicks = [];
      return;
    }

    const rawMin = Math.min(...prices);
    const rawMax = Math.max(...prices);
    const padding = rawMax > rawMin ? (rawMax - rawMin) * 0.08 : Math.max(Math.abs(rawMax) * 0.001, 1);
    this.priceMin = rawMin - padding;
    this.priceMax = rawMax + padding;
    this.priceTicks = Array.from({ length: 5 }, (_, index) => {
      const price = this.priceMax - (index / 4) * (this.priceMax - this.priceMin);
      return { y: this.priceToY(price), label: this.formatAxisPrice(price) };
    });

    const candleStep =
      (this.plotRight - this.plotLeft) / Math.max(chart.candles.length, 1);
    const candleBodyWidth = Math.min(2.8, candleStep * 0.8);
    this.candles = chart.candles.map((candle, index) => {
      const openY = this.priceToY(candle.open);
      const closeY = this.priceToY(candle.close);
      return {
        x:
          this.plotLeft +
          ((index + 0.5) / chart.candles.length) *
            (this.plotRight - this.plotLeft),
        highY: this.priceToY(candle.high),
        lowY: this.priceToY(candle.low),
        bodyY: Math.min(openY, closeY),
        bodyHeight: Math.max(Math.abs(closeY - openY), 1.3),
        bodyWidth: candleBodyWidth,
        color: candle.close >= candle.open ? 'up' : 'down',
        candle,
      };
    });
    this.timeTicks = this.buildTimeTicks(this.candles);

    const maximumVolume = Math.max(...(profile?.bins.map((bin) => bin.volume) ?? [0]), 1);
    this.profileBins = (profile?.bins ?? []).map((bin) => {
      const top = this.priceToY(bin.low + bin.size);
      const bottom = this.priceToY(bin.low);
      const width = (bin.volume / maximumVolume) * this.profileMaxWidth;
      return {
        x: this.plotLeft,
        y: Math.min(top, bottom),
        width,
        height: Math.max(Math.abs(bottom - top), 1),
        low: bin.low,
        size: bin.size,
        volume: bin.volume,
      };
    });
  }

  private buildTimeTicks(candles: readonly CandleGlyph[]): readonly TimeTick[] {
    if (!candles.length) return [];
    const tickCount = Math.min(candles.length, 3);
    return Array.from({ length: tickCount }, (_, index) => {
      const candleIndex =
        tickCount === 1
          ? 0
          : Math.round((index * (candles.length - 1)) / (tickCount - 1));
      const candle = candles[candleIndex].candle;
      return {
        x: candles[candleIndex].x,
        label: this.formatAxisTime(candle.time),
        anchor:
          tickCount === 1 || (index !== 0 && index !== tickCount - 1)
            ? 'middle'
            : index === 0
              ? 'start'
              : 'end',
      };
    });
  }

  private formatAxisTime(timestamp: number): string {
    const interval = (this.chart.interval ?? this.chart.period).toLowerCase();
    const date = new Date(timestamp);
    if (interval.endsWith('d') || interval.endsWith('w')) {
      return date.toLocaleDateString('en-GB', {
        timeZone: 'UTC',
        day: '2-digit',
        month: 'short',
      });
    }
    return date.toLocaleTimeString('en-GB', {
      timeZone: 'UTC',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }
}
