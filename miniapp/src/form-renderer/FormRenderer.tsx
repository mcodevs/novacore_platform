/** ⭐ Form renderer — Mini App'ning yuragi.
 *  Shablon JSON → forma. Bo'limlar bo'yicha qadam-baqadam (bir ekranda 1–2 maydon).
 */

import type { LineInput } from '../api';
import { label as pickLabel, t } from '../i18n';
import type { FieldSchema, Line, MediaItem, TemplateSchema } from '../types';
import {
  BoolField,
  NumberField,
  PhotoField,
  SelectField,
  SubmissionPickerField,
  TextField,
  VehicleField,
  type FieldProps,
} from './fields';
import { LinesField } from './LinesField';

interface Props {
  schema: TemplateSchema;
  section: string | null;
  values: Record<string, unknown>;
  lines: Line[];
  media: MediaItem[];
  errors: Record<string, string>;
  submissionId: number;
  onChange(code: string, value: unknown): void;
  onMediaChange(media: MediaItem[]): void;
  onLinesSave(lines: LineInput[]): Promise<void>;
}

const RENDERERS: Record<string, (props: FieldProps) => JSX.Element> = {
  text: TextField,
  textarea: TextField,
  number: NumberField,
  money: NumberField,
  bool: BoolField,
  select: SelectField,
  vehicle_picker: VehicleField,
  submission_picker: SubmissionPickerField,
  photo: PhotoField,
};

export function sectionsOf(schema: TemplateSchema): (string | null)[] {
  const list = (schema.sections ?? []).map((s) => s.code);
  const extra = schema.fields.some((f) => !f.section || !list.includes(f.section));
  return list.length ? (extra ? [...list, null] : list) : [null];
}

export function fieldsOfSection(schema: TemplateSchema, section: string | null): FieldSchema[] {
  const known = (schema.sections ?? []).map((s) => s.code);
  return schema.fields.filter((field) =>
    section === null ? !field.section || !known.includes(field.section) : field.section === section,
  );
}

export function sectionTitle(schema: TemplateSchema, section: string | null): string {
  if (section === null) return pickLabel(schema.name);
  const found = (schema.sections ?? []).find((s) => s.code === section);
  return found ? pickLabel(found.title) : pickLabel(schema.name);
}

/** Klientdagi tekshiruv — tez fikr-mulohaza uchun. Server baribir qayta tekshiradi. */
export function validateSection(
  schema: TemplateSchema,
  section: string | null,
  values: Record<string, unknown>,
  lines: Line[],
  media: MediaItem[],
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of fieldsOfSection(schema, section)) {
    if (field.type === 'photo') {
      const min = Number(field.options?.min ?? (field.required ? 1 : 0));
      const count = media.filter((m) => m.field_code === field.code).length;
      if (field.required && count < Math.max(min, 1)) {
        errors[field.code] = t('required');
      }
      continue;
    }
    if (field.type === 'lines') {
      const kind = field.options?.kind ?? 'labor';
      if (field.required && !lines.some((line) => line.kind === kind)) {
        errors[field.code] = t('required');
      }
      continue;
    }
    const value = values[field.code];
    if (!field.required) continue;
    const empty =
      value === null ||
      value === undefined ||
      (typeof value === 'string' && !value.trim()) ||
      (field.type === 'vehicle_picker' &&
        !(value as { vehicle_id?: number } | null)?.vehicle_id) ||
      (field.type === 'submission_picker' &&
        !(value as { submission_id?: number } | null)?.submission_id);
    if (empty) {
      errors[field.code] = t('required');
      continue;
    }
    const minLength = Number(field.validation?.min_length ?? 0);
    if (minLength && String(value).trim().length < minLength) {
      errors[field.code] = `${minLength}+`;
    }
  }
  return errors;
}

/** `submission_picker` nomzodlarini shu hisobotdagi mashina bo'yicha filtrlash. */
function pickedVehicleId(schema: TemplateSchema, values: Record<string, unknown>): number | null {
  const code = schema.field_mapping?.vehicle;
  const candidates = code
    ? [code]
    : schema.fields.filter((f) => f.type === 'vehicle_picker').map((f) => f.code);
  for (const key of candidates) {
    const id = (values[key] as { vehicle_id?: number } | null)?.vehicle_id;
    if (id) return id;
  }
  return null;
}

export function FormRenderer(props: Props) {
  const { schema, section, values, lines, media, errors, submissionId } = props;
  const vehicleId = pickedVehicleId(schema, values);
  return (
    <>
      {fieldsOfSection(schema, section).map((field) => {
        if (field.type === 'lines') {
          return (
            <LinesField
              key={field.code}
              field={field}
              lines={lines}
              error={errors[field.code]}
              onSave={props.onLinesSave}
            />
          );
        }
        const Renderer = RENDERERS[field.type];
        if (!Renderer) return null;
        return (
          <Renderer
            key={field.code}
            field={field}
            value={values[field.code]}
            error={errors[field.code]}
            submissionId={submissionId}
            media={media}
            vehicleId={vehicleId}
            onChange={(value) => props.onChange(field.code, value)}
            onMediaChange={props.onMediaChange}
          />
        );
      })}
    </>
  );
}
