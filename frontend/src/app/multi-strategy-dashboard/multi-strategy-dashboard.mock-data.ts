import {
  MultiStrategyDashboardData,
  ParameterCombination,
} from './multi-strategy-dashboard.models';

const STARTING_BALANCE = 10_000;
const COMBINATION_COUNT = 120;
const BEST_COMBINATION_INDEX = 41;
const EQUITY_POINT_COUNT = 96;
const DAY_IN_MILLISECONDS = 86_400_000;
const EQUITY_START_TIMESTAMP = Date.UTC(2025, 0, 1);

function createEquityCurve(index: number, pnl: number) {
  const points = Array.from({ length: EQUITY_POINT_COUNT }, (_, pointIndex) => {
    const progress = pointIndex / (EQUITY_POINT_COUNT - 1);
    const cycle = Math.sin(Math.PI * progress);
    const volatility =
      Math.sin((pointIndex + index) * 0.42) * 180 * cycle +
      Math.cos((pointIndex + index) * 0.19) * 90 * cycle;

    return {
      timestamp: EQUITY_START_TIMESTAMP + pointIndex * DAY_IN_MILLISECONDS,
      value: Number((STARTING_BALANCE + pnl * progress + volatility).toFixed(2)),
    };
  });

  return { startingBalance: STARTING_BALANCE, points };
}

function createCombination(index: number): ParameterCombination {
  const isBest = index === BEST_COMBINATION_INDEX;
  const roi = isBest
    ? 184.2
    : Number((((index * 37) % 91) - 32 + (index % 5) * 0.2).toFixed(1));
  const pnl = isBest ? 18_420 : Number((roi * 100).toFixed(2));

  return {
    id: `COMB-${String(index + 1).padStart(3, '0')}`,
    parameters: {
      'Fast EMA': 5 + (index % 14),
      'Slow EMA': 18 + (index % 38),
      'Entry Threshold': Number((0.25 + (index % 16) * 0.05).toFixed(2)),
      'Stop Loss': `${(0.5 + (index % 15) * 0.1).toFixed(1)}%`,
      'Take Profit': `${(1 + (index % 20) * 0.2).toFixed(1)}%`,
    },
    statistics: {
      totalTrades: isBest ? 324 : 85 + ((index * 37) % 450),
      winrate: isBest ? 68.5 : 37 + ((index * 17) % 48),
      pnl,
      roi,
      maxDrawdown: isBest ? 7.8 : Number((3.2 + ((index * 11) % 220) / 10).toFixed(1)),
      profitFactor: isBest
        ? 2.18
        : Number((0.78 + ((index * 17) % 125) / 100).toFixed(2)),
    },
    equityCurve: createEquityCurve(index, pnl),
  };
}

const combinations = Array.from({ length: COMBINATION_COUNT }, (_, index) =>
  createCombination(index),
);

export const MULTI_STRATEGY_DASHBOARD_MOCK_DATA: MultiStrategyDashboardData = {
  strategy: {
    name: 'Orderflow Momentum',
    totalParameterCombinations: COMBINATION_COUNT,
  },
  marketDataProgress: { percentage: 68.4, displayValue: '4/20' },
  combinations,
};
