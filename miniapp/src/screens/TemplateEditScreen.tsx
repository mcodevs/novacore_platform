/** Shablon konstruktori — maydonlarni qo'shish, tartiblash, sozlash, nashr.
 *
 * Telefonda drag&drop noqulay — tartib ↑/↓ tugmalari bilan (kutubxonasiz,
 * bundle kichik qoladi).
 *
 * Versiyalash (docs/02-architecture/03-report-templates.md §5): nashr etilgan
 * shablonni tahrirlash serverda **yangi versiya** ochadi, eski hisobotlar
 * o'z versiyasida qoladi. UI faqat shu haqda ogohlantiradi.
 */

import { useEffect, useState } from 'react';

import * as api from '../api';
import { ApiError } from '../api';
import { t } from '../i18n';
import { FIELD_TYPES } from '../types';
import type { FieldDefinition, FieldType, TemplateDefinition, TemplateDetail } from '../types';
import { Card } from '../ui';

interface Props {
  templateId: number | null;
  onDone(message: string): void;
}

const EMPTY: TemplateDefinition = {
  code: '',
  name: { uz: '', ru: '' },
  icon: '📝',
  subject_type: 'vehicle',
  has_money: true,
  negotiable: true,
  field_mapping: {},
  sections: [],
  fields: [],
};

function newField(index: number, section: string | null): FieldDefinition {
  return {
    code: `field_${index + 1}`,
    type: 'text',
    label: { uz: '', ru: '' },
    required: false,
    section,
    options: {},
    validation: {},
  };
}

