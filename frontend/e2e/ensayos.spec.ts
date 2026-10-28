import { expect, test } from './fixtures';

// Modo local (sin login): un solo usuario administrador. La base de la prueba se rehace en cada arranque.
test.describe('Ensayos guardados en el servidor', () => {
  test('se guarda con lote, aparece en la lista, se comenta y se baja el reporte', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Cargar ejemplo' }).click();
    await expect(page.locator('.medidor-num')).toHaveText('85');

    const lote = `E2E-${Date.now()}`;
    await page.getByRole('button', { name: 'Guardar ensayo' }).click();
    await page.getByLabel(/Lote/).fill(lote);
    await page.getByRole('button', { name: 'Guardar', exact: true }).click();
    await expect(page.getByRole('button', { name: '✓ Guardado' })).toBeVisible();

    await page.getByRole('button', { name: 'Ensayos', exact: true }).click();
    const fila = page.locator('article.ensayo', { hasText: lote });
    await expect(fila).toBeVisible();
    await expect(fila).toContainText('Registrado');
    await expect(fila.locator('.ensayo-metricas')).toContainText('85');

    await fila.getByRole('button', { name: 'Ver' }).click();
    const detalle = page.getByRole('region', { name: /Detalle del ensayo/ });
    await expect(detalle).toContainText(lote);
    await expect(detalle.locator('.corto').first()).toHaveText(/^[0-9a-f]{64}$/);

    // en modo local hay un solo usuario: quien hizo el ensayo no lo aprueba
    await expect(detalle.getByText(/no puede revisarlo/i)).toBeVisible();
    await expect(detalle.getByRole('button', { name: 'Aprobar' })).toHaveCount(0);

    await detalle.getByLabel('Comentario').fill('pesada con balanza B');
    await detalle.getByRole('button', { name: 'Comentar' }).click();
    await expect(detalle.locator('.eventos')).toContainText('pesada con balanza B');

    const [pdf] = await Promise.all([page.waitForEvent('download'), detalle.getByRole('button', { name: 'PDF' }).click()]);
    expect(pdf.suggestedFilename()).toMatch(/^ensayo-\d{3}\.pdf$/);
  });

  test('corregir crea otro ensayo y deja el original marcado como reemplazado', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Cargar ejemplo' }).click();
    await expect(page.locator('.medidor-num')).toHaveText('85');
    const lote = `COR-${Date.now()}`;
    await page.getByRole('button', { name: 'Guardar ensayo' }).click();
    await page.getByLabel(/Lote/).fill(lote);
    await page.getByRole('button', { name: 'Guardar', exact: true }).click();

    await page.getByRole('button', { name: 'Ensayos', exact: true }).click();
    await page.locator('article.ensayo', { hasText: lote }).getByRole('button', { name: 'Ver' }).click();
    await page.getByRole('button', { name: 'Corregir…' }).click();
    await expect(page.getByRole('button', { name: /Guardar corrección de N°/ })).toBeVisible();
    await page.getByRole('button', { name: /Guardar corrección de N°/ }).click();
    // sin motivo no se puede guardar
    await expect(page.getByRole('button', { name: 'Guardar', exact: true })).toBeDisabled();
    await page.getByLabel(/Notas/).fill('se pesó mal el catalizador');
    await page.getByRole('button', { name: 'Guardar', exact: true }).click();

    await page.getByRole('button', { name: 'Ensayos', exact: true }).click();
    await expect(page.locator('article.ensayo.reemplazado', { hasText: lote })).toContainText(/Reemplazado por N°/);
    await expect(page.locator('article.ensayo', { hasText: 'Corrige N°' }).first()).toBeVisible();
  });

  test('la auditoría verifica la cadena de hashes', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Auditoría' }).click();
    await page.getByRole('button', { name: 'Verificar integridad' }).click();
    await expect(page.getByRole('status').filter({ hasText: /Integridad correcta/ })).toBeVisible();
  });

  test('un navegador con ensayos de la versión anterior ofrece importarlos', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('retorta.ensayos', JSON.stringify([{
        numero: 7, fecha: '2026-01-05T12:00:00Z', reaccion_id: 'ibuprofeno-simplificada',
        componentes: [
          { id: 'ibb', gramos: 134, pureza: 99 }, { id: 'aa', gramos: 102, pureza: 98 }, { id: 'cat', gramos: 20, pureza: 97 },
          { id: 'h2', gramos: 2, pureza: 99 }, { id: 'co', gramos: 28, pureza: 98 }, { id: 'exc', gramos: 30, pureza: 99 },
        ],
        puntaje: 85, categoria: 'Muy buena', rendimiento_pct: 80, pureza_producto_pct: 99,
      }]));
    });
    await page.goto('/');
    await page.getByRole('button', { name: 'Ensayos', exact: true }).click();
    await page.getByRole('button', { name: 'Importarlos al servidor' }).click();
    await expect(page.getByRole('status').filter({ hasText: /Se importaron 1 de 1/ })).toBeVisible();
    await expect(page.getByText(/ensayo guardado en este navegador/)).toHaveCount(0);
    expect(await page.evaluate(() => localStorage.getItem('retorta.ensayos'))).toBeNull();
  });
});
