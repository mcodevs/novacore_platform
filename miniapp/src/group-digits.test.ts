/** Summa maydonlarining guruhlashi (`MoneyInput` shu funksiyaga tayanadi).
 *
 * Eng xavfli holat — **kasrli qiymat**: server Decimal'ni JSON'da qator qilib
 * beradi («250000.00»). Raqamlarni ko'r-ko'rona yig'ib olsak nuqta tushib
 * qoladi va maydonda 100 barobar katta summa — «25 000 000» — paydo bo'ladi.
 * Bu narx kelishuvida ham, to'lovda ham qimmatga tushadigan xato.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { groupDigits } from './group-digits.ts';

test('raqamlar uchlik guruhlarga bo‘linadi', () => {
  assert.equal(groupDigits('90000'), '90 000');
  assert.equal(groupDigits('250'), '250');
  assert.equal(groupDigits('1234567'), '1 234 567');
  assert.equal(groupDigits(340000), '340 000');
});

test('kasrli qiymat avval yaxlitlanadi — nuqta tashlab yuborilmaydi', () => {
  assert.equal(groupDigits('250000.00'), '250 000');
  assert.equal(groupDigits('250000.60'), '250 001');
  assert.equal(groupDigits('90000,50'), '90 001');
  assert.equal(groupDigits(250000.4), '250 000');
});

test('bo‘sh qiymat bo‘sh qoladi — maydonda «0» chiqib qolmaydi', () => {
  assert.equal(groupDigits(''), '');
  assert.equal(groupDigits(null), '');
  assert.equal(groupDigits(undefined), '');
});

test('raqam bo‘lmagan belgilar tashlanadi', () => {
  assert.equal(groupDigits('90 000'), '90 000');
  assert.equal(groupDigits('90000 so‘m'), '90 000');
});
