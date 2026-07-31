/** `lines` maydoni — ishlar va qismlar.
 *
 * ⚠️ Tayanch narx bu yerda KO'RSATILMAYDI (R3): usta o'z narxini erkin qo'yadi.
 * Qism qatorlarida narx maydoni yo'q — uni ta'minotchi kiritadi.
 */

import { useEffect, useState } from 'react';

import * as api from '../api';
import type { LineInput } from '../api';
import { money } from '../format';
import { label as pickLabel, t } from '../i18n';
import type { FieldSchema, Line, WorkCatalogItem } from '../types';

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
  const [query, setQuery] = useState('');
  const [catalog, setCatalog] = useState<WorkCatalogItem[]>([]);
  const [picked, setPicked] = useState<{ name: string; catalog_id: number | null } | null>(null);
  const [price, setPrice] = useState('');
  const [qty, setQty] = useState('1');
  const [busy, setBusy] = useState(false);

  const mine = lines.filter((line) => line.kind === kind);
  const total = mine.reduce((sum, line) => sum + Number(line.proposed_amount), 0);

  useEffect(() => {
    if (!adding) return;
    const timer = setTimeout(() => {
      const loader = kind === 'labor' ? api.workCatalog : api.partsCatalog;
      loader(query).then(setCatalog).catch(() => setCatalog([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [adding, query, kind]);

  function toInput(line: Line): LineInput {
    return {
      kind: line.kind,
      name: line.name,
      qty: Number(line.qty),
      unit_price: Number(line.qty) ? Number(line.proposed_amount) / Number(line.qty) : 0,
      catalog_id: null,
    };
  }

  async function addLine() {
    if (!picked) return;
    setBusy(true);
    const next: LineInput[] = [
      ...lines.map(toInput),
      {
        kind,
        name: picked.name,
        qty: Number(qty) || 1,
        unit_price: withPrice ? Number(price) || 0 : 0,
        catalog_id: picked.catalog_id,
      },
    ];
    await onSave(next);
    setBusy(false);
    setAdding(false);
    setPicked(null);
    setPrice('');
    setQty('1');
    setQuery('');
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
          </span>
          <span>
            {withPrice ? <strong>{money(line.proposed_amount)}</strong> : null}{' '}
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

      {withPrice && mine.length ? (
        <div className="row">
          <span className="muted">{t('total_labor')}</span>
          <strong>{money(total)}</strong>
        </div>
      ) : null}

      {!adding ? (
        <button type="button" className="btn-secondary" onClick={() => setAdding(true)}>
          {kind === 'labor' ? t('add_work') : t('add_part')}
        </button>
      ) : (
        <div style={{ marginTop: 10 }}>
          <input
            type="text"
            placeholder={t('search')}
            value={picked ? picked.name : query}
            onChange={(e) => {
              setPicked(null);
              setQuery(e.target.value);
            }}
          />
          {!picked ? (
            <div className="chips" style={{ marginTop: 8 }}>
              {catalog.slice(0, 8).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="chip"
                  onClick={() => setPicked({ name: item.name, catalog_id: item.id })}
                >
                  {item.name}
                </button>
              ))}
              {allowCustom && query.trim().length > 2 ? (
                <button
                  type="button"
                  className="chip active"
                  onClick={() => setPicked({ name: query.trim(), catalog_id: null })}
                >
                  ✍️ {query.trim()}
                </button>
              ) : null}
            </div>
          ) : null}

          {picked && kind === 'part' ? (
            <input
              type="number"
              inputMode="decimal"
              style={{ marginTop: 8 }}
              value={qty}
              onChange={(e) => setQty(e.target.value)}
            />
          ) : null}

          {picked && withPrice ? (
            <>
              <label className="field" style={{ marginTop: 10 }}>
                {t('my_price')}
              </label>
              <input
                type="number"
                inputMode="numeric"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="250000"
              />
            </>
          ) : null}

          <div className="btn-row" style={{ marginTop: 10 }}>
            <button
              type="button"
              onClick={() => void addLine()}
              disabled={busy || !picked || (withPrice && !price)}
            >
              {t('add')}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setAdding(false);
                setPicked(null);
              }}
            >
              {t('cancel')}
            </button>
          </div>
        </div>
      )}

      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}
