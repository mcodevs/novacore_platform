/** 📋 Hisobotlar arxivi — admin va buxgalter uchun barcha hisobotlar.
 *
 * Bosh ekranda faqat tasdiq navbati va o'z hisobotlaring ko'rinadi; tasdiqlangan
 * hisobot u yerdan yo'qoladi. Bu ekran — «avvalgi hisobotlar» ni topish joyi.
 * Ustaga kerak emas: uning hammasi bosh ekranda «Hisobotlarim» da turadi.
 */

import { useCallback, useEffect, useState } from 'react';

import * as api from '../api';
import { money } from '../format';
import { statusLabel, t } from '../i18n';
import type { Submission, SubmissionStatus } from '../types';
import { Card, Skeleton } from '../ui';

interface Props {
  onOpen(id: number): void;
}

const PAGE = 20;

/** Filtr chiplari — `null` = hammasi. */
const FILTERS: { key: string; statuses: SubmissionStatus[] | null }[] = [
  { key: 'filter_all', statuses: null },
  { key: 'filter_pending', statuses: ['submitted', 'in_review'] },
  { key: 'filter_negotiation', statuses: ['price_negotiation', 'price_disputed'] },
  { key: 'filter_approved', statuses: ['approved', 'paid'] },
  { key: 'filter_rejected', statuses: ['rejected'] },
];

export function ReportsScreen({ onOpen }: Props) {
  const [active, setActive] = useState(0);
  const [rows, setRows] = useState<Submission[] | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (filterIndex: number, offset: number) => {
      setBusy(true);
      const statuses = FILTERS[filterIndex].statuses;
      try {
        const page = await api.listSubmissions({
          limit: PAGE,
          offset,
          ...(statuses ? { status: statuses.join(',') } : {}),
        });
        setDone(page.length < PAGE);
        setRows((prev) => (offset === 0 || prev === null ? page : [...prev, ...page]));
      } catch {
        if (offset === 0) setRows([]);
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  useEffect(() => {
    setRows(null);
    setDone(false);
    void load(active, 0);
  }, [active, load]);

  return (
    <>
      <div className="header">
        <h1>{t('all_reports')}</h1>
      </div>

      <div className="chips" style={{ marginBottom: 12 }}>
        {FILTERS.map((filter, index) => (
          <button
            key={filter.key}
            type="button"
            className={`chip${active === index ? ' active' : ''}`}
            onClick={() => setActive(index)}
          >
            {t(filter.key)}
          </button>
        ))}
      </div>

      <Card>
        {rows === null ? <Skeleton count={3} /> : null}
        {rows?.length === 0 ? <p className="muted">{t('no_reports')}</p> : null}

        {rows?.map((item) => (
          <button
            key={item.id}
            className="list-item"
            type="button"
            onClick={() => onOpen(item.id)}
          >
            <div>
              <strong>{item.number}</strong> ·{' '}
              {money(item.labor_amount ?? item.proposed_labor_amount)}
              {item.auto_approved ? ' · ⓘ' : ''}
            </div>
            <div className="badge">
              {statusLabel(item.status)} · {item.author_name} ·{' '}
              {item.vehicle?.plate_display ?? '—'}
            </div>
          </button>
        ))}

        {rows && rows.length > 0 && !done ? (
          <button
            type="button"
            className="btn-secondary"
            disabled={busy}
            onClick={() => void load(active, rows.length)}
          >
            {busy ? t('loading') : t('load_more')}
          </button>
        ) : null}
      </Card>
    </>
  );
}
