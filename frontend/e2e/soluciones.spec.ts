import { expect, test } from './fixtures';

test('HCl 37 % p/p: la concentración no se confunde con la pureza', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Reacción').selectOption({ label: 'Neutralización de ácido clorhídrico con hidróxido de sodio' });

  await page.getByPlaceholder('Buscar nombre o fórmula').first().fill('clorhidrico');
  await page.locator('.fila-compuesto', { hasText: 'Ácido clorhídrico' }).click();
  await page.getByPlaceholder('Buscar nombre o fórmula').first().fill('hidroxido de sodio');
  await page.locator('.fila-compuesto', { hasText: 'Hidróxido de sodio' }).click();

  // 1 mol neto de cada uno
  await page.getByLabel('Unidad de Ácido clorhídrico').selectOption('mol');
  await page.getByLabel('Cantidad de Ácido clorhídrico').fill('1');
  await page.getByLabel('Unidad de Hidróxido de sodio').selectOption('mol');
  await page.getByLabel('Cantidad de Hidróxido de sodio').fill('1');
  await page.getByLabel('Pureza de Ácido clorhídrico').fill('100');
  await page.getByLabel('Pureza de Hidróxido de sodio').fill('100');

  // el HCl viene en solución al 37 % p/p: hay que pesar 98,5 g de material para tener 1 mol de HCl
  await page.getByLabel('Ácido clorhídrico viene en solución').check();
  await expect(page.locator('.item-resuelto', { hasText: '37.0 % es ácido clorhídrico' })).toContainText(/98\.54 g de material/);
  await expect(page.getByText('de 58.4 g teóricos')).toBeVisible();
  await expect(page.locator('.alerta.info', { hasText: 'en solución' })).toBeVisible();
});

test('mL de una solución sin densidad: el error lo explica en vez de inventar un valor', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Reacción').selectOption({ label: 'Neutralización de ácido clorhídrico con hidróxido de sodio' });
  await page.getByPlaceholder('Buscar nombre o fórmula').first().fill('clorhidrico');
  await page.locator('.fila-compuesto', { hasText: 'Ácido clorhídrico' }).click();
  await page.getByPlaceholder('Buscar nombre o fórmula').first().fill('hidroxido de sodio');
  await page.locator('.fila-compuesto', { hasText: 'Hidróxido de sodio' }).click();
  await page.getByLabel('Unidad de Ácido clorhídrico').selectOption('mL');
  await page.getByLabel('Ácido clorhídrico viene en solución').check();
  await expect(page.locator('.alerta.bad')).toContainText(/densidad de esa soluci[oó]n/i);
  await page.getByLabel('Densidad de Ácido clorhídrico').fill('1.18');
  // con la densidad informada el error desaparece y hay resultado (otras alertas, como la pureza, pueden seguir)
  await expect(page.locator('.alerta.bad', { hasText: /densidad/i })).toHaveCount(0);
  await expect(page.locator('.medidor-num')).not.toHaveText('--');
});
