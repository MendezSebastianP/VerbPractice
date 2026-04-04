# Accessibility Audit

## Shipped In This Pass
- Added a visible-on-focus skip link to jump past the fixed header.
- Added polite live announcements for toast feedback.
- Added `aria-current` to the SPA navbar.
- Added `role="tab"` and `aria-selected` to verb-lab and admin workbench mode switches.
- Kept focus flow tight after answer submits and conjugation table moves.

## Manual Checks Completed
- Keyboard path through login, dashboard, words, verb lab, chat, and monitor.
- Visible focus rings on buttons, inputs, selects, and textarea fields.
- Toast and in-page feedback remain readable in light, dark, and arcade modes.
- Fixed-header layout still allows keyboard users to reach content quickly.

## Remaining Gaps
- Full screen-reader pass with NVDA or VoiceOver is still pending.
- Color-contrast spot checks were done visually, but not with an automated axe/pa11y pass yet.
- The admin workbench still needs richer inline validation text for malformed edits.
- Charts are not present yet, so there was no graph accessibility review to complete.
