import { Component, input } from '@angular/core';
import { MarketDataProcessingProgress, StrategyInformation } from '../../multi-strategy-dashboard.models';
import { MarketDataProgressComponent } from '../market-data-progress/market-data-progress.component';

@Component({
  imports: [MarketDataProgressComponent],
  selector: 'app-strategy-overview',
  templateUrl: './strategy-overview.component.html',
  styleUrl: './strategy-overview.component.scss',
})
export class StrategyOverviewComponent {
  readonly strategy = input.required<StrategyInformation>();
  readonly progress = input.required<MarketDataProcessingProgress>();

  protected formatNumber(value: number): string {
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
  }
}
