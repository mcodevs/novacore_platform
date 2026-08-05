/** Forma ekrani: shablon bo'yicha qadam-baqadam.
 *
 *  ⭐ **Har qadam mustaqil** (2026-08-05). Ilgari «Davom etish» keyingi qadamga
 *  darhol o'tkazardi. Lekin ustaning ishi vaqt bo'yicha ajralgan: mashina keldi
 *  (raqam yoziladi) → biroz o'tib diagnostika (foto) → keyin ta'mir → oxirida
 *  yakun. Har safar undan «hozir davom et» deb turish noto'g'ri edi.
 *
 *  Endi har qadamda bitta amal — «Saqlash»: qoralama saqlanadi va ekran
 *  yopiladi. Qayta ochilganda forma **birinchi to'ldirilmagan qadamdan**
 *  boshlanadi. Qadamlar orasida erkin yurish — tepadagi indikator orqali.
 *
 *  Oxirgi qadamda amal bitta: «Mashina ketdi — yuborish» (`mark-left` + `submit`).
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
  firstIncompleteStep,
  sectionTitle,
  sectionsOf,
  stepOfField,
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
      const merged = { ...local, ...loaded.data };
      setValues(merged);

      const tpl = await api.templateSchema(loaded.template_code, loaded.template_version);
      if (!alive) return;
      setSchema(tpl);
      // Qoralama qayta ochildi — qoldirilgan joydan davom etamiz
      setStep(firstIncompleteStep(tpl, merged, loaded.lines, loaded.media));
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

  /** ⭐ Qadamni saqlash: tekshiriladi, serverga yoziladi, ekran yopiladi.
   *  Keyingi qadamga **o'zi o'tmaydi** — usta ishga qaytadi. */
  async function saveStep() {
    if (!schema || !submission) return;
    const found = validateSection(schema, section, values, submission.lines, media);
    setErrors(found);
    if (Object.keys(found).some((key) => found[key])) {
      haptic('error');
      return;
    }
    setBusy(true);
    try {
      await api.patchSubmission(submissionId, values);
      localStorage.removeItem(LOCAL_KEY(submissionId));
      haptic('success');
      onDone(t('draft_saved'));
    } catch (error) {
      // Saqlanmadi — ekranni yopmaymiz, aks holda ish yo'qolgandek tuyuladi
      // (localStorage'da qoladi, lekin usta buni bilmaydi).
      haptic('error');
      setFailure((error as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  /** ⭐ Oxirgi qadam — bitta amal: mashina ketdi (`left_at`, R6) + yuborish.
   *
   *  Ikkalasi bir tugmada, chunki ustaning nazarida bu bitta hodisa: mashina
   *  ketdi = ish tugadi. Ilgari «Mashina ketdi» ni bosib to'xtab qolar, hisobot
   *  esa qoralamada qolib ketardi.
   */
  async function finish() {
    if (!submission || !schema) return;
    const found = validateSection(schema, section, values, submission.lines, media);
    setErrors(found);
    if (Object.keys(found).some((key) => found[key])) {
      haptic('error');
      return;
    }
    const already = Boolean(submission.left_at);
    if (!(await confirmAction(t(already ? 'submit_confirm' : 'left_and_submit_confirm')))) return;

    setBusy(true);
    setFailure('');
    try {
      await api.patchSubmission(submissionId, values);
      // `left_at` allaqachon qo'yilgan bo'lishi mumkin: eski qoralama yoki
      // yuborish xatosidan keyingi ikkinchi urinish. Qayta bosilmaydi.
      if (!already) setSubmission(await api.markLeft(submissionId));
      const result = await api.submitSubmission(submissionId);
      localStorage.removeItem(LOCAL_KEY(submissionId));
      haptic('success');
      onDone(result.auto_approved ? t('auto_approved_ok') : t('submitted_ok'));
    } catch (error) {
      haptic('error');
      const api_error = error as ApiError;
      const fields = api_error.fields ?? {};
      setErrors(fields);
      setFailure(api_error.message);
      // Xato boshqa qadamdagi maydonda bo'lsa — o'sha qadamga olib boramiz,
      // aks holda usta xatoni ko'rmaydi va nima yetmayotganini bilmaydi.
      const culprit = Object.keys(fields).find((code) => !code.startsWith('_'));
      if (culprit) {
        const target = stepOfField(schema, culprit);
        if (target !== step) {
          setStep(target);
          setFailure(t('incomplete_step', { n: target + 1 }));
        }
      }
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

  return (
    <>
      {/*  Indikator — bosiladigan: qadamlar mustaqil bo'lgach oldinga yurishning
          yagona yo'li shu. Tekshiruvsiz o'tadi, chunki usta ataylab tartibsiz
          to'ldirishi mumkin (masalan qismni keyinroq eslaydi). */}
      <div className="stepper">
        {sections.map((code, index) => (
          <button
            key={code ?? 'rest'}
            type="button"
            className={index <= step ? 'done' : ''}
            aria-label={`${t('step')} ${index + 1}`}
            onClick={() => setStep(index)}
          />
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

      {isLast ? (
        <Card>
          <Row label={t('total_labor')} value={money(submission.proposed_labor_amount)} />
          {submission.left_at ? (
            <Row
              label={t('downtime')}
              value={`${dateTime(submission.left_at)} · ${duration(submission.downtime_seconds)}`}
            />
          ) : null}
          <button type="button" onClick={() => void finish()} disabled={busy}>
            {t(submission.left_at ? 'submit' : 'left_and_submit')}
          </button>
          <p className="hint">{t('submit_hint')}</p>
        </Card>
      ) : (
        <>
          <button type="button" onClick={() => void saveStep()} disabled={busy}>
            {t('save_step')}
          </button>
          <p className="hint">{t('save_step_hint')}</p>
        </>
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
