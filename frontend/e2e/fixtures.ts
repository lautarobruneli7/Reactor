import { expect, test as base } from '@playwright/test';

/** Igual que `test`, pero sin pedir las tipografías de Google (las pruebas no necesitan red externa y arrancan más rápido). */
export const test = base.extend({
  page: async ({ page }, usar) => {
    await page.route(/fonts\.(googleapis|gstatic)\.com/, (ruta) => ruta.abort());
    await usar(page);
  },
});

export { expect };
