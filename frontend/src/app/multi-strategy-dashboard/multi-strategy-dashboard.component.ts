import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { ConnectionIndicatorComponent } from '../shared/connection-indicator/connection-indicator.component';
import { ReplayControlService } from '../shared/services/replay-control.service';
import { SurfaceNavigationComponent } from '../shared/surface-navigation/surface-navigation.component';
import { BestCombinationComponent } from './components/best-combination/best-combination.component';
import { OtherCombinationsTableComponent } from './components/other-combinations-table/other-combinations-table.component';
import { StrategyOverviewComponent } from './components/strategy-overview/strategy-overview.component';
import { MULTI_STRATEGY_DASHBOARD_MOCK_DATA } from './multi-strategy-dashboard.mock-data';
import { ParameterCombination } from './multi-strategy-dashboard.models';

@Component({
  imports: [
    BestCombinationComponent,
    ConnectionIndicatorComponent,
    OtherCombinationsTableComponent,
    StrategyOverviewComponent,
    SurfaceNavigationComponent,
  ],
  selector: 'app-multi-strategy-dashboard',
  templateUrl: './multi-strategy-dashboard.component.html',
  styleUrl: './multi-strategy-dashboard.component.scss',
})
export class MultiStrategyDashboardComponent {
  private readonly replayControl = inject(ReplayControlService);
  protected readonly strategy = MULTI_STRATEGY_DASHBOARD_MOCK_DATA.strategy;
  protected readonly marketDataProgress = MULTI_STRATEGY_DASHBOARD_MOCK_DATA.marketDataProgress;
  protected readonly replayPlaying = signal(false);
  protected readonly replayRequestPending = signal(false);
  protected readonly replayRequestError = signal<string | null>(null);
  private readonly combinationResults = signal<readonly ParameterCombination[]>(
    MULTI_STRATEGY_DASHBOARD_MOCK_DATA.combinations,
  );
  protected readonly selectedCombinationId = signal<string | null>(null);
  protected readonly autoSelectTopCombination = signal(false);
  protected readonly bestCombination = computed(() =>
    this.combinationResults().reduce<ParameterCombination | null>(
      (best, combination) =>
        best === null || combination.statistics.roi > best.statistics.roi ? combination : best,
      null,
    ),
  );
  protected readonly otherCombinations = computed(() => {
    const bestId = this.bestCombination()?.id;
    return this.combinationResults()
      .filter(({ id }) => id !== bestId)
      .sort((left, right) => right.statistics.roi - left.statistics.roi);
  });
  protected readonly displayedCombination = computed(() => {
    if (this.autoSelectTopCombination()) return this.bestCombination();
    const selectedId = this.selectedCombinationId();
    return (
      this.combinationResults().find(({ id }) => id === selectedId) ??
      this.bestCombination()
    );
  });
  protected readonly highlightedCombinationId = computed(() =>
    this.autoSelectTopCombination()
      ? this.bestCombination()?.id ?? null
      : this.selectedCombinationId(),
  );
  protected readonly rankedCombinations = computed(() => {
    const best = this.bestCombination();
    return best ? [best, ...this.otherCombinations()] : [];
  });
  protected readonly parameterCombinationsCollapsed = signal(false);

  protected selectCombination(combinationId: string): void {
    this.autoSelectTopCombination.set(false);
    this.selectedCombinationId.set(combinationId);
  }

  protected toggleTopCombinationSelection(): void {
    if (this.autoSelectTopCombination()) {
      const best = this.bestCombination();
      this.autoSelectTopCombination.set(false);
      if (best) this.selectedCombinationId.set(best.id);
      return;
    }

    this.selectedCombinationId.set(null);
    this.autoSelectTopCombination.set(true);
  }

  updateCombinationResult(result: ParameterCombination): void {
    this.combinationResults.update((current) => {
      if (!current.some(({ id }) => id === result.id)) return [...current, result];
      return current.map((combination) => (combination.id === result.id ? result : combination));
    });
  }

  protected toggleReplay(): void {
    if (this.replayRequestPending()) return;

    const action = this.replayPlaying() ? 'stop' : 'start';
    this.replayRequestPending.set(true);
    this.replayRequestError.set(null);
    this.replayControl.setReplayState(action).subscribe({
      next: () => {
        this.replayPlaying.set(action === 'start');
        this.replayRequestPending.set(false);
      },
      error: (error: unknown) => {
        this.replayRequestPending.set(false);
        if (error instanceof HttpErrorResponse && error.status === 0) {
          this.replayRequestError.set(null);
        } else {
          this.replayRequestError.set(
            error instanceof HttpErrorResponse
              ? `Replay request failed (HTTP ${error.status}).`
              : 'Replay request failed.',
          );
        }
      },
    });
  }
}
