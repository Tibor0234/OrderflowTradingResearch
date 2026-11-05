import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type ReplayAction = 'start' | 'stop';

@Injectable({ providedIn: 'root' })
export class ReplayControlService {
  private readonly http = inject(HttpClient);

  setReplayState(action: ReplayAction): Observable<void> {
    return this.http.post<void>(environment.replayControlUrl, { action });
  }
}
