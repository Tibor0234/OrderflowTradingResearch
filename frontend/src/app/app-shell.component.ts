import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MarketDataSocketService } from './core/services/market-data-socket.service';

@Component({
  imports: [RouterOutlet],
  selector: 'app-root',
  template: '<router-outlet />',
  styles: [':host { display: block; height: 100dvh; min-height: 440px; }'],
})
export class AppShellComponent {
  private readonly marketSocket = inject(MarketDataSocketService);

  constructor() {
    this.marketSocket.start();
  }
}
