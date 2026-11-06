import { Component, input } from '@angular/core';
import { MarketDataProcessingProgress } from '../../multi-strategy-dashboard.models';

@Component({
  selector: 'app-market-data-progress',
  templateUrl: './market-data-progress.component.html',
  styleUrl: './market-data-progress.component.scss',
})
export class MarketDataProgressComponent {
  readonly progress = input.required<MarketDataProcessingProgress>();
}
