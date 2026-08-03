/** Ko'rib chiqish ekrani.
 *
 *  Admin: narx tarixi + tasdiqlash / kamaytirish / qaytarish / rad etish.
 *  Muallif: o'z hisoboti + narx taklifiga rozilik yoki nizo.
 *  ⚠️ Narx tarixi faqat admin/buxgalterga so'raladi (R3).
 */

import { useEffect, useState } from 'react';

import * as api from '../api';
import { ApiError } from '../api';
import { dateTime, duration, money } from '../format';
import { t } from '../i18n';
import { confirmAction, haptic } from '../telegram';
import type { AuthResponse, PriceContext, Submission } from '../types';
import { Card, Row, Skeleton, StatusBadge } from '../ui';

interface Props {
  auth: AuthResponse;
  submissionId: number;
  onDone(message: string): void;
  onEdit(id: number): void;
}

type Prompt = 'reduce' | 'reject' | 'reopen' | 'dispute' | 'final' | null;

export function DetailScreen({ auth, submissionId, onDone, onEdit }: Props) {
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [contexts, setContexts] = useState<PriceContext[]>([]);
  const [prompt, setPrompt] = useState<Prompt>(null);
  const [lineId, setLineId] = useState<number | null>(null);
  const [amount, setAmount] = useState('');
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');

  const isAdmin = auth.employee.role.kind === 'admin';
  const isAuthor = submission?.author_id === auth.employee.id;

  useEffect(() => {
    api
      .getSubmission(submissionId)
      .then((loaded) => {
        setSubmission(loaded);
        if (auth.employee.role.kind !== 'reporter') {
          api.priceContext(submissionId).then(setContexts).catch(() => setContexts([]));
        }
      })
      .catch((error: ApiError) => setFailure(error.message));
  }, [submissionId, auth.employee.role.kind]);

  async function run(action: () => Promise<Submission>, message: string) {
    setBusy(true);
    setFailure('');
    try {
      const updated = await action();
      setSubmission(updated);
      haptic('success');
      onDone(message);
    } catch (error) {
      haptic('error');
      setFailure((error as ApiError).message);
    } finally {
      setBusy(false);
      setPrompt(null);
      setComment('');
      setAmount('');
    }
  }

  if (failure && !submission) return <p className="error">{failure}</p>;
  if (!submission) return <Skeleton count={4} />;

  const labor = submission.lines.filter((line) => line.kind === 'labor');
  const parts = submission.lines.filter((line) => line.kind === 'part');
  const canReview =
    isAdmin && ['submitted', 'in_review', 'price_disputed'].includes(submission.status);
  const canNegotiate = isAuthor && submission.status === 'price_negotiation';

  return (
    <>
      <div className="header">
        <h1>{submission.number}</h1>
        <StatusBadge status={submission.status} />
      </div>

      <Card>
        <Row label={t('author')} value={submission.author_name} />
        {submission.vehicle ? (
          <Row
            label="🚘"
            value={`${submission.vehicle.plate_display} · ${submission.vehicle.brand} ${submission.vehicle.model}`}
          />
        ) : null}
        <Row label={t('arrived')} value={dateTime(submission.arrived_at)} />
        <Row
          label={t('left')}
          value={`${dateTime(submission.left_at)} (${duration(submission.downtime_seconds)})`}
        />
        {submission.auto_approved ? <p className="hint">⚙️ {t('auto_approved_line')}</p> : null}
      </Card>

      <Card title="💰">
        {labor.map((line) => {
          const ctx = contexts.find((c) => c.line_id === line.id);
          return (
            <div key={line.id} style={{ marginBottom: 10 }}>
              <div className="row">
                <span>🔧 {line.name}</span>
                <strong>
                  {money(line.proposed_amount)}
                  {line.approved_amount !== null &&
                  Number(line.approved_amount) !== Number(line.proposed_amount)
                    ? ` → ${money(line.approved_amount)}`
                    : ''}
                </strong>
              </div>
              {ctx ? (
                <div className="history">
                  {ctx.count > 0 ? (
                    <>
                      📊 {t('history_avg', { n: ctx.count })}: {money(ctx.avg_approved)} ·{' '}
                      {money(ctx.min_approved)} – {money(ctx.max_approved)}
                      {ctx.author_avg !== null ? (
                        <>
                          <br />
                          👤 {t('author_avg', { name: submission.author_name })}:{' '}
                          {money(ctx.author_avg)} ·{' '}
                          {t('reduction_rate', {
                            pct: Math.round(Number(ctx.author_reduction_pct ?? 0)),
                          })}
                        </>
                      ) : null}
                    </>
                  ) : (
                    t('history_none')
                  )}
                </div>
              ) : null}
              {line.price_change_reason ? (
                <div className="history">💬 {line.price_change_reason}</div>
              ) : null}
            </div>
          );
        })}
        {parts.length ? (
          <>
            <p className="muted">{t('parts')}</p>
            {parts.map((line) => (
              <div className="row" key={line.id}>
                <span>📦 {line.name} ×{line.qty}</span>
                <strong>
                  {Number(line.approved_amount ?? line.proposed_amount) > 0
                    ? money(line.approved_amount ?? line.proposed_amount)
                    : '—'}
                </strong>
              </div>
            ))}
          </>
        ) : null}
        <Row label={t('requested')} value={money(submission.proposed_labor_amount)} />
        {submission.labor_amount !== null ? (
          <Row label={t('approved_sum')} value={money(submission.labor_amount)} />
        ) : null}
      </Card>

      {submission.media.length ? (
        <Card title={t('photos')}>
          <div className="photos">
            {submission.media.map((item) => (
              <a key={item.id} href={item.url} target="_blank" rel="noreferrer">
                <img src={item.url} alt={item.field_code ?? ''} loading="lazy" />
              </a>
            ))}
          </div>
        </Card>
      ) : null}

      {typeof submission.data.comment === 'string' && submission.data.comment ? (
        <Card title={t('comment')}>
          <p>{String(submission.data.comment)}</p>
        </Card>
      ) : null}

      {/* --- Usta: narx taklifiga javob --- */}
      {canNegotiate ? (
        <Card title={t('negotiation')}>
          <div className="negotiation">
            {labor
              .filter(
                (line) =>
                  line.approved_amount !== null &&
                  Number(line.approved_amount) < Number(line.proposed_amount),
              )
              .map((line) => (
                <div key={line.id}>
                  <Row label={t('you_asked')} value={money(line.proposed_amount)} />
                  <Row label={t('admin_proposed')} value={money(line.approved_amount)} />
                </div>
              ))}
          </div>
          <p className="hint">{t('auto_accept_note', { hours: 48 })}</p>
          {prompt === 'dispute' ? (
            <>
              <textarea
                placeholder={t('dispute_comment')}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              <button
                type="button"
                disabled={busy || comment.trim().length < 5}
                onClick={() =>
                  void run(() => api.disputePrice(submissionId, comment.trim()), t('done'))
                }
              >
                {t('dispute_price')}
              </button>
            </>
          ) : (
            <div className="btn-row">
              <button
                type="button"
                disabled={busy}
                onClick={async () => {
                  if (await confirmAction(t('accept_price'))) {
                    void run(() => api.acceptPrice(submissionId), t('done'));
                  }
                }}
              >
                {t('accept_price')}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setPrompt('dispute')}
              >
                {t('dispute_price')}
              </button>
            </div>
          )}
        </Card>
      ) : null}

      {/* --- Admin: qarorlar --- */}
      {canReview ? (
        <Card>
          {prompt === null ? (
            <>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  submission.status === 'price_disputed'
                    ? setPrompt('final')
                    : void run(() => api.approve(submissionId), t('done'))
                }
              >
                {submission.status === 'price_disputed' ? t('final_decision') : t('approve')}
              </button>
              <div className="btn-row" style={{ marginTop: 8 }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setPrompt('reduce');
                    setLineId(labor[0]?.id ?? null);
                  }}
                >
                  {t('reduce_price')}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setPrompt('reopen')}
                >
                  {t('reopen')}
                </button>
              </div>
              <button
                type="button"
                className="btn-danger"
                style={{ marginTop: 8 }}
                onClick={() => setPrompt('reject')}
              >
                {t('reject')}
              </button>
            </>
          ) : null}

          {prompt === 'reduce' ? (
            <>
              <div className="chips">
                {labor.map((line) => (
                  <button
                    key={line.id}
                    type="button"
                    className={`chip${lineId === line.id ? ' active' : ''}`}
                    onClick={() => setLineId(line.id)}
                  >
                    {line.name}
                  </button>
                ))}
              </div>
              <label className="field" style={{ marginTop: 10 }}>
                {t('new_amount')}
              </label>
              <input
                type="number"
                inputMode="numeric"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              {(() => {
                const ctx = contexts.find((c) => c.line_id === lineId);
                return ctx?.quick_amounts?.length ? (
                  <>
                    <p className="hint">{t('quick_choice')}</p>
                    <div className="chips">
                      {ctx.quick_amounts.map((value) => (
                        <button
                          key={value}
                          type="button"
                          className="chip"
                          onClick={() => setAmount(String(value))}
                        >
                          {money(value)}
                        </button>
                      ))}
                    </div>
                  </>
                ) : null;
              })()}
              <label className="field" style={{ marginTop: 10 }}>
                {t('reason')}
              </label>
              <textarea value={comment} onChange={(e) => setComment(e.target.value)} />
              <button
                type="button"
                disabled={busy || !lineId || !amount || comment.trim().length < 5}
                onClick={() => {
                  const line = labor.find((l) => l.id === lineId);
                  if (line && Number(amount) > Number(line.proposed_amount)) {
                    setFailure(t('price_increase_forbidden'));
                    haptic('error');
                    return;
                  }
                  void run(
                    () =>
                      api.proposePrice(
                        submissionId,
                        [{ line_id: lineId as number, amount: Number(amount) }],
                        comment.trim(),
                      ),
                    t('done'),
                  );
                }}
              >
                {t('send_proposal')}
              </button>
            </>
          ) : null}

          {prompt === 'reject' || prompt === 'reopen' || prompt === 'final' ? (
            <>
              <label className="field">{t('reason')}</label>
              <textarea value={comment} onChange={(e) => setComment(e.target.value)} />
              <button
                type="button"
                disabled={busy || comment.trim().length < 5}
                onClick={() => {
                  if (prompt === 'reject') {
                    void run(() => api.reject(submissionId, comment.trim()), t('done'));
                  } else if (prompt === 'reopen') {
                    void run(() => api.reopen(submissionId, comment.trim()), t('done'));
                  } else {
                    void run(() => api.approve(submissionId, comment.trim()), t('done'));
                  }
                }}
              >
                {t('done')}
              </button>
            </>
          ) : null}

          {prompt !== null ? (
            <button
              type="button"
              className="btn-secondary"
              style={{ marginTop: 8 }}
              onClick={() => setPrompt(null)}
            >
              {t('cancel')}
            </button>
          ) : null}
        </Card>
      ) : null}

      {failure ? <p className="error">{failure}</p> : null}

      {isAuthor && (submission.status === 'reopened' || submission.status === 'draft') ? (
        <button type="button" onClick={() => onEdit(submission.id)}>
          ✏️ {t('form_title')}
        </button>
      ) : null}
    </>
  );
}
