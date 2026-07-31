/** Forma ekrani: shablon bo'yicha qadam-baqadam + «Mashina ketdi» va «Yuborish».
 *
 *  Avtosaqlash: server (PATCH) + localStorage zaxira — tarmoq uzilsa ish yo'qolmasin.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import * as api from '../api';
import type { LineInput } from '../api';
import { ApiError } from '../api';
import { dateTime, duration, money } from '../format';
import { t } from '../i18n';
import { confirmAction, haptic } from '../telegram';
import type { MediaItem, Submission, TemplateSchema } from '../types';
import { Card, Row, Skeleton } from '../ui';
import {
  FormRenderer,
  sectionTitle,
  sectionsOf,
  validateSection,
} from '../form-renderer/FormRenderer';

interface Props {
  submissionId: number;
  onDone(message: string): void;
  onCancel(): void;
}

const LOCAL_KEY = (id: number) => `nc_draft_${id}`;

export function FormScreen({ submissionId, onDone, onCancel }: Props) {
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [schema, setSchema] = useState<TemplateSchema | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const saveTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    let alive = true;
    (async () => {
      const loaded = await api.getSubmission(submissionId);
      if (!alive) return;
      setSubmission(loaded);
      setMedia(loaded.media);

      const cached = localStorage.getItem(LOCAL_KEY(submissionId));
      const local = cached ? (JSON.parse(cached) as Record<string, unknown>) : {};
      setValues({ ...local, ...loaded.data });

      const tpl = await api.templateSchema(loaded.template_code, loaded.template_version);
      if (alive) setSchema(tpl);
    })().catch((error: ApiError) => setFailure(error.message));
    return () => {
      alive = false;
    };
  }, [submissionId]);

  const sections = useMemo(() => (schema ? sectionsOf(schema) : []), [schema]);
  const section = sections[step] ?? null;
  const isLast = step >= sections.length - 1;

  const persist = useCallback(
    (next: Record<string, unknown>) => {
      localStorage.setItem(LOCAL_KEY(submissionId), JSON.stringify(next));
      window.clearTimeout(saveTimer.current);
      saveTimer.current = window.setTimeout(() => {
        api.patchSubmission(submissionId, next).catch(() => {
          /* offline — localStorage'da qoladi, keyingi urinishda yuboriladi */
        });
      }, 800);
    },
    [submissionId],
  );

  function change(code: string, value: unknown) {
    setValues((prev) => {
      const next = { ...prev, [code]: value };
      persist(next);
      return next;
    });
    setErrors((prev) => ({ ...prev, [code]: '' }));
  }

  async function saveLines(lines: LineInput[]) {
    const updated = await api.replaceLines(submissionId, lines);
    setSubmission(updated);
  }

  function next() {
    if (!schema || !submission) return;
    const found = validateSection(schema, section, values, submission.lines, media);
    setErrors(found);
    if (Object.keys(found).some((key) => found[key])) {
      haptic('error');
      return;
    }
    api.patchSubmission(submissionId, values).catch(() => undefined);
    if (!isLast) setStep(step + 1);
  }

  async function markLeft() {
    setBusy(true);
    try {
      setSubmission(await api.markLeft(submissionId));
      haptic('success');
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!submission) return;
    setBusy(true);
    setFailure('');
    try {
      await api.patchSubmission(submissionId, values);
      const result = await api.submitSubmission(submissionId);
      localStorage.removeItem(LOCAL_KEY(submissionId));
      haptic('success');
      onDone(result.auto_approved ? t('auto_approved_ok') : t('submitted_ok'));
    } catch (error) {
      haptic('error');
      const api_error = error as ApiError;
      setErrors(api_error.fields ?? {});
      setFailure(api_error.message);
    } finally {
      setBusy(false);
    }
  }

  async function removeDraft() {
    if (!(await confirmAction(t('delete_draft_confirm')))) return;
    await api.deleteSubmission(submissionId);
    localStorage.removeItem(LOCAL_KEY(submissionId));
    onCancel();
  }

  if (failure && !submission) return <p className="error">{failure}</p>;
  if (!submission || !schema) return <Skeleton count={4} />;

  const done = isLast;

  return (
    <>
      <div className="stepper">
        {sections.map((code, index) => (
          <span key={code ?? 'rest'} className={index <= step ? 'done' : ''} />
        ))}
      </div>

      <div className="header">
        <h1>{sectionTitle(schema, section)}</h1>
        <span className="muted">
          {t('step')} {step + 1}/{sections.length}
        </span>
      </div>

      <p className="muted">
        {submission.number} · {t('arrived')}: {dateTime(submission.arrived_at)}
      </p>

      <FormRenderer
        schema={schema}
        section={section}
        values={values}
        lines={submission.lines}
        media={media}
        errors={errors}
        submissionId={submissionId}
        onChange={change}
        onMediaChange={setMedia}
        onLinesSave={saveLines}
      />

      {done ? (
        <Card>
          <Row label={t('total_labor')} value={money(submission.proposed_labor_amount)} />
          {submission.left_at ? (
            <Row
              label={t('downtime')}
              value={`${dateTime(submission.left_at)} · ${duration(submission.downtime_seconds)}`}
            />
          ) : null}
          {!submission.left_at ? (
            <button type="button" onClick={() => void markLeft()} disabled={busy}>
              {t('car_left')}
            </button>
          ) : (
            <button type="button" onClick={() => void submit()} disabled={busy}>
              {t('submit')}
            </button>
          )}
          {!submission.left_at ? <p className="hint">{t('submit_after_left')}</p> : null}
        </Card>
      ) : (
        <button type="button" onClick={next} disabled={busy}>
          {t('next')}
        </button>
      )}

      {failure ? <p className="error">{failure}</p> : null}

      <div className="btn-row" style={{ marginTop: 12 }}>
        {step > 0 ? (
          <button type="button" className="btn-secondary" onClick={() => setStep(step - 1)}>
            {t('back')}
          </button>
        ) : null}
        <button type="button" className="btn-danger" onClick={() => void removeDraft()}>
          {t('delete')}
        </button>
      </div>
    </>
  );
}
