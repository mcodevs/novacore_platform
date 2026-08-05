/** `lines` maydoni — ishlar va qismlar.
 *
 * ⚠️ Tayanch narx bu yerda KO'RSATILMAYDI (R3): usta o'z narxini erkin qo'yadi.
 *
 * ⭐ Qism qatorida narx **faqat «o'z hisobimdan» belgisi bilan** ochiladi
 * (ADR-0016): belgi qo'yilsa — usta o'z puliga olgan, unga qaytariladi va
 * **chek fotosi majburiy** (F5a). Belgisiz qism kompaniyaniki — narxsiz
 * qayd etiladi va qarzga kirmaydi.
 */

import { useEffect, useState } from 'react';

import * as api from '../api';
import type { LineInput } from '../api';
import { money } from '../format';
import { label as pickLabel, t } from '../i18n';
import type { FieldSchema, Line, WorkCatalogItem } from '../types';
import { MoneyInput } from '../ui';

interface Props {
  field: FieldSchema;
  lines: Line[];
  error?: string;
  onSave(lines: LineInput[]): Promise<void>;
}

export function LinesField({ field, lines, error, onSave }: Props) {
  const kind = (field.options?.kind ?? 'labor') as 'labor' | 'part';
  const withPrice = Boolean(field.options?.price_field ?? kind === 'labor');
  const allowCustom = field.options?.allow_custom !== false;

  const [adding, setAdding] = useState(false);
  /** ⭐ Yozilgan matnning **o'zi** — tanlov (2026-08-05).
   *
   *  Ilgari nom faqat chip bosilgach «tanlangan» hisoblanardi: usta «Benzonasos»
   *  deb yozib, siyohrang «✍️ Benzonasos» chipini bosish kerakligini tushunmay,
   *  pastga o'tib ketardi va qator qo'shilmasdi. Endi katalog chiplari — faqat
   *  tez to'ldirish taklifi, majburiy qadam emas.
   */
  const [name, setName] = useState('');
  const [catalogId, setCatalogId] = useState<number | null>(null);
  const [catalog, setCatalog] = useState<WorkCatalogItem[]>([]);
  const [price, setPrice] = useState('');
  const [qty, setQty] = useState('1');
  const [selfFunded, setSelfFunded] = useState(false);
  const [busy, setBusy] = useState(false);

  // Qismda narx maydoni belgi bilan ochiladi; ish haqida — doim (ADR-0016)
  const priceOpen = kind === 'part' ? selfFunded : withPrice;
  //  `allow_custom: false` bo'lgan shablonda erkin matn qabul qilinmaydi —
  //  bunday maydonda katalogdan tanlash majburiy bo'lib qoladi.
  const ready = name.trim().length >= 2 && (allowCustom || catalogId !== null);

  const mine = lines.filter((line) => line.kind === kind);
  const total = mine.reduce((sum, line) => sum + Number(line.proposed_amount), 0);

  useEffect(() => {
    if (!adding) return;
    const timer = setTimeout(() => {
      const loader = kind === 'labor' ? api.workCatalog : api.partsCatalog;
      loader(name).then(setCatalog).catch(() => setCatalog([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [adding, name, kind]);

  function reset() {
    setAdding(false);
    setName('');
    setCatalogId(null);
    setPrice('');
    setQty('1');
    setSelfFunded(false);
  }

  /** ⚠️ `self_funded` ni saqlash SHART: server qatorlarni o'chirib qayta
   *  yaratadi, belgi tushib qolsa qarz yo'qoladi. */
  function toInput(line: Line): LineInput {
    return {
      kind: line.kind,
      name: line.name,
      qty: Number(line.qty),
      unit_price: Number(line.qty) ? Number(line.proposed_amount) / Number(line.qty) : 0,
      catalog_id: null,
      self_funded: line.self_funded,
    };
  }

  async function addLine() {
    if (!ready) return;
    setBusy(true);
    const next: LineInput[] = [
      ...lines.map(toInput),
      {
        kind,
        name: name.trim(),
        qty: Number(qty) || 1,
        unit_price: priceOpen ? Number(price) || 0 : 0,
        catalog_id: catalogId,
        self_funded: kind === 'part' ? selfFunded : false,
      },
    ];
    await onSave(next);
    setBusy(false);
    reset();
  }

  async function removeLine(id: number) {
    setBusy(true);
    await onSave(lines.filter((line) => line.id !== id).map(toInput));
    setBusy(false);
  }

  return (
    <div className="card">
      <label className="field">
        {pickLabel(field.label)}
        {field.required ? ' *' : ''}
      </label>
      {kind === 'labor' ? (
        <p className="hint">{t('price_hint_own')}</p>
      ) : (
        <p className="hint">{t('part_price_note')}</p>
      )}

      {mine.map((line) => (
        <div className="row" key={line.id}>
          <span>
            {kind === 'labor' ? '🔧' : '📦'} {line.name}
            {Number(line.qty) !== 1 ? ` ×${line.qty}` : ''}
            {line.self_funded ? <small className="row-hint">💳 {t('self_funded')}</small> : null}
          </span>
          <span>
            {withPrice || Number(line.proposed_amount) > 0 ? (
              <strong>{money(line.proposed_amount)}</strong>
            ) : null}{' '}
            <button
              type="button"
              className="btn-danger"
              style={{ width: 'auto', minHeight: 32, padding: '4px 10px' }}
              onClick={() => void removeLine(line.id)}
              disabled={busy}
            >
              🗑
            </button>
          </span>
        </div>
      ))}

      {mine.length && (withPrice || total > 0) ? (
        <div className="row">
          <span className="muted">{kind === 'labor' ? t('total_labor') : t('total_own_parts')}</span>
          <strong>{money(total)}</strong>
        </div>
      ) : null}

      {!adding ? (
        <button type="button" className="btn-secondary lines-add" onClick={() => setAdding(true)}>
          {kind === 'labor' ? t('add_work') : t('add_part')}
        </button>
      ) : (
        <div className="lines-add">
          <input
            type="text"
            placeholder={allowCustom ? t('line_name_placeholder') : t('search')}
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setCatalogId(null); // qo'lda tahrirlangan nom — katalog qatori emas
            }}
          />

          {/*  Katalog — taklif, to'siq emas: bosilsa nom to'ldiriladi, bosilmasa
              usta o'zi yozgani bilan davom etadi. */}
          {catalog.length ? (
            <>
              <p className="hint">{t('quick_choice')}</p>
              <div className="chips" style={{ marginTop: 'var(--s-2)' }}>
                {catalog.slice(0, 8).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`chip${catalogId === item.id ? ' active' : ''}`}
                    onClick={() => {
                      setName(item.name);
                      setCatalogId(item.id);
                    }}
                  >
                    {item.name}
                  </button>
                ))}
              </div>
            </>
          ) : null}

          {ready && kind === 'part' ? (
            <input
              type="number"
              inputMode="decimal"
              style={{ marginTop: 8 }}
              value={qty}
              onChange={(e) => setQty(e.target.value)}
            />
          ) : null}

          {/* ⭐ ADR-0016 — belgi narx maydonini ochadi */}
          {ready && kind === 'part' ? (
            <label className="check-row" style={{ marginTop: 10 }}>
              <input
                type="checkbox"
                checked={selfFunded}
                onChange={(e) => {
                  setSelfFunded(e.target.checked);
                  if (!e.target.checked) setPrice('');
                }}
              />
              <span>
                {t('self_funded')}
                <small className="row-hint">{t('self_funded_hint')}</small>
              </span>
            </label>
          ) : null}

          {ready && priceOpen ? (
            <>
              <label className="field" style={{ marginTop: 10 }}>
                {t('my_price')} *
              </label>
              {/* ⚠️ Placeholder matnli: «250 000» raqami to'ldirilgan qiymatdek
                  ko'rinib, usta narxni yozmay o'tib ketardi. */}
              <MoneyInput value={price} onChange={setPrice} placeholder={t('price_placeholder')} />
            </>
          ) : null}

          <div className="btn-row" style={{ marginTop: 10 }}>
            <button
              type="button"
              onClick={() => void addLine()}
              disabled={busy || !ready || (priceOpen && !price)}
            >
              {t('add')}
            </button>
            <button type="button" className="btn-secondary" onClick={reset}>
              {t('cancel')}
            </button>
          </div>
        </div>
      )}

      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}
