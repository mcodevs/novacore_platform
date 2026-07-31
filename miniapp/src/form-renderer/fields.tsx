/** Maydon turlari → UI. Yangi shablon = yangi JSON, yangi kod emas. */

import { useEffect, useRef, useState } from 'react';

import * as api from '../api';
import { compressImage, money } from '../format';
import { label as pickLabel, t } from '../i18n';
import type { FieldSchema, MediaItem, Vehicle } from '../types';

export interface FieldProps {
  field: FieldSchema;
  value: unknown;
  error?: string;
  submissionId: number;
  media: MediaItem[];
  onChange(value: unknown): void;
  onMediaChange(media: MediaItem[]): void;
}

function Label({ field }: { field: FieldSchema }) {
  const hint = pickLabel(field.hint as { uz: string; ru?: string } | undefined);
  return (
    <>
      <label className="field">
        {pickLabel(field.label)}
        {field.required ? ' *' : ''}
      </label>
      {hint ? <p className="hint">{hint}</p> : null}
    </>
  );
}

export function TextField({ field, value, error, onChange }: FieldProps) {
  const long = field.type === 'textarea';
  return (
    <div className="card">
      <Label field={field} />
      {long ? (
        <textarea
          value={(value as string) ?? ''}
          onChange={(e) => onChange(e.target.value)}
          maxLength={Number(field.validation?.max_length ?? 2000)}
        />
      ) : (
        <input
          type="text"
          value={(value as string) ?? ''}
          onChange={(e) => onChange(e.target.value)}
          maxLength={Number(field.validation?.max_length ?? 200)}
        />
      )}
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}

export function NumberField({ field, value, error, onChange }: FieldProps) {
  const isMoney = field.type === 'money';
  return (
    <div className="card">
      <Label field={field} />
      <input
        type="number"
        inputMode="numeric"
        value={(value as number | string) ?? ''}
        onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
      />
      {isMoney && value ? <p className="hint">{money(Number(value))}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}

export function BoolField({ field, value, onChange }: FieldProps) {
  return (
    <div className="card">
      <Label field={field} />
      <div className="btn-row">
        <button
          type="button"
          className={value === true ? '' : 'btn-secondary'}
          onClick={() => onChange(true)}
        >
          {t('done')}
        </button>
        <button
          type="button"
          className={value === false ? '' : 'btn-secondary'}
          onClick={() => onChange(false)}
        >
          ✕
        </button>
      </div>
    </div>
  );
}

export function SelectField({ field, value, error, onChange }: FieldProps) {
  const [options, setOptions] = useState<{ code: string; name: string }[]>([]);

  useEffect(() => {
    const source = String(field.options?.source ?? '');
    if (source.startsWith('catalog:')) {
      // kichik spravochniklar (nosozlik kategoriyalari) — API'dan
      api
        .catalogItems(source.split(':')[1])
        .then((rows) =>
          setOptions(rows.map((row) => ({ code: row.code, name: `${row.icon ?? ''} ${row.name}`.trim() }))),
        )
        .catch(() => setOptions([]));
      return;
    }
    const choices = (field.options?.choices ?? []) as { code: string; label?: { uz: string } }[];
    setOptions(choices.map((c) => ({ code: c.code, name: pickLabel(c.label) || c.code })));
  }, [field]);

  return (
    <div className="card">
      <Label field={field} />
      <div className="chips">
        {options.map((option) => (
          <button
            key={option.code}
            type="button"
            className={`chip${value === option.code ? ' active' : ''}`}
            onClick={() => onChange(option.code)}
          >
            {option.name}
          </button>
        ))}
      </div>
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}

export function VehicleField({ field, value, error, onChange }: FieldProps) {
  const current = value as { vehicle_id?: number; plate?: string } | undefined;
  const [plate, setPlate] = useState(current?.plate ?? '');
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle');

  async function lookup(raw: string) {
    const normalized = raw.replace(/[^0-9A-Za-z]/g, '').toUpperCase();
    setPlate(normalized);
    if (normalized.length < 6) return;
    setStatus('loading');
    try {
      const found = await api.lookupVehicle(normalized);
      setVehicle(found);
      setStatus('idle');
      onChange({ vehicle_id: found.id, plate: found.plate_number });
    } catch {
      setVehicle(null);
      setStatus('error');
      onChange(null);
    }
  }

  return (
    <div className="card">
      <Label field={field} />
      <input
        type="text"
        autoCapitalize="characters"
        placeholder={t('plate_placeholder')}
        value={plate}
        onChange={(e) => void lookup(e.target.value)}
      />
      {status === 'error' ? <p className="error">{t('vehicle_not_found')}</p> : null}
      {vehicle ? (
        <p className="hint">
          ✅ {vehicle.plate_display} · {vehicle.brand} {vehicle.model}
          {vehicle.year ? ` · ${vehicle.year}` : ''}
          {vehicle.current_driver_name ? ` · 👤 ${vehicle.current_driver_name}` : ''}
        </p>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}

export function PhotoField({
  field,
  submissionId,
  media,
  error,
  onMediaChange,
}: FieldProps) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState('');

  const max = Number(field.options?.max ?? 5);
  const min = Number(field.options?.min ?? (field.required ? 1 : 0));
  const kind = String(field.options?.kind ?? 'other');
  const cameraOnly = Boolean(field.options?.camera_only);
  const items = media.filter((m) => m.field_code === field.code);

  async function upload(files: FileList | null, source: 'camera' | 'gallery') {
    if (!files?.length) return;
    setBusy(true);
    setFailed('');
    const uploaded: MediaItem[] = [];
    for (const file of Array.from(files).slice(0, max - items.length)) {
      try {
        const blob = await compressImage(file);
        uploaded.push(await api.uploadMedia(submissionId, field.code, blob, kind, source));
      } catch {
        setFailed(t('retry'));
      }
    }
    setBusy(false);
    if (uploaded.length) onMediaChange([...media, ...uploaded]);
  }

  return (
    <div className="card">
      <Label field={field} />
      <p className="hint">
        {t('photo_count', { n: items.length, max })}
        {cameraOnly ? ` · ${t('photo_hint')}` : ''}
      </p>

      <div className="photos">
        {items.map((item) => (
          <div className="photo-slot" key={item.id}>
            <img src={item.url} alt="" loading="lazy" />
          </div>
        ))}
      </div>

      <div className="btn-row" style={{ marginTop: 10 }}>
        <button
          type="button"
          onClick={() => cameraRef.current?.click()}
          disabled={busy || items.length >= max}
        >
          {busy ? t('uploading') : t('photo_take')}
        </button>
        {/* Zaxira yo'l: Telegram WebView'da `capture` ishlamasa galereya */}
        <button
          type="button"
          className="btn-secondary"
          onClick={() => galleryRef.current?.click()}
          disabled={busy || items.length >= max}
        >
          {t('photo_gallery')}
        </button>
      </div>

      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={(e) => void upload(e.target.files, 'camera')}
      />
      <input
        ref={galleryRef}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(e) => void upload(e.target.files, 'gallery')}
      />

      {failed ? <p className="error">{failed}</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {items.length < min ? <p className="hint">min: {min}</p> : null}
    </div>
  );
}
