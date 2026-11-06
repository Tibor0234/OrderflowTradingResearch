import { Component, EventEmitter, input, Output } from '@angular/core';
import { ParameterCombination } from '../../multi-strategy-dashboard.models';

@Component({
  selector: 'app-other-combinations-table',
  templateUrl: './other-combinations-table.component.html',
  styleUrl: './other-combinations-table.component.scss',
})
export class OtherCombinationsTableComponent {
  readonly combinations = input.required<readonly ParameterCombination[]>();
  readonly bestCombinationId = input.required<string>();
  readonly selectedCombinationId = input.required<string | null>();
  @Output() readonly combinationSelected = new EventEmitter<string>();

  protected formatNumber(value: number): string {
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
  }

  protected selectOnKeyboard(event: KeyboardEvent, combinationId: string): void {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    this.combinationSelected.emit(combinationId);
  }

  protected formatPercent(value: number): string {
    return `${value.toFixed(1)}%`;
  }
}
