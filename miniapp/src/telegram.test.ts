/** Regressiya: `initData` asinxron kelishi (2026-08-02 dagi jonli xato).
 *
 * `window.Telegram.WebApp.initData` Telegram klienti bilan `postMessage`
 * handshake orqali to'ladi — bu sinxron emas. `waitForInitData` buni hisobga
 * olmasa, foydalanuvchi haqiqiy Telegram ichida turib «Bu sahifa Telegram
 * ichida ochilishi kerak» xatosini ko'rishi mumkin (bir nechta Mini App tabi
 * parallel ochiq bo'lganda handshake kechikadi).
 *
 * Har testda modul yangi holatda import qilinadi (`window.Telegram` moduldan
 * OLDIN o'rnatiladi), chunki `hasTelegramObject` modul yuklanganda bir marta
 * hisoblanadi.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { pathToFileURL } from 'node:url';

async function freshTelegramModule(webApp: Record<string, unknown> | undefined) {
  (globalThis as unknown as { window: unknown }).window = webApp
    ? { Telegram: { WebApp: webApp } }
    : { Telegram: undefined };
  const url = pathToFileURL(new URL('./telegram.ts', import.meta.url).pathname).href;
  // Node ESM keshini oldini olish uchun har safar yangi query
  return import(`${url}?t=${Date.now()}-${Math.random()}`);
}

test('initData boshida bor bo‘lsa — darhol true, kutmasdan', async () => {
  const { waitForInitData } = await freshTelegramModule({ initData: 'abc' });
  const start = Date.now();
  const result = await waitForInitData(2000);
  assert.equal(result, true);
  assert.ok(Date.now() - start < 100, 'darhol qaytishi kerak, timeout kutmasligi kerak');
});

test('Telegram obyekti umuman yo‘q (haqiqiy brauzer) — darhol false', async () => {
  const { waitForInitData } = await freshTelegramModule(undefined);
  const start = Date.now();
  const result = await waitForInitData(2000);
  assert.equal(result, false);
  assert.ok(Date.now() - start < 100, 'brauzerda kutmasdan xato berishi kerak');
});

test('initData kechikib kelsa — asinxron handshakni kutib ushlab qoladi', async () => {
  const webApp: Record<string, unknown> = { initData: '' };
  const { waitForInitData } = await freshTelegramModule(webApp);

  setTimeout(() => {
    webApp.initData = 'late-data'; // Telegram handshake kechikkanda shunday bo'ladi
  }, 120);

  const result = await waitForInitData(2000);
  assert.equal(result, true);
});

test('Telegram obyekti bor, lekin initData hech qachon kelmasa — timeout bilan false', async () => {
  const { waitForInitData } = await freshTelegramModule({ initData: '' });
  const start = Date.now();
  const result = await waitForInitData(200);
  assert.equal(result, false);
  assert.ok(Date.now() - start >= 200, 'to‘liq timeout kutilishi kerak');
});
