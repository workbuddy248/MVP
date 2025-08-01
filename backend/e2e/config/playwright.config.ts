import { defineConfig } from '@playwright/test';

export default defineConfig({
  timeout: 300 * 1000, // 300 seconds
  expect: {
    timeout: 10000,
  },
  retries: 1,
  use: {
    actionTimeout: 300 * 1000, // 300 seconds
    navigationTimeout: 250 * 1000, // 250 seconds
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    baseURL: 'https://172.27.248.92/',
    headless: false, // run in headed mode
    ignoreHTTPSErrors: true, // allow self-signed certs
  },
  reporter: [['list'], ['html', { outputFolder: 'playwright-report' }]],
});

