// @ts-check
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  timeout: 30000,
  retries: 0,
  use: {
    baseURL: 'http://localhost:8889',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'python3 -m http.server 8889',
    port: 8889,
    reuseExistingServer: true,
  },
});
