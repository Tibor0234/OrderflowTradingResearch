import { Component, Input, OnChanges } from '@angular/core';
import { EquityPoint } from './equity-curve.models';

interface EquityTick {
  y: number;
  label: string;
}

interface EquityTimeTick {
  x: number;
  label: string;
}

@Component({
  selector: 'app-equity-curve',
  standalone: true,
  styleUrl: './equity-curve.component.scss',
  templateUrl: './equity-curve.component.html',
})
export class EquityCurveComponent implements OnChanges {
  @Input({ required: true }) points: readonly EquityPoint[] = [];
  @Input() startingBalance: number | null = null;
  @Input() aspectRatio: number | null = null;
  @Input() compactAxisLabels = false;
  @Input() prominentValueLabels = false;

  protected linePath = '';
  protected areaPath = '';
  protected currentEquityY: number | null = null;
  protected currentEquityValue: number | null = null;
  protected startingEquityY: number | null = null;
  protected startingEquityValue: number | null = null;
  protected valueTicks: readonly EquityTick[] = [];
  protected timeTicks: readonly EquityTimeTick[] = [];

  protected readonly plotLeft = 0;
  protected readonly plotRight = 455;
  private readonly plotTop = 16;
  private readonly plotBottom = 152;
  private low = 0;
  private high = 1;

  ngOnChanges(): void {
    this.buildChart();
  }

  protected equityLabelTop(y: number): string {
    const progress = y / 184;
    if (this.aspectRatio === null) {
      const chartHeight = 190.3;
      const svgHeightInChart = chartHeight - 10;
      return `${((6 + progress * svgHeightInChart) / chartHeight) * 100}%`;
    }

    const paddingOffset = 6 - progress * 10;
    const offsetOperator = paddingOffset >= 0 ? '+' : '-';
    return `calc(${progress * 100}% ${offsetOperator} ${Math.abs(paddingOffset)}px)`;
  }

  protected formatCurrentEquity(value: number): string {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    });
  }

  private buildChart(): void {
    if (this.points.length === 0) {
      this.linePath = '';
      this.areaPath = '';
      this.currentEquityY = null;
      this.currentEquityValue = null;
      this.startingEquityY = null;
      this.startingEquityValue = null;
      this.valueTicks = [];
      this.timeTicks = [];
      return;
    }

    const values = this.points.map((point) => point.value);
    if (this.startingBalance !== null) values.push(this.startingBalance);
    const rawLow = Math.min(...values);
    const rawHigh = Math.max(...values);
    const padding = Math.max((rawHigh - rawLow) * 0.14, 20);
    this.low = rawLow - padding;
    this.high = rawHigh + padding;

    const coordinates = this.points.map((point, index) => ({
      x: this.plotLeft + (index / Math.max(this.points.length - 1, 1)) * (this.plotRight - this.plotLeft),
      y: this.toY(point.value),
    }));

    this.linePath = coordinates
      .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
      .join(' ');
    this.areaPath = `${this.linePath} L${this.plotRight} ${this.plotBottom} L${this.plotLeft} ${this.plotBottom} Z`;
    this.startingEquityY =
      this.startingBalance === null ? null : Number(this.toY(this.startingBalance).toFixed(2));
    this.startingEquityValue = this.startingBalance;
    this.currentEquityY = Number(coordinates[coordinates.length - 1].y.toFixed(2));
    this.currentEquityValue = this.points[this.points.length - 1].value;

    this.valueTicks = Array.from({ length: 4 }, (_, index) => {
      const ratio = index / 3;
      const value = this.high - ratio * (this.high - this.low);
      return {
        y: this.plotTop + ratio * (this.plotBottom - this.plotTop),
        label: `$${(value / 1000).toFixed(1)}k`,
      };
    });

    const tickIndices = Array.from({ length: 4 }, (_, index) =>
      Math.round((index * (this.points.length - 1)) / 3),
    );
    this.timeTicks = tickIndices.map((index) => ({
      x: coordinates[index].x,
      label: new Date(this.points[index].timestamp).toLocaleString('en-GB', {
        timeZone: 'UTC',
        day: '2-digit',
        month: 'short',
      }),
    }));
  }

  private toY(value: number): number {
    return this.plotBottom - ((value - this.low) / (this.high - this.low)) * (this.plotBottom - this.plotTop);
  }
}
