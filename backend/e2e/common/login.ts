import { Page, expect } from '@playwright/test';
import { robustClick, robustFill, takeScreenshot } from '../utils/actions';

export async function login(page: Page, username: string, password: string) {
  // Wait for Username and Password fields to be visible
  const usernameField = page.locator('[aria-label="Username"], [data-test-name="username"], [data-test-id="username"], input[name="username"], input[type="text"]');
  const passwordField = page.locator('[aria-label="Password"], [data-test-name="password"], [data-test-id="password"], input[name="password"], input[type="password"]');
  await expect(usernameField).toBeVisible({ timeout: 600000 });
  await expect(passwordField).toBeVisible({ timeout: 600000 });
  await robustFill(usernameField, username);
  await robustFill(passwordField, password);
  await takeScreenshot(page, 'before-login-click');
  // Try button selectors first, then fallback to text selector
  let loginButton = page.locator('[aria-label="Login"], [data-test-name="login"], [data-test-id="login"], button[type="submit"]');
  if (!(await loginButton.isVisible({ timeout: 10000 }))) {
    loginButton = page.getByRole('button', { name: /login/i });
  }
  await robustClick(loginButton);
}