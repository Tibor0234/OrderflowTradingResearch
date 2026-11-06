import { Component, computed, input } from '@angular/core';
import { EquityCurveComponent } from '../../../shared/charts/equity-curve/equity-curve.component';
import { ParameterCombination, ParameterValue } from '../../multi-strategy-dashboard.models';

@Component({
  imports: [EquityCurveComponent],
  selector: 'app-best-combination',
  templateUrl: './best-combination.component.html',
  styleUrl: './best-combination.component.scss',
})
export class BestCombinationComponent {
  readonly combination = input.required<ParameterCombination>();
  readonly rank = input.required<number>();
  protected readonly equityCurveAspectRatio = 294 / 190.3;
  protected readonly parameters = computed(() =>
    Object.entries(this.combination().parameters).map(([name, value]) => ({ name, value })),
  );
  private readonly numberFormatter = new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
  });
  private readonly currencyFormatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  });

  protected formatNumber(value: number): string {
    return this.numberFormatter.format(value);
  }

  protected formatCurrency(value: number): string {
    return this.currencyFormatter.format(value);
  }

  protected formatPercent(value: number): string {
    return `${value.toFixed(1)}%`;
  }

  protected formatParameter(value: ParameterValue): string {
    if (typeof value === 'boolean') return value ? 'On' : 'Off';
    return typeof value === 'number' ? this.numberFormatter.format(value) : value;
  }
}
