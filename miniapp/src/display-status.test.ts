/** «Qisman to'langan» — faqat ko'rsatish holati.
 *
 * Chegaralar muhim: 0 to'lov hamon «Tasdiqlangan», to'liq to'lov esa serverda
 * `paid` bo'lib keladi. Oradagi holat ilgari umuman ko'rinmasdi — xodim
 * hisobotini «Tasdiqlangan» deb ko'rar, lekin pulning yarmi kelgan bo'lardi.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { displayStatus } from './display-status.ts';

test('qisman to‘langan — tasdiqlangan hisobotda 0 < to‘langan < to‘lanadigan', () => {
  assert.equal(
    displayStatus({ status: 'approved', payable_amount: 530000, paid_amount: 440000 }),
    'partly_paid',
  );
  // Server Decimal'ni qator qilib beradi
  assert.equal(
    displayStatus({ status: 'approved', payable_amount: '530000.00', paid_amount: '0.01' }),
    'partly_paid',
  );
});

test('to‘lov boshlanmagan bo‘lsa — holat o‘zgarmaydi', () => {
  assert.equal(
    displayStatus({ status: 'approved', payable_amount: 530000, paid_amount: 0 }),
    'approved',
  );
  assert.equal(displayStatus({ status: 'approved' }), 'approved');
});

test('to‘liq to‘langan — serverning `paid` holati o‘z holicha qoladi', () => {
  assert.equal(
    displayStatus({ status: 'paid', payable_amount: 530000, paid_amount: 530000 }),
    'paid',
  );
  // Sinxronlashdan oldingi lahza: hali `approved`, lekin qarz yopilgan
  assert.equal(
    displayStatus({ status: 'approved', payable_amount: 530000, paid_amount: 530000 }),
    'approved',
  );
});

test('boshqa holatlar tegilmaydi — to‘lov faqat tasdiqdan keyin bo‘ladi', () => {
  assert.equal(
    displayStatus({ status: 'price_negotiation', payable_amount: 100, paid_amount: 50 }),
    'price_negotiation',
  );
  assert.equal(displayStatus({ status: 'draft' }), 'draft');
});
