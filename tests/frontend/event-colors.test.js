import assert from 'node:assert/strict';
import test from 'node:test';

import { eventColors, indexMetadata, metadataKeys, safeHex } from '../../src/event-colors.js';

const event = {
    uid: 'stable@example.com',
    recurrence_id: 'instance-1',
    start: { dateTime: '2026-11-01T01:30:00-04:00' }
};

test('inherit_event_colors uses matching event metadata', () => {
    const calendar = {
        inherit_event_colors: true,
        color: '#999999',
        _eventColors: indexMetadata([{ ...event, color: '#AABBCC', text_color: '#000000' }])
    };
    assert.deepEqual(eventColors(event, calendar), { color: '#aabbcc', textColor: '#000000' });
});

test('option absent preserves ordinary configured calendar color', () => {
    assert.deepEqual(eventColors(event, { color: 'var(--my-color)' }), {
        color: 'var(--my-color)',
        textColor: 'inherit'
    });
});

test('missing backend follows configured and normal fallback levels', () => {
    assert.equal(eventColors(event, { inherit_event_colors: true, color: '#010203' }).color, '#010203');
    assert.equal(eventColors(event, { inherit_event_colors: true }).color, 'inherit');
});

test('invalid metadata is rejected and cannot inject CSS', () => {
    const calendar = {
        inherit_event_colors: true,
        color: '#010203',
        _eventColors: indexMetadata([{ ...event, color: 'red;display:none' }])
    };
    assert.equal(eventColors(event, calendar).color, '#010203');
    assert.equal(safeHex('#123abc'), '#123abc');
    assert.equal(safeHex('#fff'), null);
});

test('stable identifiers distinguish identical titles and times', () => {
    const second = { ...event, uid: 'other@example.com' };
    assert.notDeepEqual(metadataKeys(event), metadataKeys(second));
});

test('separate metadata maps prevent color leakage between events', () => {
    const first = { ...event, uid: 'first@example.com' };
    const second = { ...event, uid: 'second@example.com' };
    const calendar = {
        inherit_event_colors: true,
        _eventColors: indexMetadata([
            { ...first, color: '#ff0000' },
            { ...second, color: '#00ff00' }
        ])
    };
    assert.equal(eventColors(first, calendar).color, '#ff0000');
    assert.equal(eventColors(second, calendar).color, '#00ff00');
});

