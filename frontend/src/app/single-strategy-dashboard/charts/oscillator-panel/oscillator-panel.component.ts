import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { TimeSeriesPoint, Timeframe } from '../../../shared/models/market-data.models';
import { CHART_PLOT_LEFT, CHART_PLOT_RIGHT, chartPointX } from '../../chart-layout';

interface DeltaBar {
  x: number;
  y: number;
  width: number;
  height: number;
  value: number;
  timestamp: number;
  direction: 'up' | 'down';
}

interface OscillatorTick {
  y: number;
  label: string;
}

interface OscillatorTimeTick {
  x: number;
  label: string;
}

interface SeriesGlyph {
  x: number;
  y: number;
  value: number;
  timestamp: number;
}

interface CvdSegment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  direction: 'positive' | 'negative';
}

@Component({
  selector: 'app-oscillator-panel',
  standalone: true,
  styleUrl: './oscillator-panel.component.scss',
  templateUrl: './oscillator-panel.component.html',
})
export class OscillatorPanelComponent implements OnChanges {
  @Input({ required: true }) title = '';
  @Input() kind: 'volumeDelta' | 'cvd' | 'openInterest' = 'volumeDelta';
  @Input() timeframe: Timeframe = 300;
  @Input() series: readonly TimeSeriesPoint[] = [];
  @Input() expanded = true;
  @Output() expandedChange = new EventEmitter<boolean>();

  protected deltaBars: readonly DeltaBar[] = [];
  protected deltaTicks: readonly OscillatorTick[] = [];
  protected cvdTicks: readonly OscillatorTick[] = [];
  protected timeTicks: readonly OscillatorTimeTick[] = [];
  protected cvdPoints: readonly SeriesGlyph[] = [];
  protected cvdSegments: readonly CvdSegment[] = [];
  protected cvdPath = '';
  protected cvdZeroY = 80;
  protected readonly plotLeft = CHART_PLOT_LEFT;
  protected readonly plotRight = CHART_PLOT_RIGHT;

  ngOnChanges(): void {
    this.buildChart();
  }

  protected toggleExpanded(): void {
    this.expandedChange.emit(!this.expanded);
  }

  protected get currentValue(): string {
    const value = this.series[this.series.length - 1]?.value;
    return value === undefined ? 'N/A' : value.toLocaleString('en-US', { maximumFractionDigits: 1 });
  }

  protected formatTime(timestamp: number): string {
    if (this.timeframe >= 14_400) {
      return new Date(timestamp).toLocaleDateString('en-GB', {
        timeZone: 'UTC',
        day: '2-digit',
        month: 'short',
      });
    }
    return new Date(timestamp).toLocaleString('en-GB', {
      timeZone: 'UTC',
      ...(this.timeframe >= 3_600 ? { day: '2-digit', month: 'short' } : {}),
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  private buildChart(): void {
    if (this.series.length === 0) {
      this.deltaBars = [];
      this.deltaTicks = [];
      this.cvdTicks = [];
      this.timeTicks = [];
      this.cvdPoints = [];
      this.cvdSegments = [];
      this.cvdPath = '';
      return;
    }

    const step = (this.plotRight - this.plotLeft) / this.series.length;
    const deltaMax = Math.max(...this.series.map((point) => Math.abs(point.value)), 1);
    const zeroY = 86;
    const deltaHeight = 65;

    this.deltaBars = this.series.map((point, index) => {
      const height = (Math.abs(point.value) / deltaMax) * deltaHeight;
      const direction = point.value >= 0 ? 'up' : 'down';
      return {
        x: chartPointX(index, this.series.length),
        y: direction === 'up' ? zeroY - height : zeroY,
        width: Math.max(2, Math.min(10, step * 0.62)),
        height,
        value: point.value,
        timestamp: point.timestamp,
        direction,
      };
    });

    this.deltaTicks = [
      { y: zeroY - deltaHeight, label: `+${deltaMax.toFixed(0)}` },
      { y: zeroY, label: '0' },
      { y: zeroY + deltaHeight, label: `−${deltaMax.toFixed(0)}` },
    ];

    const rawMin = Math.min(...this.series.map((point) => point.value));
    const rawMax = Math.max(...this.series.map((point) => point.value));
    const padding = Math.max((rawMax - rawMin) * 0.1, 1);
    const low = rawMin - padding;
    const high = rawMax + padding;
    const toY = (value: number) => 154 - ((value - low) / (high - low)) * 140;
    this.cvdPoints = this.series.map((point, index) => ({
      x: chartPointX(index, this.series.length),
      y: toY(point.value),
      value: point.value,
      timestamp: point.timestamp,
    }));

    this.cvdPath = this.cvdPoints
      .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
      .join(' ');
    this.cvdZeroY = toY(0);
    this.cvdSegments = this.buildCvdSegments(this.cvdPoints);
    this.cvdTicks = [high, (high + low) / 2, low].map((value, index) => ({
      y: 14 + index * 70,
      label: value.toLocaleString('en-US', { maximumFractionDigits: 0 }),
    }));

    const tickIndices = Array.from({ length: 5 }, (_, index) =>
      Math.round((index * (this.series.length - 1)) / 4),
    );
    this.timeTicks = tickIndices.map((index) => ({
      x: chartPointX(index, this.series.length),
      label: this.formatTime(this.series[index].timestamp),
    }));
  }

  private buildCvdSegments(points: readonly SeriesGlyph[]): readonly CvdSegment[] {
    const segments: CvdSegment[] = [];
    const addSegment = (
      start: Pick<SeriesGlyph, 'x' | 'y'>,
      end: Pick<SeriesGlyph, 'x' | 'y'>,
      direction: CvdSegment['direction'],
    ): void => {
      segments.push({
        x1: start.x,
        y1: start.y,
        x2: end.x,
        y2: end.y,
        direction,
      });
    };

    for (let index = 1; index < points.length; index += 1) {
      const previous = points[index - 1];
      const current = points[index];
      if (
        (previous.value < 0 && current.value > 0) ||
        (previous.value > 0 && current.value < 0)
      ) {
        const ratio = previous.value / (previous.value - current.value);
        const crossing = {
          x: previous.x + (current.x - previous.x) * ratio,
          y: this.cvdZeroY,
        };
        const previousDirection = previous.value < 0 ? 'negative' : 'positive';
        const currentDirection = current.value < 0 ? 'negative' : 'positive';
        addSegment(previous, crossing, previousDirection);
        addSegment(crossing, current, currentDirection);
      } else {
        const direction =
          previous.value < 0 || current.value < 0 ? 'negative' : 'positive';
        addSegment(previous, current, direction);
      }
    }

    return segments;
  }
}
