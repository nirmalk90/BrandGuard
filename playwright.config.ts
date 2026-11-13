import { defineConfig, devices } from '@playwright/test'

const external = process.env.BRANDGUARD_TEST_URL
const baseURL = external || 'http://127.0.0.1:8181'
const python = process.env.BRANDGUARD_PYTHON || (process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python')

export default defineConfig({
  testDir: './tests/browser',
  use: { baseURL, trace: 'retain-on-failure', ...devices['Desktop Chrome'] },
  webServer: external ? undefined : {
    command: `"${python}" -m alembic upgrade head && "${python}" -m uvicorn backend.main:app --port 8181`,
    env: { DATABASE_URL: process.env.BRANDGUARD_TEST_DATABASE_URL || 'sqlite:///./playwright.sqlite', SECURE_COOKIES: '0', LLM_API_KEY: '' },
    url: baseURL + '/health',
    reuseExistingServer: false,
  },
})
