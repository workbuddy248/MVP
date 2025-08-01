import { Page, Locator } from '@playwright/test';

export async function robustClick(locator: Locator, retries = 3, delay = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      await locator.click({ timeout: 10000 });
      return;
    } catch (e) {
      if (i === retries - 1) throw e;
      await new Promise(res => setTimeout(res, delay));
    }
  }
}

export async function robustFill(locator: Locator, value: string, retries = 3, delay = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      await locator.fill(value, { timeout: 10000 });
      return;
    } catch (e) {
      if (i === retries - 1) throw e;
      await new Promise(res => setTimeout(res, delay));
    }
  }
}

export async function robustNavigate(page: Page, url: string, retries = 3, delay = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 150000 });
      return;
    } catch (e) {
      if (i === retries - 1) throw e;
      await new Promise(res => setTimeout(res, delay));
    }
  }
}

export async function takeScreenshot(page: Page, name: string) {
  await page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
}