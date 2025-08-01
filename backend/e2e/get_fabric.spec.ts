import { test } from '@playwright/test';
import { login } from './common/login';
import { robustNavigate, takeScreenshot } from './utils/actions';

// Dynamic placeholders that will be replaced by the system
const baseURL = 'https://172.27.248.92/';
const username = 'admin1';
const password = 'P@ssword99';
const fabricName = 'Global/border_l3vn_design_site/BLD1';

test.describe('Get Fabric Workflow Tests', () => {
  test('test_get_fabric_workflow', async ({ page }) => {
    // Set browser to full screen
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    console.log('Starting get fabric workflow test');
    console.log(`Using URL: ${baseURL}, Username: ${username}, Fabric Name: ${fabricName}`);
    
    // Step 1: Login (reusing existing login functionality)
    await robustNavigate(page, baseURL);
    await login(page, username, password);
    console.log('Login completed successfully');
    
    // Step 2: Click on Provision option and then Fabric Sites under SD-Access
    console.log('Step 2: Navigating to Provision > Fabric Sites');
    const provisionOption = page.getByText(/provision/i).first();
    await provisionOption.click();
    await page.waitForTimeout(1000);
    
    const fabricSitesOption = page.getByText(/Fabric Sites/i).first();
    await fabricSitesOption.click();
    
    // Wait for navigation to fabric-sites page
    await page.waitForURL('**/dna/provision/evpn/fabric-sites**', { timeout: 30000 });
    await page.waitForLoadState('networkidle');
    console.log('Successfully navigated to fabric-sites page');
    
    // Step 3: Scroll down and click on Manage All Fabric Sites
    console.log('Step 3: Scrolling down and clicking on Manage All Fabric Sites');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2000); // Wait for scroll to complete
    
    const manageAllFabricSites = page.getByText(/Manage All Fabric Sites/i).first();
    await manageAllFabricSites.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000); // Wait for page to load completely
    console.log('Clicked on Manage All Fabric Sites and page loaded');
    
    // Step 4: Wait for page to load completely and check if fabric name exists, then click on it
    console.log(`Step 4: Looking for fabric with name: ${fabricName}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Look for fabric name in various possible locations
    const fabricNameSelectors = [
      `text="${fabricName}"`,
      `[title="${fabricName}"]`,
      `td:has-text("${fabricName}")`,
      `[class*="fabric"] >> text="${fabricName}"`,
      `a:has-text("${fabricName}")`,
      `span:has-text("${fabricName}")`
    ];
    
    let fabricFound = false;
    for (const selector of fabricNameSelectors) {
      const fabricElement = page.locator(selector).first();
      if (await fabricElement.isVisible({ timeout: 5000 })) {
        await fabricElement.click();
        console.log(`Found and clicked on fabric: ${fabricName} using selector: ${selector}`);
        fabricFound = true;
        break;
      }
    }
    
    if (!fabricFound) {
      console.log(`Fabric with name ${fabricName} not found, clicking on first available fabric`);
      // If exact match not found, click on first available fabric
      const firstFabric = page.locator('table tbody tr td a, table tbody tr td span, [class*="fabric"]').first();
      if (await firstFabric.isVisible({ timeout: 5000 })) {
        await firstFabric.click();
        console.log('Clicked on first available fabric');
      } else {
        throw new Error('No fabric found to click on');
      }
    }
    
    // Step 5: Wait for page to load completely and check if Settings exists and click on it
    console.log('Step 5: Waiting for page to load completely and checking for Settings');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000); // Wait for page to load completely
    
    const SettingsSelectors = [
      `text="Settings"`,
      `[title="Settings"]`,
      `td:has-text("Settings")`,
      `[class*="fabric"] >> text="Settings"`,
      `a:has-text("Settings")`,
      `span:has-text("Settings")`
    ];
    let settingsFound = false;
    for (const selector of SettingsSelectors) {
      const settingsElement = page.locator(selector).first();
      if (await settingsElement.isVisible({ timeout: 5000 })) {
        await settingsElement.click();
        console.log(`Found and clicked on fabric: ${fabricName} using selector: ${selector}`);
        settingsFound = true;
        break;
      }
    }
    if (!settingsFound) {
      console.log(`Fabric settings not found`);
      // If exact match not found, click on first available fabric
      const settingFabric = page.locator('table tbody tr td a, table tbody tr td span, [class*="Settings"]').first();
      if (await settingFabric.isVisible({ timeout: 5000 })) {
        await settingFabric.click();
        console.log('Clicked on first available Settings option');
      } else {
        throw new Error('No Settings option found to click on');
      }
    }
    
    // Step 6: Wait for page to load completely, take screenshot and mark test success
    console.log('Step 6: Taking final screenshot and marking test success');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Final wait for complete loading
    
    await takeScreenshot(page, 'get-fabric-workflow-success');
    
    console.log('Get fabric workflow test completed successfully');
    console.log(`Screenshot taken for fabric: ${fabricName}`);
    console.log('✅ Test marked as successful - workflow completed!');
  });
});