export function TemplateEditScreen({ templateId, onDone }: Props) {
  const [detail, setDetail] = useState<TemplateDetail | null>(null);
  const [def, setDef] = useState<TemplateDefinition>(EMPTY);
  const [open, setOpen] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (templateId === null) return;
    api
      .adminTemplate(templateId)
      .then((row) => {
        setDetail(row);
        setDef(row.definition);
      })
      .catch((err: ApiError) => setMessage(err.message));
  }, [templateId]);

  function patch(changes: Partial<TemplateDefinition>) {
    setDef((prev) => ({ ...prev, ...changes }));
  }

  function patchField(index: number, changes: Partial<FieldDefinition>) {
    setDef((prev) => ({
      ...prev,
      fields: prev.fields.map((f, i) => (i === index ? { ...f, ...changes } : f)),
    }));
  }

  function move(index: number, delta: number) {
    setDef((prev) => {
      const next = [...prev.fields];
      const target = index + delta;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return { ...prev, fields: next.map((f, i) => ({ ...f, sort: (i + 1) * 10 })) };
    });
    setOpen(null);
  }

  function remove(index: number) {
    setDef((prev) => ({ ...prev, fields: prev.fields.filter((_, i) => i !== index) }));
    setOpen(null);
  }

  function add() {
    const section = def.sections[0]?.code ?? null;
    setDef((prev) => ({ ...prev, fields: [...prev.fields, newField(prev.fields.length, section)] }));
    setOpen(def.fields.length);
  }

  async function save() {
    setBusy(true);
    setErrors({});
    try {
      const payload = {
        ...def,
        fields: def.fields.map((f, i) => ({ ...f, sort: (i + 1) * 10 })),
      };
      const saved =
        templateId === null
          ? await api.createTemplate(payload)
          : await api.updateTemplate(templateId, payload);
      setDetail((prev) => (prev ? { ...prev, ...saved } : { ...saved, definition: payload }));
      setMessage(t('saved_ok'));
      if (templateId === null) onDone(t('saved_ok'));
    } catch (err) {
      const error = err as ApiError;
      setErrors(error.fields ?? {});
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    if (templateId === null) return;
    setBusy(true);
    try {
      const saved = await api.publishTemplate(templateId);
      setDetail((prev) => (prev ? { ...prev, ...saved } : prev));
      onDone(t('published_ok'));
    } catch (err) {
      setMessage((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  const isDraft = detail?.is_draft ?? true;

  return (
    <>
      <div className="header">
        <h1>
          {def.icon} {def.name.uz || t('new_template')}
        </h1>
        {detail ? (
          <span className="chip">
            v{detail.version} · {isDraft ? t('draft') : t('published')}
          </span>
        ) : null}
      </div>

      {message ? <p className="hint">{message}</p> : null}
      {isDraft && detail ? <p className="error">{t('draft_warning')}</p> : null}
      {!isDraft ? <p className="hint">{t('publish_creates_version')}</p> : null}

      <Card title={t('templates')}>
        <label>
          {t('template_code')}
          <input
            value={def.code}
            disabled={templateId !== null}
            placeholder="car_wash"
            onChange={(e) => patch({ code: e.target.value })}
          />
        </label>
        {errors.code ? <p className="error">{errors.code}</p> : null}

        <label>
          {t('name_uz')}
          <input value={def.name.uz} onChange={(e) => patch({ name: { ...def.name, uz: e.target.value } })} />
        </label>
        <label>
          {t('name_ru')}
          <input
            value={def.name.ru ?? ''}
            onChange={(e) => patch({ name: { ...def.name, ru: e.target.value } })}
          />
        </label>
        <label>
          {t('icon')}
          <input value={def.icon} maxLength={4} onChange={(e) => patch({ icon: e.target.value })} />
        </label>

        <div className="chips">
          {(['vehicle', 'employee', 'none'] as const).map((subject) => (
            <button
              key={subject}
              type="button"
              className={`chip${def.subject_type === subject ? ' active' : ''}`}
              onClick={() => patch({ subject_type: subject })}
            >
              {t(`subject_${subject}`)}
            </button>
          ))}
        </div>

        <label className="switch">
          <input
            type="checkbox"
            checked={def.has_money}
            onChange={(e) => patch({ has_money: e.target.checked })}
          />
          {t('has_money')}
        </label>
        <label className="switch">
          <input
            type="checkbox"
            checked={def.negotiable}
            onChange={(e) => patch({ negotiable: e.target.checked })}
          />
          {t('negotiable')}
        </label>
      </Card>

      <Card title={`${t('fields')} · ${def.fields.length}`}>
        {def.fields.length === 0 ? <p className="muted">{t('no_fields')}</p> : null}

        {def.fields.map((field, index) => (
          <div className="builder-field" key={`${field.code}-${index}`}>
            <div className="builder-field-head">
              <button type="button" className="link" onClick={() => setOpen(open === index ? null : index)}>
                <strong>{field.label.uz || field.code}</strong>
                <span className="badge">
                  {field.type}
                  {field.required ? ' · *' : ''}
                </span>
              </button>
              <div className="builder-field-actions">
                <button type="button" onClick={() => move(index, -1)} aria-label="↑">
                  ↑
                </button>
                <button type="button" onClick={() => move(index, 1)} aria-label="↓">
                  ↓
                </button>
                <button type="button" className="btn-danger" onClick={() => remove(index)}>
                  ✕
                </button>
              </div>
            </div>

            {errors[`fields.${index}.code`] ? (
              <p className="error">{`${t('field_code')}: ${errors[`fields.${index}.code`]}`}</p>
            ) : null}
            {errors[`fields.${index}.type`] ? (
              <p className="error">{`${t('field_type')}: ${errors[`fields.${index}.type`]}`}</p>
            ) : null}
            {errors[`fields.${index}.label`] ? <p className="error">{t('required')}</p> : null}

            {open === index ? (
              <div className="builder-field-body">
                <label>
                  {t('field_code')}
                  <input value={field.code} onChange={(e) => patchField(index, { code: e.target.value })} />
                </label>
                <label>
                  {t('field_type')}
                  <select
                    value={field.type}
                    onChange={(e) => patchField(index, { type: e.target.value as FieldType })}
                  >
                    {FIELD_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {t('name_uz')}
                  <input
                    value={field.label.uz}
                    onChange={(e) => patchField(index, { label: { ...field.label, uz: e.target.value } })}
                  />
                </label>
                <label>
                  {t('name_ru')}
                  <input
                    value={field.label.ru ?? ''}
                    onChange={(e) => patchField(index, { label: { ...field.label, ru: e.target.value } })}
                  />
                </label>
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={Boolean(field.required)}
                    onChange={(e) => patchField(index, { required: e.target.checked })}
                  />
                  {t('field_required')}
                </label>

                {field.type === 'photo' ? (
                  <div className="btn-row">
                    <label>
                      {t('photo_min')}
                      <input
                        type="number"
                        min={0}
                        value={Number(field.options?.min ?? 1)}
                        onChange={(e) =>
                          patchField(index, {
                            options: { ...field.options, min: Number(e.target.value) },
                          })
                        }
                      />
                    </label>
                    <label>
                      {t('photo_max')}
                      <input
                        type="number"
                        min={1}
                        value={Number(field.options?.max ?? 3)}
                        onChange={(e) =>
                          patchField(index, {
                            options: { ...field.options, max: Number(e.target.value) },
                          })
                        }
                      />
                    </label>
                  </div>
                ) : null}

                {field.type === 'lines' ? (
                  <div className="chips">
                    {(['labor', 'part'] as const).map((kind) => (
                      <button
                        key={kind}
                        type="button"
                        className={`chip${(field.options?.kind ?? 'labor') === kind ? ' active' : ''}`}
                        onClick={() =>
                          patchField(index, { options: { ...field.options, kind } })
                        }
                      >
                        {t(`lines_${kind}`)}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        ))}

        <button type="button" className="btn-secondary" onClick={add}>
          {t('add_field')}
        </button>
        <p className="hint">{t('field_types')}</p>
      </Card>

      <div className="btn-row">
        <button type="button" onClick={() => void save()} disabled={busy}>
          {t('save')}
        </button>
        {templateId !== null && isDraft ? (
          <button type="button" className="btn-secondary" onClick={() => void publish()} disabled={busy}>
            {t('publish')}
          </button>
        ) : null}
      </div>
    </>
  );
}
