import { expect, test } from './fixtures';

test.describe('Reactor: estimación vs. medido', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Cargar ejemplo' }).click();
    await expect(page.locator('.medidor-num')).toHaveText('85');
  });

  test('el ejemplo da 85 y se marca como ESTIMACIÓN', async ({ page }) => {
    await expect(page.getByTestId('origen')).toHaveText(/estimaci[oó]n/i);
    await expect(page.locator('.origen-tag.modelo').first()).toBeVisible();
    // el estado de validación del modelo se muestra, no se esconde
    await expect(page.getByText(/sin validar/i).first()).toBeVisible();
  });

  test('una pureza medida pasa el resultado a MIXTO y el rendimiento medido a MEDIDO', async ({ page }) => {
    await page.getByRole('button', { name: /Ver detalle técnico/ }).click();
    await page.getByLabel('Pureza medida').fill('99.4');
    await expect(page.getByTestId('origen')).toHaveText(/mixto/i);
    await page.getByLabel('Rendimiento medido').fill('80, 82, 78');
    await expect(page.getByTestId('origen')).toHaveText(/medido/i);
    await expect(page.locator('.origen-tag.experimental').first()).toBeVisible();
  });

  test('la especificación incompleta no se da por cumplida', async ({ page }) => {
    await page.getByRole('button', { name: /Ver detalle técnico/ }).click();
    await page.getByLabel('Pureza medida').fill('99.4');
    // la pureza cumple, pero hay parámetros sin límite cargado: no puede decir "cumple"
    const global = page.locator('.global-spec');
    await expect(global).toContainText(/incompleta/i);
    await expect(global).not.toContainText(/^Cumple/);
    await expect(page.locator('.estado.sin_limite').first()).toBeVisible();
    await expect(page.locator('tr', { hasText: 'Pureza del producto' }).locator('.estado')).toHaveText(/cumple/i);
  });

  test('la incertidumbre muestra intervalos y avisa lo que no cubre', async ({ page }) => {
    await page.getByLabel('Calcular incertidumbre (Monte Carlo)').check();
    const tabla = page.locator('.tabla-incert');
    await expect(tabla).toBeVisible();
    await expect(tabla.locator('tbody tr')).toHaveCount(4);
    await expect(page.locator('.notas-incert')).toContainText(/no incluye cu[aá]nto se aparta el modelo/i);
  });
});
