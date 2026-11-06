import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MultiStrategyDashboardComponent } from './multi-strategy-dashboard.component';
import { MULTI_STRATEGY_DASHBOARD_MOCK_DATA } from './multi-strategy-dashboard.mock-data';
import { ParameterCombination } from './multi-strategy-dashboard.models';
import { environment } from '../../environments/environment';

describe('MultiStrategyDashboardComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MultiStrategyDashboardComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
  });

  it('renders market progress, best-combination details, and a selectable combinations table', () => {
    const fixture = TestBed.createComponent(MultiStrategyDashboardComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;

    expect(root.querySelector('[role="progressbar"]')?.getAttribute('aria-valuenow')).toBe('68.4');
    expect(root.querySelector('.progress-value')?.textContent?.trim()).toBe('4/20');
    expect(root.querySelector('.strategy-overview')?.textContent).toContain('Progress');
    expect(root.querySelector('.strategy-overview')?.textContent).not.toContain(
      'Market Data Processing',
    );
    expect(root.querySelector('.strategy-overview')?.textContent).not.toContain(
      'Processing market history',
    );
    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe('COMB-042');
    expect(root.querySelector('.best-heading')?.textContent).not.toContain('Best Parameter Combination');
    expect(root.querySelector('.combination-rank')?.textContent?.trim()).toBe('Rank #1');
    expect(root.querySelector('.combination-rank')?.classList.contains('top-rank')).toBe(true);
    expect(root.querySelectorAll('.stat-item')).toHaveLength(6);
    expect(root.querySelector('.dashboard-card, .detail-panel')).toBeNull();
    expect(root.querySelector('.equity-panel svg path.equity-line')).toBeTruthy();
    expect(root.querySelector('.equity-panel .equity-chart.aspect-ratio-chart')).toBeTruthy();
    expect(root.querySelector('.equity-panel .equity-chart.compact-axis-labels')).toBeTruthy();
    expect(root.querySelector('.equity-panel .equity-chart.prominent-value-labels')).toBeTruthy();
    expect(root.querySelectorAll('.parameter-item')).toHaveLength(5);
    expect(Array.from(root.querySelectorAll('thead th'), (cell) => cell.textContent?.trim())).toEqual([
      'Rank',
      'ID',
      'ROI',
      'Max DD',
    ]);
    expect(root.querySelectorAll('tbody tr')).toHaveLength(
      MULTI_STRATEGY_DASHBOARD_MOCK_DATA.combinations.length,
    );
    expect(root.querySelector('tbody')?.textContent).not.toContain('Fast EMA');
    const tableRows = Array.from(root.querySelectorAll<HTMLTableRowElement>('tbody tr'));
    const tableRois = tableRows.map((row) =>
      Number(row.cells[2].textContent?.replace('%', '')),
    );
    const tableIds = tableRows.map((row) =>
      row.cells[1].textContent?.trim().split(/\s+/)[0],
    );
    const tableRanks = tableRows.map((row) => Number(row.cells[0].textContent));
    expect(tableRois).toEqual([...tableRois].sort((left, right) => right - left));
    expect(new Set(tableIds).size).toBe(tableIds.length);
    expect(tableRanks).toEqual(tableRanks.map((_, index) => index + 1));
    expect(tableIds[0]).toBe('COMB-042');
    expect(root.querySelector('.best-combination-label')).toBeNull();
    expect(tableRows[0].classList.contains('selected-combination-row')).toBe(false);
    expect(tableIds).toContain('COMB-042');
    expect(tableRows.every((row) => row.cells.length === 4)).toBe(true);
    expect(root.querySelectorAll('.combinations-table-wrap a, .combinations-table-wrap button')).toHaveLength(0);
  });

  it('updates best details and re-ranks existing combinations by their immutable IDs', () => {
    const fixture = TestBed.createComponent(MultiStrategyDashboardComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const initialEquityPath = root.querySelector(
      '.equity-panel path.equity-line',
    )?.getAttribute('d');
    const firstCombination = MULTI_STRATEGY_DASHBOARD_MOCK_DATA.combinations.find(
      ({ id }) => id === 'COMB-001',
    )!;
    const updatedFirstCombination: ParameterCombination = {
      ...firstCombination,
      parameters: { ...firstCombination.parameters, 'Fast EMA': 12 },
      statistics: {
        ...firstCombination.statistics,
        totalTrades: 111,
        pnl: 22_000,
        roi: 220,
      },
      equityCurve: {
        ...firstCombination.equityCurve,
        points: firstCombination.equityCurve.points.map((point) => ({
          ...point,
          value: point.value + 1_000,
        })),
      },
    };

    fixture.componentInstance.updateCombinationResult(updatedFirstCombination);
    fixture.detectChanges();

    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe('COMB-001');
    expect(root.querySelector('.stat-item strong')?.textContent?.trim()).toBe('111');
    expect(root.querySelectorAll('.stat-item strong')[2].textContent?.trim()).toBe('$22,000.00');
    expect(root.querySelectorAll('.stat-item strong')[2].classList.contains('positive')).toBe(true);
    expect(root.querySelector('.parameter-item dd')?.textContent?.trim()).toBe('12');
    expect(root.querySelector('.equity-panel path.equity-line')?.getAttribute('d')).not.toBe(
      initialEquityPath,
    );
    expect(root.querySelector<HTMLTableRowElement>('tbody tr')?.cells[1].textContent?.trim()).toContain(
      'COMB-001',
    );

    const secondCombination = MULTI_STRATEGY_DASHBOARD_MOCK_DATA.combinations.find(
      ({ id }) => id === 'COMB-002',
    )!;
    fixture.componentInstance.updateCombinationResult({
      ...secondCombination,
      statistics: { ...secondCombination.statistics, roi: 190 },
    });
    fixture.detectChanges();

    const rows = Array.from(root.querySelectorAll<HTMLTableRowElement>('tbody tr'));
    const rois = rows.map((row) => Number(row.cells[2].textContent?.replace('%', '')));
    const ids = rows.map((row) => row.cells[1].textContent?.trim().split(/\s+/)[0]);
    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe('COMB-001');
    expect(ids.slice(0, 2)).toEqual(['COMB-001', 'COMB-002']);
    expect(ids).toContain('COMB-001');
    expect(new Set(ids).size).toBe(MULTI_STRATEGY_DASHBOARD_MOCK_DATA.combinations.length);
    expect(rois).toEqual([...rois].sort((left, right) => right - left));
  });

  it('shows the selected combination in the details panel', () => {
    const fixture = TestBed.createComponent(MultiStrategyDashboardComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const selectedCombination = MULTI_STRATEGY_DASHBOARD_MOCK_DATA.combinations.find(
      ({ id }) => id === 'COMB-001',
    )!;
    const autoSelectButton = root.querySelector<HTMLButtonElement>('.select-top-button')!;
    expect(autoSelectButton.textContent?.trim()).toBe('Auto-select Top Combination');
    expect(autoSelectButton.title).toContain('as rankings update');
    const selectedRow = Array.from(root.querySelectorAll<HTMLTableRowElement>('tbody tr')).find(
      (row) => row.cells[1].textContent?.trim() === selectedCombination.id,
    )!;

    selectedRow.click();
    fixture.detectChanges();

    const expectedTotalTrades = new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 2,
    }).format(selectedCombination.statistics.totalTrades);
    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe(
      selectedCombination.id,
    );
    expect(root.querySelector('.combination-rank')?.textContent?.trim()).toBe(
      `Rank #${selectedRow.cells[0].textContent?.trim()}`,
    );
    expect(root.querySelector('.combination-rank')?.classList.contains('top-rank')).toBe(false);
    expect(root.querySelector('.stat-item strong')?.textContent?.trim()).toBe(expectedTotalTrades);
    expect(selectedRow.getAttribute('aria-selected')).toBe('true');
    expect(selectedRow.classList.contains('selected-combination-row')).toBe(true);

    selectedRow.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    fixture.detectChanges();
    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe(
      selectedCombination.id,
    );

    root.querySelector<HTMLButtonElement>('.select-top-button')?.click();
    fixture.detectChanges();
    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe('COMB-042');
    expect(root.querySelector('.combination-rank')?.textContent?.trim()).toBe('Rank #1');
    expect(root.querySelector('.combination-rank')?.classList.contains('top-rank')).toBe(true);
    expect(root.querySelector('.select-top-button')?.getAttribute('aria-pressed')).toBe('true');
    const topRow = Array.from(root.querySelectorAll<HTMLTableRowElement>('tbody tr')).find(
      (row) => row.cells[1].textContent?.trim() === 'COMB-042',
    );
    expect(topRow?.classList.contains('selected-combination-row')).toBe(true);
    expect(topRow?.classList.contains('best-combination-row')).toBe(true);

    root.querySelector<HTMLButtonElement>('.select-top-button')?.click();
    fixture.detectChanges();
    expect(root.querySelector('.select-top-button')?.getAttribute('aria-pressed')).toBe('false');
    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe('COMB-042');

    const firstCombination = MULTI_STRATEGY_DASHBOARD_MOCK_DATA.combinations.find(
      ({ id }) => id === 'COMB-001',
    )!;
    fixture.componentInstance.updateCombinationResult({
      ...firstCombination,
      statistics: { ...firstCombination.statistics, roi: 300 },
    });
    fixture.detectChanges();
    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe('COMB-042');
    expect(root.querySelector('.combination-rank')?.textContent?.trim()).toBe('Rank #2');
    expect(root.querySelector('.combination-rank')?.classList.contains('top-rank')).toBe(false);
    expect(topRow?.classList.contains('selected-combination-row')).toBe(true);
    expect(topRow?.classList.contains('best-combination-row')).toBe(false);

    root.querySelector<HTMLButtonElement>('.select-top-button')?.click();
    fixture.detectChanges();
    expect(root.querySelector('.select-top-button')?.getAttribute('aria-pressed')).toBe('true');
    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe('COMB-001');
    expect(root.querySelector('.combination-rank')?.textContent?.trim()).toBe('Rank #1');
    expect(root.querySelector('.combination-rank')?.classList.contains('top-rank')).toBe(true);

    const currentTopRow = Array.from(root.querySelectorAll<HTMLTableRowElement>('tbody tr')).find(
      (row) => row.cells[1].textContent?.trim() === 'COMB-001',
    )!;
    currentTopRow.click();
    fixture.detectChanges();
    expect(root.querySelector('.select-top-button')?.getAttribute('aria-pressed')).toBe('false');

    const secondCombination = MULTI_STRATEGY_DASHBOARD_MOCK_DATA.combinations.find(
      ({ id }) => id === 'COMB-002',
    )!;
    fixture.componentInstance.updateCombinationResult({
      ...secondCombination,
      statistics: { ...secondCombination.statistics, roi: 400 },
    });
    fixture.detectChanges();
    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe('COMB-001');
  });

  it('renders shared header controls and a summary-only strategy card', async () => {
    const fixture = TestBed.createComponent(MultiStrategyDashboardComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;

    expect(root.querySelector('.monitor-header app-connection-indicator')).toBeTruthy();
    const overview = root.querySelector('.strategy-overview')!;
    expect(overview.querySelector('h1, .eyebrow')).toBeNull();
    expect(overview.querySelectorAll('.overview-metric')).toHaveLength(2);
    expect(
      Array.from(overview.querySelectorAll('.overview-metric strong'), (element) =>
        element.textContent?.trim(),
      ),
    ).toEqual([MULTI_STRATEGY_DASHBOARD_MOCK_DATA.strategy.name, '120']);
    expect(overview.querySelector('app-market-data-progress [role="progressbar"]')).toBeTruthy();
    expect(root.querySelector('.best-combination-id')?.textContent?.trim()).toBe('COMB-042');
    const navigationButton = root.querySelector<HTMLAnchorElement>('app-surface-navigation a');
    expect(navigationButton?.getAttribute('href')).toBe('/');
    expect(navigationButton?.getAttribute('aria-label')).toBe('Open single-strategy monitor');
  });

  it('shows playback and disabled export controls in the header without a summary bubble', () => {
    const fixture = TestBed.createComponent(MultiStrategyDashboardComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;

    expect(root.querySelector('.multi-header-controls .play-button')?.getAttribute('aria-label')).toBe(
      'Play replay',
    );
    const exportButton = root.querySelector<HTMLButtonElement>(
      '.multi-header-controls .export-button',
    )!;
    expect(exportButton.disabled).toBe(true);
    expect(root.querySelector('.replay-step-button, .auto-stop-settings-button')).toBeNull();
    expect(root.querySelector('.multi-header-summary')).toBeNull();
    expect(root.querySelector('.monitor-header .session-summary')).toBeNull();

    exportButton.click();
    TestBed.inject(HttpTestingController).expectNone(environment.replayControlUrl);
  });

  it('collapses and expands the parameter combinations sidebar', () => {
    const fixture = TestBed.createComponent(MultiStrategyDashboardComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;

    root.querySelector<HTMLButtonElement>('.sidebar-heading .collapse-button')!.click();
    fixture.detectChanges();
    expect(root.querySelector('.parameter-sidebar .rail-label')?.textContent?.trim()).toBe(
      'PARAMETER COMBINATIONS',
    );
    expect(root.querySelectorAll('.parameter-sidebar tbody tr')).toHaveLength(0);

    root.querySelector<HTMLButtonElement>('.parameter-sidebar .collapsed-rail')!.click();
    fixture.detectChanges();
    expect(root.querySelectorAll('.parameter-sidebar tbody tr')).toHaveLength(
      MULTI_STRATEGY_DASHBOARD_MOCK_DATA.combinations.length,
    );
  });

  it('starts and pauses replay from the header play button', () => {
    const fixture = TestBed.createComponent(MultiStrategyDashboardComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const button = root.querySelector<HTMLButtonElement>('.multi-header-controls .play-button')!;
    const httpTesting = TestBed.inject(HttpTestingController);

    button.click();
    const startRequest = httpTesting.expectOne(environment.replayControlUrl);
    expect(startRequest.request.body).toEqual({ action: 'start' });
    startRequest.flush({});
    fixture.detectChanges();
    expect(button.getAttribute('aria-label')).toBe('Pause replay');

    button.click();
    const stopRequest = httpTesting.expectOne(environment.replayControlUrl);
    expect(stopRequest.request.body).toEqual({ action: 'stop' });
    stopRequest.flush({});
    fixture.detectChanges();
    expect(button.getAttribute('aria-label')).toBe('Play replay');
    httpTesting.verify();
  });
});
