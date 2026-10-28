import { expect, test } from './fixtures';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Calculadoras' }).click();
});

test('peso molecular de una fórmula cualquiera', async ({ page }) => {
  await page.getByLabel('Fórmula', { exact: true }).fill('CuSO4·5H2O');
  await page.getByRole('button', { name: 'Calcular', exact: true }).click();
  await expect(page.getByTestId('pm')).toContainText(/249\.6/);
  await page.getByLabel('Fórmula', { exact: true }).fill('Xx2');
  await page.getByRole('button', { name: 'Calcular', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText(/Elemento desconocido/);
});

test('balanceo de la combustión del propano', async ({ page }) => {
  await page.getByRole('button', { name: 'Balanceo de ecuaciones' }).click();
  await page.getByRole('button', { name: 'Balancear' }).click();
  await expect(page.getByTestId('ecuacion')).toHaveText(/C3H8 \+ 5 O2 → 3 CO2 \+ 4 H2O|C₃H₈ \+ 5 O₂ → 3 CO₂ \+ 4 H₂O/);
});

test('conversión de volumen a moles con la densidad del catálogo', async ({ page }) => {
  await page.getByRole('button', { name: 'Conversión de unidades' }).click();
  await page.getByLabel('Compuesto').selectOption('etanol');
  await page.getByLabel('Cantidad').fill('100');
  await page.getByLabel('De', { exact: true }).selectOption('mL');
  await page.getByLabel('A', { exact: true }).selectOption('mol');
  await page.getByRole('button', { name: 'Convertir' }).click();
  // 100 mL de etanol ≈ 79 g ≈ 1,7 mol
  await expect(page.getByTestId('conversion')).toContainText(/1\.7\d* mol/);
});

test('concentración: de % p/p a molaridad pide la densidad y no la inventa', async ({ page }) => {
  await page.getByRole('button', { name: 'Concentración de soluciones' }).click();
  await page.getByLabel('Densidad de la solución').fill('');
  await page.getByRole('button', { name: 'Convertir' }).click();
  await expect(page.getByTestId('pp')).toContainText('37');
  await expect(page.getByTestId('molar')).toContainText('—');
  await page.getByLabel('Densidad de la solución').fill('1.18');
  await page.getByRole('button', { name: 'Convertir' }).click();
  await expect(page.getByTestId('molar')).toContainText(/11\.9/);
});
