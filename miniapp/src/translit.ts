/**
 * Lotin → kirill translitatsiyasi (o'zbek tili).
 *
 * Kirillcha lokal alohida lug'at emas: `uz` matnidan avtomatik olinadi —
 * yangi kalit qo'shilganda kirillchasi o'zi paydo bo'ladi.
 *
 * Backend nusxasi: `backend/app/core/translit.py` — qoidalar bir xil.
 */

/** O'girilmaydigan atoqli nomlar */
const KEEP_WORDS = [
  'novacore',
  'telegram',
  'excel',
  'yandex',
  'fleet',
  'mini',
  'app',
  'id',
  'pdf',
  'sms',
  'qr',
  'uzs',
  'web',
  'bot',
];

/** Tegilmaydigan bo'laklar: {param}, HTML teg, URL, /buyruq, atoqli nom */
const PROTECTED = new RegExp(
  `(\\{[^{}]*\\}|<[^<>]*>|https?://\\S+|/[A-Za-z_][A-Za-z0-9_]*|\\b(?:${KEEP_WORDS.join('|')})\\b)`,
  'gi',
);

const APOSTROPHES = "'‘’ʻʼ`´";

const DIGRAPHS: Record<string, string> = {
  "o'": 'ў',
  "g'": 'ғ',
  sh: 'ш',
  ch: 'ч',
  yo: 'ё',
  ye: 'е',
  yu: 'ю',
  ya: 'я',
  ts: 'ц',
};

const SINGLES: Record<string, string> = {
  a: 'а',
  b: 'б',
  c: 'к',
  d: 'д',
  e: 'е', // so'z boshida — э
  f: 'ф',
  g: 'г',
  h: 'ҳ',
  i: 'и',
  j: 'ж',
  k: 'к',
  l: 'л',
  m: 'м',
  n: 'н',
  o: 'о',
  p: 'п',
  q: 'қ',
  r: 'р',
  s: 'с',
  t: 'т',
  u: 'у',
  v: 'в',
  w: 'в',
  x: 'х',
  y: 'й',
  z: 'з',
};

const FIXES: Record<string, string> = { рейестр: 'реестр' };

function applyCase(source: string, target: string): string {
  const bare = source.replace(new RegExp(`[${APOSTROPHES}]`, 'g'), '');
  if (bare.length > 1 && source === source.toUpperCase() && source !== source.toLowerCase()) {
    return target.toUpperCase();
  }
  if (source[0] === source[0].toUpperCase() && source[0] !== source[0].toLowerCase()) {
    return target[0].toUpperCase() + target.slice(1);
  }
  return target;
}

function isLetter(char: string): boolean {
  return /\p{L}/u.test(char) || APOSTROPHES.includes(char);
}

function normPair(pair: string): string {
  const lower = pair.toLowerCase();
  if (lower.length === 2 && APOSTROPHES.includes(lower[1])) return `${lower[0]}'`;
  return lower;
}

function convert(text: string): string {
  let out = '';
  let i = 0;
  while (i < text.length) {
    const char = text[i];
    const lower = char.toLowerCase();
    const pair = text.slice(i, i + 2);
    const pairKey = normPair(pair);
    // «yo'q» — «y» + «o'» + «q»: apostrofli birikma kuchliroq
    const nextKey = normPair(text.slice(i + 1, i + 3));

    if (DIGRAPHS[pairKey] && nextKey !== "o'" && nextKey !== "g'") {
      out += applyCase(pair, DIGRAPHS[pairKey]);
      i += 2;
      continue;
    }

    if (APOSTROPHES.includes(char)) {
      // so'z ichidagi tutuq belgisi: ta'mir → таъмир
      const inWord = i > 0 && isLetter(text[i - 1]) && i + 1 < text.length && isLetter(text[i + 1]);
      out += inWord ? 'ъ' : char;
      i += 1;
      continue;
    }

    if (SINGLES[lower]) {
      const wordStart = i === 0 || !isLetter(text[i - 1]);
      out += applyCase(char, lower === 'e' && wordStart ? 'э' : SINGLES[lower]);
      i += 1;
      continue;
    }

    out += char;
    i += 1;
  }
  return out;
}

export function toCyrillic(text: string): string {
  if (!text) return text;
  const parts = text.split(PROTECTED);
  // split() himoyalangan bo'laklarni toq indekslarda qoldiradi
  let result = parts.map((part, idx) => (idx % 2 ? part : convert(part))).join('');
  for (const [wrong, right] of Object.entries(FIXES)) {
    const cap = wrong[0].toUpperCase() + wrong.slice(1);
    result = result.split(wrong).join(right).split(cap).join(right[0].toUpperCase() + right.slice(1));
  }
  return result;
}
