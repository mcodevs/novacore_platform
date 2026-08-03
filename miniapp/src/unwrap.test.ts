/** Regressiya testi: `node --test` (qo'shimcha kutubxonasiz). */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { unwrap } from './unwrap.ts';

test('sof konvert ochiladi', () => {
  assert.deepEqual(unwrap({ data: { id: 7 } }), { id: 7 });
  assert.deepEqual(unwrap({ data: [1, 2], meta: { request_id: 'x' } }), [1, 2]);
});

test('hisobot obyekti ochilmaydi — unda `data` maydoni bor', () => {
  const submission = { id: 42, number: 'WO-2026-000042', data: { category: 'brakes' } };
  const result = unwrap<typeof submission>(submission);
  assert.equal(result.id, 42, 'id yo‘qolmasligi kerak');
  assert.deepEqual(result.data, { category: 'brakes' });
});

test('massiv va oddiy qiymatlar o‘zgarmaydi', () => {
  assert.deepEqual(unwrap([{ id: 1 }]), [{ id: 1 }]);
  assert.equal(unwrap(null), null);
  assert.equal(unwrap('matn'), 'matn');
});

test('faqat `data` bo‘lgan obyekt konvert deb qaraladi', () => {
  assert.deepEqual(unwrap({ data: { ok: true } }), { ok: true });
  // `data` + boshqa maydon = konvert emas
  assert.deepEqual(unwrap({ data: {}, status: 'draft' }), { data: {}, status: 'draft' });
});
