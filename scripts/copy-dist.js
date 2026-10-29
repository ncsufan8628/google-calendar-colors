import { copyFile, mkdir } from 'node:fs/promises';

await mkdir('custom_components/google_calendar_colors/www', { recursive: true });
await copyFile(
    'dist/week-planner-card.js',
    'custom_components/google_calendar_colors/www/week-planner-card.js'
);
