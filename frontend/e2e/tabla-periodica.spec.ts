import { expect, test } from './fixtures';

test('la tabla periódica muestra los 118 elementos y el detalle de uno', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Tabla periódica' }).click();
  await expect(page.locator('.elemento')).toHaveCount(118);
  await page.getByRole('button', { name: /Hierro \(Fe\)/ }).click();
  const detalle = page.locator('aside.detalle');
  await expect(detalle).toContainText('Hierro');
  await expect(detalle).toContainText('26');
});

test('buscar atenúa los elementos que no coinciden', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Tabla periódica' }).click();
  await page.getByLabel('Buscar elemento').fill('cobre');
  await expect(page.locator('.elemento:not(.atenuado)')).toHaveCount(1);
});
