/** Kichik UI primitivlari — tashqi UI kutubxonasiz (bundle kichik qolsin). */

import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';

import { STATUS_TONE, statusText } from './i18n';
import type { SubmissionStatus } from './types';

export function Card({ title, children }: { title?: ReactNode; children: ReactNode }) {
  return (
    <div className="card">
      {title ? <h2>{title}</h2> : null}
      {children}
    </div>
  );
}

export function Row({
  label,
  value,
  tone,
}: {
  label: ReactNode;
  value: ReactNode;
  /** Qiymatni rang bilan ajratadi (masalan tejamkorlik — yashil). */
  tone?: 'good' | 'accent';
}) {
  return (
    <div className="row">
      <span className="muted">{label}</span>
      <strong className={tone}>{value}</strong>
    </div>
  );
}

/** Holat belgisi — rangli nuqta + matn. */
export function StatusBadge({ status }: { status: SubmissionStatus }) {
  return <span className={`status status-${STATUS_TONE[status]}`}>{statusText(status)}</span>;
}

export function Tile({
  value,
  label,
  tone,
  onClick,
}: {
  value: ReactNode;
  label: ReactNode;
  /** Raqamni rang bilan ajratadi — faqat e'tibor kerak bo'lganda beriladi. */
  tone?: 'warn' | 'accent' | 'good';
  onClick?: () => void;
}) {
  return (
    <button className={`tile${tone ? ` tone-${tone}` : ''}`} onClick={onClick} type="button">
      <div className="value">{value}</div>
      <div className="label">{label}</div>
    </button>
  );
}

/** Ism-familiyadan bosh harflar — avatar uchun (rasm yo'q). */
export function initials(fullName: string): string {
  return fullName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

export function Avatar({ name, className = 'avatar' }: { name: string; className?: string }) {
  return <div className={className}>{initials(name) || '👤'}</div>;
}

/** Pastki paneldagi ikonkalar — emoji emas, chunki emoji platformaga qarab
 *  har xil ko'rinadi va monoxrom UI'da rangi chalg'itadi. */
function Icon({ path }: { path: string }) {
  return (
    <svg
      className="tab-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

export const ICONS = {
  home: 'M3 10.2 12 3l9 7.2V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  reports: 'M8 3h8l4 4v14H4V3zM8 12h8M8 16h5',
  period: 'M4 6h16v15H4zM4 10h16M8 3v4M16 3v4',
  profile: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8M4.5 20.5a7.7 7.7 0 0 1 15 0',
} as const;

export interface Tab {
  key: string;
  icon: keyof typeof ICONS;
  label: string;
}

/** Pastki navigatsiya — ilovaning asosiy bo'limlari doim qo'l ostida. */
export function TabBar({
  tabs,
  active,
  onSelect,
}: {
  tabs: Tab[];
  active: string;
  onSelect(key: string): void;
}) {
  return (
    <nav className="tabbar">
      <div className="tabbar-inner">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`tab${tab.key === active ? ' active' : ''}`}
            onClick={() => onSelect(tab.key)}
          >
            <Icon path={ICONS[tab.icon]} />
            <span className="tab-text">{tab.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}

export function Skeleton({ count = 3 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <div className="skeleton" key={i} />
      ))}
    </>
  );
}

export function Toast({ text, onDone }: { text: string; onDone: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDone, 2600);
    return () => clearTimeout(timer);
  }, [text, onDone]);
  return <div className="toast">{text}</div>;
}

export function useToast(): [ReactNode, (text: string) => void] {
  const [text, setText] = useState('');
  const node = text ? <Toast text={text} onDone={() => setText('')} /> : null;
  return [node, setText];
}
