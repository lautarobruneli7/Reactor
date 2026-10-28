import { expect, test } from './fixtures';

// Modo local (sin login): un solo usuario administrador, así que puede ver la cola pero no decidir sobre sus propios ensayos.
// La revisión con dos personas está cubierta en backend/tests/test_aceptacion.py y test_auth.py.
test.describe('Aceptación de ensayos', () => {
  test('un ensayo nuevo aparece en «Por revisar» y quien lo hizo no puede decidir', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Cargar ejemplo' }).click();
    await expect(page.locator('.medidor-num')).toHaveText('85');

    const lote = `ACE-${Date.now()}`;
    await page.getByRole('button', { name: 'Guardar ensayo' }).click();
    await page.getByLabel(/Lote/).fill(lote);
    await page.getByRole('button', { name: 'Guardar', exact: true }).click();
    await expect(page.getByRole('button', { name: '✓ Guardado' })).toBeVisible();

    await page.getByRole('button', { name: /^Aceptación/ }).click();
    await expect(page.getByRole('heading', { name: 'Aceptación de ensayos' })).toBeVisible();

    const porRevisar = page.getByRole('button', { name: /Por revisar/ });
    await expect(porRevisar).toHaveAttribute('aria-pressed', 'true');
    await expect(porRevisar.locator('.contador-num')).not.toHaveText('0');

    const fila = page.locator('button.cola-item', { hasText: lote });
    await expect(fila).toBeVisible();
    await expect(fila).toContainText('Tuyo');
    await fila.click();

    const panel = page.getByRole('region', { name: /^Ensayo \d{3}$/ });
    await expect(panel).toContainText(lote);
    await expect(panel).toContainText('Lo hiciste vos');
    await expect(panel).toContainText(/lo revisa y lo aprueba otra persona de calidad/i);
    await expect(panel.getByRole('button', { name: 'Marcar revisado' })).toHaveCount(0);
    await expect(panel.getByRole('button', { name: 'Aprobar' })).toHaveCount(0);

    // comentar sí se puede, y no cambia el estado
    await panel.getByLabel('Comentario').fill('pesada con balanza B');
    await panel.getByRole('button', { name: 'Comentar' }).click();
    await expect(panel.locator('.eventos')).toContainText('pesada con balanza B');
    await expect(page.getByRole('status').filter({ hasText: /Comentario agregado/ })).toBeVisible();
    await expect(fila).toContainText('1 comentario');
  });

  test('los contadores cambian de pestaña y las listas vacías lo dicen', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /^Aceptación/ }).click();
    await page.getByRole('button', { name: /Rechazados/ }).click();
    await expect(page.getByRole('button', { name: /Rechazados/ })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByText(/Todavía no hay ensayos rechazados|No hay un ensayo para mostrar/).first()).toBeVisible();
  });
});
