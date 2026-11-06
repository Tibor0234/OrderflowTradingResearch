export interface StrategyInformation {
  readonly name: string;
  readonly totalParameterCombinations: number;
}

export interface PerformanceStatistics {
  readonly totalTrades: number;
  readonly winrate: number;
  readonly pnl: number;
  readonly roi: number;
  readonly maxDrawdown: number;
  readonly profitFactor: number;
}

export interface EquityCurvePoint {
  readonly timestamp: number;
  readonly value: number;
}

export interface EquityCurveData {
  readonly startingBalance: number;
  points: readonly EquityCurvePoint[];
}

export type ParameterValue = boolean | number | string;

export interface ParameterCombination {
  readonly id: string;
  parameters: Readonly<Record<string, ParameterValue>>;
  readonly statistics: PerformanceStatistics;
  readonly equityCurve: EquityCurveData;
}

export interface MarketDataProcessingProgress {
  readonly percentage: number;
  readonly displayValue: string;
}

export interface MultiStrategyDashboardData {
  readonly strategy: StrategyInformation;
  readonly marketDataProgress: MarketDataProcessingProgress;
  readonly combinations: readonly ParameterCombination[];
}
