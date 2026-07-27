/* AISMAT Command Deck — Elevation (shadows + glows)
   Dark-first: surfaces are separated by hairline BORDERS first, deep diffuse
   shadows second. Glow is reserved for LIVE / focused / active instruments —
   it is a signal, not decoration. Keep glow off static content. */
:root {
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-sm: 0 2px 6px rgba(0, 0, 0, 0.45);
  --shadow-md: 0 8px 24px rgba(2, 6, 12, 0.5);
  --shadow-lg: 0 20px 48px rgba(2, 6, 12, 0.6);
  --shadow-xl: 0 32px 72px rgba(2, 6, 12, 0.66);

  /* Panel: faint top inner highlight + drop for instrument depth */
  --shadow-panel: inset 0 1px 0 rgba(255, 255, 255, 0.03), 0 12px 32px rgba(2, 6, 12, 0.42);

  /* Glows (signal only) */
  --glow-cyan: 0 0 0 1px rgba(51, 222, 205, 0.35), 0 0 18px rgba(51, 222, 205, 0.22);
  --glow-gold: 0 0 0 1px rgba(255, 203, 92, 0.35), 0 0 18px rgba(255, 203, 92, 0.20);
  --glow-pass: 0 0 16px rgba(67, 213, 133, 0.28);
  --glow-warn: 0 0 16px rgba(253, 180, 62, 0.28);
  --glow-fail: 0 0 16px rgba(255, 107, 107, 0.32);

  /* Focus ring (2px ring; offset variant adds a bg gap first) */
  --ring: 0 0 0 var(--border-width-focus) var(--focus-ring);
  --ring-offset: 0 0 0 2px var(--bg-app), 0 0 0 4px var(--focus-ring);
  --ring-glow: 0 0 0 1px var(--focus-ring), 0 0 14px rgba(51, 222, 205, 0.35);
}
