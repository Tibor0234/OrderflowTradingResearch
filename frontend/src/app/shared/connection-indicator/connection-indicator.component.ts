import { Component, computed, inject } from '@angular/core';
import { MarketDataSocketService } from '../../core/services/market-data-socket.service';

@Component({
  selector: 'app-connection-indicator',
  templateUrl: './connection-indicator.component.html',
  styleUrl: './connection-indicator.component.scss',
})
export class ConnectionIndicatorComponent {
  private readonly marketSocket = inject(MarketDataSocketService);

  protected readonly connectionStatus = this.marketSocket.status;
  protected readonly connectionLabel = computed(() => {
    switch (this.connectionStatus()) {
      case 'connected':
        return this.marketSocket.series().candles.length > 0
          ? 'LIVE'
          : 'CONNECTED · WAITING FOR DATA';
      case 'connecting':
        return 'CONNECTING…';
      case 'error':
        return this.marketSocket.error() ?? 'BACKEND UNAVAILABLE';
      case 'closed':
        return 'DISCONNECTED';
      default:
        return 'IDLE';
    }
  });
}
