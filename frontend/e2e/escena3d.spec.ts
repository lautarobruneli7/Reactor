import { expect, test } from './fixtures';

// Esta prueba usa WebGL por software (SwiftShader): es lenta, por eso es una sola y con tiempo de sobra.
test.use({ launchOptions: { args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] } });

test('el reactor 3D dibuja un canvas cuando el navegador tiene WebGL', async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto('/');
  const escena = page.locator('.escena3d');
  await expect(escena).toBeVisible();
  await expect(escena.locator('canvas')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText('no tiene WebGL')).toHaveCount(0);
});
