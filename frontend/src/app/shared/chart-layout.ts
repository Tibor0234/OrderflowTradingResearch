export const CHART_PLOT_LEFT = 30;
export const CHART_PLOT_RIGHT = 952;

export function chartPointX(index: number, pointCount: number): number {
  return CHART_PLOT_LEFT + ((index + 0.5) / pointCount) * (CHART_PLOT_RIGHT - CHART_PLOT_LEFT);
}
