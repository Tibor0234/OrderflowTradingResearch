import { Routes } from '@angular/router';
import { SingleStrategyDashboardComponent } from './single-strategy-dashboard/single-strategy-dashboard.component';
import { MultiStrategyDashboardComponent } from './multi-strategy-dashboard/multi-strategy-dashboard.component';

export const routes: Routes = [
  { path: '', pathMatch: 'full', component: SingleStrategyDashboardComponent },
  { path: 'multi-strategy-monitor', component: MultiStrategyDashboardComponent },
  { path: '**', redirectTo: '' },
];
