/** Kichik UI primitivlari — tashqi UI kutubxonasiz (bundle kichik qolsin). */

import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';

export function Card({ title, children }: { title?: ReactNode; children: ReactNode }) {
  return (
    <div className="card">
      {title ? <h2>{title}</h2> : null}
      {children}
    </div>
  );
}

export function Row({ label, value }: { label: ReactNode; value: ReactNode }) {
  return (
    <div className="row">
      <span className="muted">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function Tile({
  value,
  label,
  onClick,
}: {
  value: ReactNode;
  label: ReactNode;
  onClick?: () => void;
}) {
  return (
    <button className="tile" onClick={onClick} type="button">
      <div className="value">{value}</div>
      <div className="label">{label}</div>
    </button>
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
