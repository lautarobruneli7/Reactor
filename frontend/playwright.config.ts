import { defineConfig } from '@playwright/test';

// Las pruebas de interfaz levantan el backend (puerto 8000) y el frontend (puerto 5173) si no están corriendo.
// Base de datos de prueba aparte: nunca toca simulador.db.
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    viewport: { width: 1500, height: 1000 },
    // Sin WebGL el reactor 3D muestra un aviso y no corre su animación: las pruebas de formularios van mucho más rápido.
    // La prueba de la escena 3D (escena3d.spec.ts) vuelve a habilitarlo.
    launchOptions: { args: ['--disable-3d-apis'] },
  },
  webServer: [
    {
      // La base de usuarios y ensayos de la prueba se borra en cada arranque (nunca se toca la real).
      command: 'rm -f /tmp/retorta-e2e-datos.db && python -m uvicorn app.main:app --port 8000',
      cwd: '../backend',
      env: {
        SIM_DB_PATH: process.env.SIM_E2E_DB ?? '/tmp/retorta-e2e.db',
        SIM_DATABASE_URL: 'sqlite:////tmp/retorta-e2e-datos.db',
        SIM_AUTH: '',
      },
      url: 'http://127.0.0.1:8000/api/salud',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
