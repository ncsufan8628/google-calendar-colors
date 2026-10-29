# Development

The frontend starts from upstream week-planner-card 1.14.1 at commit
`243c007eb3ef50292fdbc7e5dc4e5eba18ca15ac`. Keep upstream changes separate from the small
color patch in `src/event-colors.js` and the calls in `src/card.js`.

## Commands

```bash
python -m pytest
ruff check custom_components tests/backend
pyright
npm ci
npm test
npm run build
python scripts/validate_hacs.py
```

`npm run build` writes the optimized artifact both to `dist/` and
`custom_components/google_calendar_colors/www/`. Commit the latter for HACS installs.
Pyright checks the runtime modules; `config_flow.py` is covered by Ruff/tests and excluded
because Home Assistant's dynamic `domain=` config-flow registration is not representable
without installing the full Core type environment.

When updating upstream, verify the REST event fields, event combine/filter code,
`--border-color`, dialog/actions, editor, and all responsive styles. Then run the manual
verification checklist in the README on light and dark themes and on TouchKio.

