const SAFE_HEX = /^#[0-9a-fA-F]{6}$/;

export function safeHex(value) {
    return typeof value === 'string' && SAFE_HEX.test(value) ? value.toLowerCase() : null;
}

function rawDate(value) {
    if (!value) return '';
    if (typeof value === 'string') return value;
    return value.dateTime ?? value.date ?? '';
}

export function metadataKeys(event) {
    const uid = event.uid ?? '';
    const recurrenceId = event.recurrence_id ?? '';
    const start = rawDate(event.start);
    const keys = [];
    if (uid) {
        keys.push(`uid:${uid}|recurrence:${recurrenceId}`);
        if (start) keys.push(`uid:${uid}|start:${start}`);
    }
    if (recurrenceId) keys.push(`recurrence:${recurrenceId}`);
    return keys;
}

export function indexMetadata(items) {
    const result = new Map();
    for (const item of items ?? []) {
        const color = safeHex(item?.color);
        if (!color) continue;
        const safe = {
            color,
            text_color: safeHex(item.text_color),
            source: item.source
        };
        for (const key of metadataKeys(item)) result.set(key, safe);
    }
    return result;
}

export function eventColors(event, calendar) {
    if (calendar.inherit_event_colors === true && calendar._eventColors instanceof Map) {
        for (const key of metadataKeys(event)) {
            const metadata = calendar._eventColors.get(key);
            if (metadata) {
                return {
                    color: metadata.color,
                    textColor: metadata.text_color ?? 'inherit'
                };
            }
        }
    }
    return { color: calendar.color ?? 'inherit', textColor: 'inherit' };
}

