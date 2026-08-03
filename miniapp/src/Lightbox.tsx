/** Foto ko'ruvchi — ilova **ichida**, brauzerga chiqmasdan.
 *
 * Ilgari foto `<a target="_blank">` bilan tashqi brauzerda ochilardi: usta
 * ilovadan chiqib ketardi va qaytib kelishi noqulay edi.
 *
 * Imkoniyatlar: ikki barmoq bilan kattalashtirish, surish, ikki marta bosish,
 * fotolar orasida chapga/o'ngga surish, Telegram «Orqaga» tugmasi bilan yopish.
 *
 * ⚠️ Kutubxonasiz: Telegram WebView'da sahifa masshtabi bloklangan, shuning
 * uchun zoom qo'lda (pointer hodisalari) amalga oshirilgan.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { pushBackHandler } from './telegram';
import type { MediaItem } from './types';
import './lightbox.css';

const MAX_SCALE = 5;
const DOUBLE_TAP_SCALE = 2.5;
const SWIPE_MIN_PX = 60;

interface Props {
  items: MediaItem[];
  index: number;
  onClose(): void;
}

interface Point {
  x: number;
  y: number;
}

export function Lightbox({ items, index, onClose }: Props) {
  const [current, setCurrent] = useState(index);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState<Point>({ x: 0, y: 0 });

  const pointers = useRef(new Map<number, Point>());
  const gesture = useRef<{ dist: number; scale: number; offset: Point } | null>(null);
  const drag = useRef<{ from: Point; offset: Point; at: number } | null>(null);
  const lastTap = useRef(0);

  const reset = useCallback(() => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  }, []);

  const show = useCallback(
    (next: number) => {
      if (next < 0 || next >= items.length) return;
      setCurrent(next);
      reset();
    },
    [items.length, reset],
  );

  // Telegram «Orqaga» — avval ko'ruvchini yopadi, ekranni emas
  useEffect(() => pushBackHandler(onClose), [onClose]);

  // Ko'ruvchi ochiq ekan orqadagi sahifa siljimasin
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  function distanceOf(points: Point[]): number {
    const [a, b] = points;
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  function onPointerDown(event: React.PointerEvent) {
    (event.target as Element).setPointerCapture?.(event.pointerId);
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });

    if (pointers.current.size === 2) {
      const points = [...pointers.current.values()];
      gesture.current = { dist: distanceOf(points), scale, offset };
      drag.current = null;
      return;
    }

    drag.current = {
      from: { x: event.clientX, y: event.clientY },
      offset,
      at: Date.now(),
    };
  }

  function onPointerMove(event: React.PointerEvent) {
    if (!pointers.current.has(event.pointerId)) return;
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });

    // Ikki barmoq — masshtab
    if (pointers.current.size === 2 && gesture.current) {
      const points = [...pointers.current.values()];
      const ratio = distanceOf(points) / (gesture.current.dist || 1);
      const next = Math.min(MAX_SCALE, Math.max(1, gesture.current.scale * ratio));
      setScale(next);
      if (next === 1) setOffset({ x: 0, y: 0 });
      return;
    }

    // Bitta barmoq — kattalashtirilgan bo'lsa surish
    if (drag.current && scale > 1) {
      setOffset({
        x: drag.current.offset.x + (event.clientX - drag.current.from.x),
        y: drag.current.offset.y + (event.clientY - drag.current.from.y),
      });
    }
  }

  function onPointerUp(event: React.PointerEvent) {
    const start = drag.current;
    pointers.current.delete(event.pointerId);
    if (pointers.current.size < 2) gesture.current = null;

    if (!start) return;
    drag.current = null;

    const dx = event.clientX - start.from.x;
    const dy = event.clientY - start.from.y;
    const moved = Math.hypot(dx, dy);
    const quick = Date.now() - start.at < 300;

    // Kattalashtirilmagan holatda: chapga/o'ngga surish — keyingi foto
    if (scale === 1 && Math.abs(dx) > SWIPE_MIN_PX && Math.abs(dx) > Math.abs(dy)) {
      show(current + (dx < 0 ? 1 : -1));
      return;
    }
    // Pastga surish — yopish
    if (scale === 1 && dy > SWIPE_MIN_PX * 1.5 && Math.abs(dy) > Math.abs(dx)) {
      onClose();
      return;
    }

    if (moved < 10 && quick) {
      const now = Date.now();
      if (now - lastTap.current < 300) {
        lastTap.current = 0;
        if (scale > 1) reset();
        else setScale(DOUBLE_TAP_SCALE);
      } else {
        lastTap.current = now;
      }
    }
  }

  const item = items[current];
  if (!item) return null;

  return (
    <div className="lightbox" role="dialog" aria-modal="true">
      <div className="lightbox-bar">
        <span className="lightbox-count">
          {current + 1} / {items.length}
        </span>
        <button type="button" className="lightbox-close" onClick={onClose} aria-label="✕">
          ✕
        </button>
      </div>

      <div
        className="lightbox-stage"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <img
          src={item.url}
          alt={item.field_code ?? ''}
          draggable={false}
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
            transition: drag.current || gesture.current ? 'none' : 'transform .18s ease-out',
          }}
        />
      </div>

      {items.length > 1 ? (
        <div className="lightbox-nav">
          <button
            type="button"
            disabled={current === 0}
            onClick={() => show(current - 1)}
            aria-label="‹"
          >
            ‹
          </button>
          <button
            type="button"
            disabled={current === items.length - 1}
            onClick={() => show(current + 1)}
            aria-label="›"
          >
            ›
          </button>
        </div>
      ) : null}
    </div>
  );
}
