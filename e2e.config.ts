import type { E2EConfig } from 'e2e';
import { web } from '@e2e-dev/web';

// No AI model: tests use screen/expect only (no agent.* steps).
// App is the localhost memory UI (no AWS).
export default {
  tests: 'tests/**/*.e2e.ts',
  workers: 1,
  targets: [
    {
      name: 'default',
      engine: web({ browser: 'chromium' }),
      app: {
        url: 'http://127.0.0.1:8765',
        readyUrl: 'http://127.0.0.1:8765/',
        command: {
          executable: 'mise',
          args: [
            'exec',
            '--',
            'uv',
            'run',
            'python',
            'scripts/serve-ui.py',
            '--host',
            '127.0.0.1',
            '--port',
            '8765',
            '--backend',
            'memory',
          ],
          env: {
            UI_BACKEND: 'memory',
          },
          startupTimeout: 60_000,
          log: '.e2e/logs/ui.log',
          reuseExisting: true,
        },
      },
    },
  ],
} satisfies E2EConfig;
