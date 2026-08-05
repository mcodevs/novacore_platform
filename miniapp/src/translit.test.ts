import assert from 'node:assert/strict';
import { test } from 'node:test';

import { toCyrillic } from './translit.ts';

test('asosiy harflar va apostrofli birikmalar', () => {
  assert.equal(toCyrillic("Ta'mir hisoboti yo'q"), 'Таъмир ҳисоботи йўқ');
  assert.equal(toCyrillic("Qo'shish"), 'Қўшиш');
  assert.equal(toCyrillic("g'isht"), 'ғишт');
  assert.equal(toCyrillic('Chiqish vaqti'), 'Чиқиш вақти');
  assert.equal(toCyrillic('yer'), 'ер');
});

test('registr saqlanadi', () => {
  assert.equal(toCyrillic('NARX'), 'НАРХ');
  assert.equal(toCyrillic('Hisobot'), 'Ҳисобот');
});

test('parametr, teg va atoqli nom tegilmaydi', () => {
  assert.equal(toCyrillic('Hisobot {number}'), 'Ҳисобот {number}');
  assert.equal(toCyrillic('<b>Narx</b>'), '<b>Нарх</b>');
  assert.equal(toCyrillic('Telegram bot va Excel'), 'Telegram bot ва Excel');
  assert.equal(toCyrillic('/yordam bosing'), '/yordam босинг');
});

test('emoji va raqamlar o‘zgarmaydi', () => {
  assert.equal(toCyrillic('✅ 250 000 so‘m'), '✅ 250 000 сўм');
});
