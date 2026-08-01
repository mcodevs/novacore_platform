/** 📅 Davr — oyni yopish, to'lov varaqalari, Excel eksport (admin/buxgalter).
 *
 * Ilgari bu faqat botda edi (`/davr`, `/eksport`). Barcha amallar Mini App'da
 * bo'lishi kerak, shuning uchun shu yerga ko'chirildi.
 *
 * ⚠️ Excel **bot orqali** keladi: Telegram WebView'da fayl yuklab olish,
 * ayniqsa iOS'da, ishonchsiz. Tugma shu yerda — fayl suhbatga tushadi.
 */

import { useCallback, useEffect, useState } from 'react';

import * as api from '../api';
import { ApiError } from '../api';
import { money } from '../format';
import { t } from '../i18n';
import type { ExportKind, Payout, Period, Precheck } from '../types';
import { Card, Row, Skeleton } from '../ui';

interface Props {
  onDone(message: string): void;
}

const EXPORTS: ExportKind[] = ['submissions', 'payouts', 'savings'];

/** Precheck to'siqlari: server `{code, ...params}` ko'rinishida qaytaradi. */
function issueText(item: Record<string, unknown>): string {
  const { code, ...params } = item;
  return t(String(code ?? ''), params as Record<string, string | number>);
}

export function PeriodScreen({ onDone }: Props) {
  const [period, setPeriod] = useState<Period | null>(null);
  const [check, setCheck] = useState<Precheck | null>(null);
  const [rows, setRows] = useState<Payout[] | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const reload = useCallback(async () => {
    try {
      const current = await api.currentPeriod();
      setPeriod(current);
      const [state, list] = await Promise.all([
        api.precheck(current.id).catch(() => null),
        api.payouts(current.id).catch(() => []),
      ]);
      setCheck(state);
      setRows(list);
    } catch (err) {
      setError((err as ApiError).message);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function run<T>(action: () => Promise<T>, message: string) {
    setBusy(true);
    setError('');
    try {
      await action();
      await reload();
      onDone(message);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
      setConfirming(false);
    }
  }

  const closed = period?.status === 'closed';
  const total = (rows ?? []).reduce((sum, row) => sum + Number(row.total), 0);

  return (
    <>
      <div className="header">
        <h1>
          {t('period')} · {period ? `${period.year}-${String(period.month).padStart(2, '0')}` : '…'}
        </h1>
        {period ? (
          <span className="chip">{closed ? t('period_closed') : t('period_open')}</span>
        ) : null}
      </div>
      {error ? <p className="error">{error}</p> : null}

      {period === null ? <Skeleton count={3} /> : null}

      {check ? (
        <Card title={t('precheck')}>
          {check.blockers.length === 0 && check.warnings.length === 0 ? (
            <p className="muted">✅ {t('precheck_clean')}</p>
          ) : null}
          {check.blockers.map((item, index) => (
            <p className="error" key={`b${index}`}>
              ⛔ {issueText(item)}
            </p>
          ))}
          {check.warnings.map((item, index) => (
            <p className="hint" key={`w${index}`}>
              ⚠️ {issueText(item)}
            </p>
          ))}

          {!closed ? (
            confirming ? (
              <div className="btn-row">
                <button
                  type="button"
                  className="btn-danger"
                  disabled={busy}
                  onClick={() => void run(() => api.closePeriod(period!.id), t('period_closed_ok'))}
                >
                  {t('confirm_close')}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setConfirming(false)}
                >
                  {t('cancel')}
                </button>
              </div>
            ) : (
              <button
                type="button"
                disabled={busy || !check.can_close}
                onClick={() => setConfirming(true)}
              >
                {t('close_period')}
              </button>
            )
          ) : null}
          {!closed && !check.can_close ? <p className="hint">{t('close_blocked')}</p> : null}
        </Card>
      ) : null}

      <Card title={t('payouts')}>
        {rows === null ? <Skeleton count={2} /> : null}
        {rows?.length === 0 ? <p className="muted">{t('payouts_after_close')}</p> : null}

        {rows?.map((row) => (
          <div key={row.id}>
            <Row
              label={`${row.employee_name} · ${row.submissions_count}`}
              value={money(row.total)}
            />
            {Number(row.reduction_total) > 0 ? (
              <p className="hint">
                {t('requested')}: {money(row.proposed_total)} · {t('reduced')}:{' '}
                {money(row.reduction_total)}
              </p>
            ) : null}
            {row.status !== 'paid' && closed ? (
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => void run(() => api.markPayoutPaid(row.id), t('marked_paid'))}
              >
                {t('mark_paid')}
              </button>
            ) : null}
            {row.status === 'paid' ? <p className="hint">✅ {t('paid')}</p> : null}
          </div>
        ))}

        {rows && rows.length > 0 ? <Row label={t('total')} value={money(total)} /> : null}
      </Card>

      <Card title={t('export')}>
        <p className="hint">{t('export_via_bot')}</p>
        {EXPORTS.map((kind) => (
          <button
            key={kind}
            type="button"
            className="btn-secondary"
            disabled={busy || !period}
            onClick={() =>
              void run(() => api.exportToTelegram(kind, period!.id), t('export_sent'))
            }
          >
            {t(`export_${kind}`)}
          </button>
        ))}
      </Card>
    </>
  );
}
