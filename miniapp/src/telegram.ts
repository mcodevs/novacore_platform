/** Telegram WebApp ustidan yupqa tipli qatlam.
 *  SDK Telegram tomonidan beriladi — bundle'ga qo'shimcha kutubxona kirmaydi.
 */

type ThemeParams = Record<string, string | undefined>;

interface MainButton {
  text: string;
  isVisible: boolean;
  setText(text: string): MainButton;
  show(): MainButton;
  hide(): MainButton;
  enable(): MainButton;
  disable(): MainButton;
  showProgress(leaveActive?: boolean): MainButton;
  hideProgress(): MainButton;
  onClick(cb: () => void): MainButton;
  offClick(cb: () => void): MainButton;
}

interface BackButton {
  isVisible: boolean;
  show(): BackButton;
  hide(): BackButton;
  onClick(cb: () => void): BackButton;
  offClick(cb: () => void): BackButton;
}

interface HapticFeedback {
  impactOccurred(style: 'light' | 'medium' | 'heavy'): void;
  notificationOccurred(type: 'error' | 'success' | 'warning'): void;
  selectionChanged(): void;
}

export interface WebApp {
  initData: string;
  initDataUnsafe: { user?: { id: number; language_code?: string } };
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  MainButton: MainButton;
  BackButton: BackButton;
  HapticFeedback: HapticFeedback;
  ready(): void;
  expand(): void;
  close(): void;
  showAlert(message: string, cb?: () => void): void;
  showConfirm(message: string, cb: (ok: boolean) => void): void;
  onEvent(event: string, cb: () => void): void;
  offEvent(event: string, cb: () => void): void;

  // Quyidagilar eski klientlarda bo'lmasligi mumkin — chaqirishdan oldin
  // mavjudligi tekshiriladi (Bot API 6.1+ / 7.7+).
  viewportHeight?: number;
  viewportStableHeight?: number;
  disableVerticalSwipes?(): void;
  setBackgroundColor?(color: string): void;
  setHeaderColor?(color: string): void;
}

const noop = () => {};

/** Brauzerda (Telegram'dan tashqarida) ochilganda ilova qulab tushmasin. */
const stub: WebApp = {
  initData: '',
  initDataUnsafe: {},
  colorScheme: 'light',
  themeParams: {},
  MainButton: new Proxy({} as MainButton, { get: () => () => stub.MainButton }),
  BackButton: new Proxy({} as BackButton, { get: () => () => stub.BackButton }),
  HapticFeedback: { impactOccurred: noop, notificationOccurred: noop, selectionChanged: noop },
  ready: noop,
  expand: noop,
  close: noop,
  showAlert: (m, cb) => {
    window.alert(m);
    cb?.();
  },
  showConfirm: (m, cb) => cb(window.confirm(m)),
  onEvent: noop,
  offEvent: noop,
};

export const tg: WebApp =
  (window as unknown as { Telegram?: { WebApp?: WebApp } }).Telegram?.WebApp ?? stub;

/** `telegram-web-app.js` skripti yuklanganmi — brauzerda ochilgan bo'lsa yo'q. */
const hasTelegramObject = Boolean(
  (window as unknown as { Telegram?: { WebApp?: WebApp } }).Telegram?.WebApp,
);

/**
 * ⚠️ `tg.initData`ni sinxron o'qib bo'lmaydi — u Telegram klienti bilan
 * asinxron `postMessage` handshake orqali to'ladi. Odatda millisekundlarda
 * tugaydi, lekin bir nechta Mini App tabi parallel ochiq bo'lsa (Telegram
 * Desktop) kechikishi mumkin. 2026-08-02 da aynan shu sabab bilan foydalanuvchi
 * **haqiqiy Telegram ichida turib** «Bu sahifa Telegram ichida ochilishi
 * kerak» xatosini ko'rgan — modul darajasidagi `const isTelegram` bir marta
 * hisoblanib, keyin hech qachon qayta tekshirilmagan.
 *
 * Yechim: `initData` darhol bo'lmasa, qisqa muddat kutib qayta tekshiramiz.
 * `hasTelegramObject=false` bo'lsa (haqiqatan brauzerda ochilgan) — darhol
 * xato, kutishning hojati yo'q.
 */
export async function waitForInitData(timeoutMs = 2000): Promise<boolean> {
  if (tg.initData) return true;
  if (!hasTelegramObject) return false;

  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    await new Promise((resolve) => setTimeout(resolve, 50));
    if (tg.initData) return true;
  }
  return false;
}

/** Light/dark rejimni ilovaga uzatadi.
 *
 * ⚠️ Telegram `themeParams` **ranglari ataylab olinmaydi**. Ilova monoxrom
 * (oq/qora) palitraga ega: foydalanuvchining temasiga qarab ranglar sakrasa,
 * kontrast va ko'rinish kafolatlanmasdi. Bizga faqat `colorScheme` kerak.
 */
export function applyTheme(): void {
  const root = document.documentElement;
  root.dataset.scheme = tg.colorScheme;

  // Telegram paneli ham ilova foni bilan bir xil bo'lsin (chok ko'rinmasin)
  const bg = tg.colorScheme === 'dark' ? '#000000' : '#ffffff';
  try {
    tg.setBackgroundColor?.(bg);
    tg.setHeaderColor?.(bg);
  } catch {
    /* eski klient — e'tiborsiz */
  }
}

/** Telegram WebView scroll muammolariga qarshi himoya.
 *
 * 1. `disableVerticalSwipes` — pastga tortilganda ilova yopilib ketmasin
 *    (ro'yxatni scroll qilayotganda tez-tez sodir bo'lardi). Bot API 7.7+.
 * 2. `--vh` — klaviatura ochilganda `100vh` noto'g'ri bo'ladi; haqiqiy
 *    balandlik `viewportStableHeight` dan olinadi.
 */
export function guardScroll(): void {
  try {
    tg.disableVerticalSwipes?.();
  } catch {
    /* eski klient — e'tiborsiz */
  }

  const setViewport = () => {
    const height = tg.viewportStableHeight || tg.viewportHeight;
    if (height) {
      document.documentElement.style.setProperty('--vh', `${height}px`);
    }
  };
  setViewport();
  tg.onEvent('viewportChanged', setViewport);
}

export function haptic(type: 'success' | 'error' | 'warning'): void {
  try {
    tg.HapticFeedback.notificationOccurred(type);
  } catch {
    /* qo'llab-quvvatlanmasa — e'tiborsiz */
  }
}

export function confirmAction(message: string): Promise<boolean> {
  return new Promise((resolve) => tg.showConfirm(message, resolve));
}

export function init(): void {
  tg.ready();
  tg.expand();
  applyTheme();
  guardScroll();
  tg.onEvent('themeChanged', applyTheme);
}
