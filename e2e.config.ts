import type { E2EConfig } from 'e2e';

// Official shape from `e2e init --engine none --gateway none`.
// No model / no browser engine: AI keys are not required.
// Meaningful scenarios wait for the v0.3.0 minimal UI (see docs/plan).
// Until then `e2e run` fails with NO_TESTS by design (do not use --pass-with-no-tests).
export default {
  targets: [{ name: 'default', platform: 'custom' }],
} satisfies E2EConfig;
