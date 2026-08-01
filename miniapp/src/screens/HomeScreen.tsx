/** Bosh ekran — rolga qarab: usta hisoblari yoki admin paneli. */

import { useEffect, useState } from 'react';

import * as api from '../api';
import { money, percent } from '../format';
import { statusLabel, t } from '../i18n';
import type { AuthResponse, Dashboard, Submission } from '../types';
import { Card, Row, Skeleton, Tile } from '../ui';

interface Props {
  auth: AuthResponse;
  onOpen(id: number): void;
  onCreate(templateCode: string): void;
  onBuilder(): void;
  onEmployees(): void;
  onReports(): void;
}

export function HomeScreen({
  auth,
  onOpen,
  onCreate,
  onBuilder,
  onEmployees,
  onReports,
}: Props) {
  const kind = auth.employee.role.kind;
  const isReporter = kind === 'reporter' || kind === 'admin';
  const seesAll = kind === 'admin' || kind === 'accountant';

  const [mine, setMine] = useState<Submission[] | null>(null);
  const [pending, setPending] = useState<Submission[] | null>(null);
  const [board, setBoard] = useState<Dashboard | null>(null);
  const [picking, setPicking] = useState(false);

  useEffect(() => {
    if (isReporter) {
      api.listSubmissions({ author_id: 'me', limit: 20 }).then(setMine).catch(() => setMine([]));
    }
    if (seesAll) {
      api.dashboard().then(setBoard).catch(() => setBoard(null));
      api
        // dashboard plitkasi bilan bir xil to'plam: ko'rilayotgani ham ro'yxatda
        // qolsin, aks holda admin ochgan hisobot ko'zdan yo'qoladi
        .listSubmissions({ status: 'submitted,in_review,price_disputed', limit: 20 })
        .then(setPending)
        .catch(() => setPending([]));
    }
  }, [isReporter, seesAll]);

  const drafts = (mine ?? []).filter((s) => s.status === 'draft' || s.status === 'reopened');
  const negotiating = (mine ?? []).filter(
    (s) => s.status === 'price_negotiation' || s.status === 'price_disputed',
  );
  const waiting = (mine ?? []).filter(
    (s) => s.status === 'submitted' || s.status === 'in_review',
  );
  const approved = (mine ?? []).filter((s) => s.status === 'approved' || s.status === 'paid');
  const myProposed = approved.reduce((sum, s) => sum + Number(s.proposed_labor_amount), 0);
  const myApproved = approved.reduce((sum, s) => sum + Number(s.labor_amount ?? 0), 0);

  function startReport() {
    if (auth.templates.length === 1) onCreate(auth.templates[0].code);
    else setPicking(true);
  }

  return (
    <>
      {seesAll ? (
        <>
          {board ? (
            <>
              <div className="grid">
                <Tile value={board.pending_review} label={t('pending')} />
                <Tile value={board.in_negotiation} label={t('in_negotiation')} />
                <Tile value={board.vehicles_in_service} label={t('cars_in_service')} />
                <Tile value={board.approved_count} label={t('approved_month')} />
              </div>
              <Card title={`${t('this_month')} · ${board.period}`}>
                <Row label={t('requested')} value={money(board.proposed_total)} />
                <Row label={t('approved_sum')} value={money(board.approved_total)} />
                <Row
                  label={`💰 ${t('savings')}`}
                  value={`${money(board.saved)} (${percent(board.saved_pct)})`}
                />
                <Row label={t('parts_total')} value={money(board.parts_total)} />
                {board.auto_approved_count > 0 ? (
                  <Row
                    label={`ⓘ ${t('auto_approved_line')}`}
                    value={`${board.auto_approved_count} · ${money(board.auto_approved_total)}`}
                  />
                ) : null}
              </Card>
            </>
          ) : (
            <Skeleton count={2} />
          )}

          <Card title={t('pending')}>
            {pending === null ? (
              <Skeleton count={2} />
            ) : pending.length === 0 ? (
              <p className="muted">{t('no_reports')}</p>
            ) : (
              pending.map((item) => (
                <button
                  key={item.id}
                  className="list-item"
                  type="button"
                  onClick={() => onOpen(item.id)}
                >
                  <div>
                    <strong>{item.number}</strong> · {money(item.proposed_labor_amount)}
                  </div>
                  <div className="badge">
                    {statusLabel(item.status)} · {item.author_name} ·{' '}
                    {item.vehicle?.plate_display ?? '—'}
                  </div>
                </button>
              ))
            )}
          </Card>

          <button
            type="button"
            className="btn-secondary"
            onClick={onReports}
            style={{ marginBottom: 12 }}
          >
            {t('all_reports')}
          </button>

          {kind === 'admin' ? (
            <div className="btn-row" style={{ marginBottom: 12 }}>
              <button type="button" className="btn-secondary" onClick={onEmployees}>
                {t('employees')}
              </button>
              <button type="button" className="btn-secondary" onClick={onBuilder}>
                {t('builder')}
              </button>
            </div>
          ) : null}
        </>
      ) : null}

      {isReporter ? (
        <>
          <div className="grid">
            <Tile value={drafts.length} label={t('drafts')} />
            <Tile value={negotiating.length} label={t('negotiation')} />
            <Tile value={waiting.length} label={t('awaiting_review')} />
            <Tile value={approved.length} label={t('approved_month')} />
          </div>

          <Card title={t('this_month')}>
            <Row label={t('requested')} value={money(myProposed)} />
            <Row label={t('approved_sum')} value={money(myApproved)} />
            <Row
              label={t('reduced')}
              value={
                myProposed > 0
                  ? `${money(myProposed - myApproved)} (${percent(
                      ((myProposed - myApproved) / myProposed) * 100,
                    )})`
                  : '—'
              }
            />
          </Card>

          {picking ? (
            <Card title={t('choose_template')}>
              {auth.templates.map((tpl) => (
                <button
                  key={tpl.code}
                  className="list-item"
                  type="button"
                  onClick={() => onCreate(tpl.code)}
                >
                  {tpl.icon} {tpl.name}
                </button>
              ))}
            </Card>
          ) : (
            <button type="button" onClick={startReport} style={{ marginBottom: 12 }}>
              {t('car_arrived')}
            </button>
          )}

          <Card title={t('my_reports')}>
            {mine === null ? (
              <Skeleton count={2} />
            ) : mine.length === 0 ? (
              <p className="muted">{t('no_reports')}</p>
            ) : (
              mine.slice(0, 10).map((item) => (
                <button
                  key={item.id}
                  className="list-item"
                  type="button"
                  onClick={() => onOpen(item.id)}
                >
                  <div>
                    <strong>{item.number}</strong> ·{' '}
                    {money(item.labor_amount ?? item.proposed_labor_amount)}
                  </div>
                  <div className="badge">
                    {statusLabel(item.status)} · {item.vehicle?.plate_display ?? '—'}
                  </div>
                </button>
              ))
            )}
          </Card>
        </>
      ) : null}
    </>
  );
}
