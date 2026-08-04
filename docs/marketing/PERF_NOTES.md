# Marketing perf notes

- 2026-08: Homepage Google Fonts CSS (`fonts.googleapis.com` via `globals.css` `@import`) replaced with self-hosted `next/font` (Fraunces + DM Mono). Remaining Lighthouse items deferred: Next 14 unconditional legacy polyfill chunk (~11 KiB), ~63ms main-thread JS task, and Google Fonts on noindex static `/board*` / `/forecast-engine` HTML demos.
