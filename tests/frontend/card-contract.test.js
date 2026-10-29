import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const card = await readFile(new URL('../../src/card.js', import.meta.url), 'utf8');
const styles = await readFile(new URL('../../src/card.styles.js', import.meta.url), 'utf8');

test('metadata is opt-in and unavailable backend keeps normal event request alive', () => {
    assert.match(card, /calendar\.inherit_event_colors === true/);
    assert.match(card, /google_calendar_colors\/get_events/);
    assert.match(card, /\.catch\(\(\) => \(\{ events: \[\] \}\)\)/);
});

test('family filter runs before events are added or colored', () => {
    const filter = card.indexOf('this._isFilterEvent(event, calendar.filter');
    const add = card.indexOf('this._addEvent(event, startDate');
    assert.ok(filter > 0 && add > filter);
});

test('card-mod border variable and scoped contrast variable are retained', () => {
    assert.match(card, /--border-color: \$\{event\.colors\[0\]\}/);
    assert.match(card, /--event-text-color: \$\{event\.textColors\[0\]\}/);
    assert.match(styles, /color: var\(--event-text-color, inherit\)/);
});

test('all existing global configuration paths remain in the inherited card', () => {
    for (const option of [
        'showDescription', 'showLocation', 'hidePastEvents', 'combineSimilarEvents',
        'weather', 'compact', 'columns', 'actions', 'filterText', 'replaceTitleText'
    ]) {
        assert.ok(card.includes(option), `missing existing option: ${option}`);
    }
});

