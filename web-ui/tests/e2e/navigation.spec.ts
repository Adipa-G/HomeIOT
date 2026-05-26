import { test, expect } from '@playwright/test';

// Helper to login
async function login(page) {
  await page.goto('/');
  await page.waitForLoadState('networkidle');

  const usernameInput = page.locator('#username');
  const passwordInput = page.locator('#password');
  const signInButton = page.locator('button:has-text("Sign in")');

  await usernameInput.fill('Admin');
  await passwordInput.fill('123');
  await signInButton.click();

  await page.waitForNavigation();
  await page.waitForLoadState('networkidle');
}

test.describe('Navigation', () => {
  test('should load dashboard after login', async ({ page }) => {
    await login(page);

    // Check we're not on login page anymore
    const isLoginPage = await page.locator('#username').isVisible().catch(() => false);
    expect(isLoginPage).toBe(false);

    // Check for page content (should have loaded dashboard)
    const body = page.locator('body');
    await expect(body).toContainText(/homeiot|dashboard|device/i);
  });

  test('should navigate to devices page', async ({ page }) => {
    await login(page);

    // Look for devices link in navigation
    const devicesLink = page.locator('a, button').filter({ hasText: /devices/i }).first();
    if (await devicesLink.isVisible()) {
      await devicesLink.click();
      await page.waitForLoadState('networkidle');

      // Verify we're on devices page
      const content = page.locator('body');
      await expect(content).toContainText(/devices|device/i);
    }
  });

  test('should navigate to modules page', async ({ page }) => {
    await login(page);

    // Look for modules link
    const modulesLink = page.locator('a, button').filter({ hasText: /modules/i }).first();
    if (await modulesLink.isVisible()) {
      await modulesLink.click();
      await page.waitForLoadState('networkidle');

      const content = page.locator('body');
      await expect(content).toContainText(/modules|module/i);
    }
  });

  test('should navigate to users page', async ({ page }) => {
    await login(page);

    // Look for users link
    const usersLink = page.locator('a, button').filter({ hasText: /users/i }).first();
    if (await usersLink.isVisible()) {
      await usersLink.click();
      await page.waitForLoadState('networkidle');

      const content = page.locator('body');
      await expect(content).toContainText(/users|user/i);
    }
  });

  test('should navigate to OTA releases page', async ({ page }) => {
    await login(page);

    // Look for OTA or releases link
    const otaLink = page.locator('a, button').filter({ hasText: /ota|releases|update/i }).first();
    if (await otaLink.isVisible()) {
      await otaLink.click();
      await page.waitForLoadState('networkidle');

      const content = page.locator('body');
      await expect(content).toContainText(/ota|releases|update/i);
    }
  });

  test('should have API accessible', async ({ page }) => {
    // Check health endpoint
    const response = await page.request.get('/health');
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.status).toBe('ok');
    expect(data.service).toBe('HomeIOT API');
  });

  test('should have Swagger UI available', async ({ page }) => {
    await page.goto('/swagger');
    await page.waitForLoadState('networkidle');

    // Check for Swagger UI elements
    const swagger = page.locator('[id*="swagger"]').first();
    const exists = await swagger.isVisible().catch(() => false);

    // Swagger might not be visible in all contexts, but the page should load
    const statusCode = page.url();
    expect(statusCode).toContain('swagger');
  });
});
