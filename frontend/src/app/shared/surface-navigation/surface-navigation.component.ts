import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  imports: [RouterLink],
  selector: 'app-surface-navigation',
  templateUrl: './surface-navigation.component.html',
  styleUrl: './surface-navigation.component.scss',
})
export class SurfaceNavigationComponent {
  readonly target = input.required<string>();
  readonly label = input.required<string>();
}
