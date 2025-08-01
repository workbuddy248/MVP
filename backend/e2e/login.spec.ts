import { test, expect } from '@playwright/test';
import { login } from './common/login';
import { robustNavigate, takeScreenshot } from './utils/actions';

const baseURL = 'https://172.27.248.92/';

test.describe('Login Tests', () => {
  test('test_valid_login', async ({ page }) => {
    console.log('Starting valid login test');
    await robustNavigate(page, baseURL);
    await login(page, "admin1", "P@ssword99");
    await takeScreenshot(page, 'after-valid-login');
    // Wait up to 3 minutes for home page and check for welcome text (case-insensitive, partial match, US spelling)
    await expect(page.getByText(/Welcome to Catalyst Center/i)).toBeVisible({ timeout: 180000 });
    console.log('Valid login test passed');
  });
});