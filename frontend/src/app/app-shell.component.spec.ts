import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { MarketDataSocketService } from './core/services/market-data-socket.service';
import { AppShellComponent } from './app-shell.component';

describe('AppShellComponent', () => {
  it('starts the WebSocket from the application shell for any route', () => {
    const start = vi.fn();
    TestBed.configureTestingModule({
      imports: [AppShellComponent],
      providers: [{ provide: MarketDataSocketService, useValue: { start } }],
    });

    TestBed.createComponent(AppShellComponent);

    expect(start).toHaveBeenCalledOnce();
  });
});
