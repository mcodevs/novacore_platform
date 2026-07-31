/** uz (lotin) + ru — 1-kundan. Til `employees.lang` da saqlanadi. */

import type { Lang, SubmissionStatus } from './types';

type Dict = Record<string, { uz: string; ru: string }>;

export const T: Dict = {
  loading: { uz: 'Yuklanmoqda…', ru: 'Загрузка…' },
  retry: { uz: 'Qayta urinish', ru: 'Повторить' },
  save: { uz: 'Saqlash', ru: 'Сохранить' },
  cancel: { uz: 'Bekor qilish', ru: 'Отмена' },
  delete: { uz: 'O‘chirish', ru: 'Удалить' },
  back: { uz: 'Orqaga', ru: 'Назад' },
  next: { uz: 'Davom etish', ru: 'Далее' },
  done: { uz: 'Tayyor', ru: 'Готово' },
  add: { uz: 'Qo‘shish', ru: 'Добавить' },
  search: { uz: 'Qidirish…', ru: 'Поиск…' },
  currency: { uz: 'so‘m', ru: 'сум' },
  required: { uz: 'Majburiy maydon', ru: 'Обязательное поле' },
  not_in_registry: {
    uz: 'Siz xodimlar reyestrida yo‘qsiz. Adminga murojaat qiling.',
    ru: 'Вас нет в реестре сотрудников. Обратитесь к администратору.',
  },
  open_in_telegram: {
    uz: 'Bu sahifa Telegram ichida ochilishi kerak.',
    ru: 'Эта страница должна открываться внутри Telegram.',
  },

  // Bosh ekran
  in_workshop: { uz: 'Ustaxonada', ru: 'В сервисе' },
  drafts: { uz: 'Qoralamalar', ru: 'Черновики' },
  negotiation: { uz: 'Narx kelishuvi', ru: 'Согласование цены' },
  awaiting_review: { uz: 'Tasdiq kutmoqda', ru: 'Ждут подтверждения' },
  approved_month: { uz: 'Bu oy tasdiqlangan', ru: 'Подтверждено за месяц' },
  this_month: { uz: 'Bu oy', ru: 'Этот месяц' },
  requested: { uz: 'So‘radim', ru: 'Запросил' },
  approved_sum: { uz: 'Tasdiqlandi', ru: 'Подтверждено' },
  reduced: { uz: 'Kamaydi', ru: 'Снижено' },
  car_arrived: { uz: '🚗 Mashina keldi', ru: '🚗 Машина приехала' },
  my_reports: { uz: 'Hisobotlarim', ru: 'Мои отчёты' },
  no_reports: { uz: 'Hozircha hisobot yo‘q', ru: 'Отчётов пока нет' },
  choose_template: { uz: 'Qaysi hisobot?', ru: 'Какой отчёт?' },

  // Admin
  admin_dashboard: { uz: 'Boshqaruv paneli', ru: 'Панель управления' },
  pending: { uz: 'Tasdiq kutmoqda', ru: 'Ждут подтверждения' },
  in_negotiation: { uz: 'Kelishuvda', ru: 'В согласовании' },
  cars_in_service: { uz: 'Ustaxonada', ru: 'В сервисе' },
  savings: { uz: 'Kelishuv tejamkorligi', ru: 'Экономия согласования' },
  parts_total: { uz: 'Ehtiyot qism', ru: 'Запчасти' },
  auto_approved_line: {
    uz: 'Avtomatik tasdiqlangan (admin)',
    ru: 'Подтверждено автоматически (админ)',
  },

  // Forma
  form_title: { uz: 'Hisobot', ru: 'Отчёт' },
  step: { uz: 'Qadam', ru: 'Шаг' },
  photo_take: { uz: '📷 Suratga olish', ru: '📷 Сделать снимок' },
  photo_gallery: { uz: '🖼 Galereyadan', ru: '🖼 Из галереи' },
  photo_hint: {
    uz: 'Foto shu yerda kamerada olinishi kerak',
    ru: 'Фото нужно снять камерой прямо сейчас',
  },
  photo_count: { uz: '{n} / {max} ta foto', ru: '{n} / {max} фото' },
  uploading: { uz: 'Yuklanmoqda…', ru: 'Загрузка…' },
  plate_placeholder: { uz: '01A123BC', ru: '01A123BC' },
  vehicle_not_found: { uz: 'Mashina reyestrda topilmadi', ru: 'Машина не найдена в реестре' },
  works: { uz: 'Bajarilgan ishlar', ru: 'Выполненные работы' },
  parts: { uz: 'Ishlatilgan qismlar', ru: 'Использованные запчасти' },
  my_price: { uz: 'Mening narxim', ru: 'Моя цена' },
  price_hint_own: {
    uz: 'Narxni o‘zingiz belgilaysiz — admin ko‘rib chiqadi',
    ru: 'Цену указываете вы — админ рассмотрит',
  },
  part_price_note: {
    uz: 'ⓘ Qism narxini ta‘minotchi kiritadi',
    ru: 'ⓘ Цену запчасти вносит снабженец',
  },
  add_work: { uz: '➕ Ish qo‘shish', ru: '➕ Добавить работу' },
  add_part: { uz: '➕ Qism qo‘shish', ru: '➕ Добавить запчасть' },
  total_labor: { uz: 'Mening ish haqim', ru: 'Моя оплата' },
  car_left: { uz: '🚙 Mashina ketdi', ru: '🚙 Машина уехала' },
  submit: { uz: '📤 Yuborish', ru: '📤 Отправить' },
  submit_after_left: {
    uz: 'Avval «Mashina ketdi» tugmasini bosing',
    ru: 'Сначала нажмите «Машина уехала»',
  },
  draft_saved: { uz: 'Qoralama saqlandi', ru: 'Черновик сохранён' },
  delete_draft_confirm: {
    uz: 'Qoralama o‘chirilsinmi?',
    ru: 'Удалить черновик?',
  },
  submitted_ok: { uz: 'Yuborildi! Admin ko‘rib chiqadi.', ru: 'Отправлено! Админ рассмотрит.' },
  auto_approved_ok: {
    uz: 'Avtomatik tasdiqlandi (admin hisoboti).',
    ru: 'Подтверждено автоматически (отчёт админа).',
  },

  // Kartochka / ko'rib chiqish
  arrived: { uz: 'Keldi', ru: 'Приехала' },
  left: { uz: 'Ketdi', ru: 'Уехала' },
  downtime: { uz: 'Ustaxonada', ru: 'В сервисе' },
  odometer: { uz: 'Probeg', ru: 'Пробег' },
  author: { uz: 'Xodim', ru: 'Сотрудник' },
  photos: { uz: 'Fotolar', ru: 'Фото' },
  comment: { uz: 'Izoh', ru: 'Комментарий' },
  history_avg: { uz: 'Tarix (oxirgi {n})', ru: 'История (последние {n})' },
  history_none: { uz: 'Bu ish bo‘yicha tarix yo‘q', ru: 'По этой работе истории нет' },
  author_avg: { uz: '{name} o‘rtachasi', ru: 'Среднее у {name}' },
  reduction_rate: { uz: 'narxi {pct}% hollarda kamaytirilgan', ru: 'цену снижали в {pct}% случаев' },
  approve: { uz: '✅ Tasdiqlash', ru: '✅ Подтвердить' },
  reduce_price: { uz: '✏️ Narxni kamaytirish', ru: '✏️ Снизить цену' },
  reopen: { uz: '↩️ Qaytarish', ru: '↩️ Вернуть' },
  reject: { uz: '❌ Rad etish', ru: '❌ Отклонить' },
  new_amount: { uz: 'Yangi summa', ru: 'Новая сумма' },
  reason: { uz: 'Sabab (majburiy)', ru: 'Причина (обязательно)' },
  reason_required: { uz: 'Sabab majburiy', ru: 'Причина обязательна' },
  price_increase_forbidden: {
    uz: 'Narxni oshirib bo‘lmaydi — faqat kamaytirish (R2)',
    ru: 'Повышать цену нельзя — только снижение (R2)',
  },
  send_proposal: { uz: '📨 Taklifni yuborish', ru: '📨 Отправить предложение' },
  quick_choice: { uz: 'Tez tanlov', ru: 'Быстрый выбор' },
  final_decision: { uz: '⚖️ Yakuniy qaror', ru: '⚖️ Окончательное решение' },

  // Kelishuv (usta)
  admin_proposed: { uz: 'Admin taklifi', ru: 'Предложение админа' },
  you_asked: { uz: 'Siz so‘radingiz', ru: 'Вы просили' },
  accept_price: { uz: '✅ Roziman', ru: '✅ Согласен' },
  dispute_price: { uz: '❌ Rozi emasman', ru: '❌ Не согласен' },
  dispute_comment: {
    uz: 'Nima uchun rozi emassiz?',
    ru: 'Почему вы не согласны?',
  },
  auto_accept_note: {
    uz: '⏱ {hours} soat javob bermasangiz — avtomatik rozilik',
    ru: '⏱ Без ответа {hours} ч — согласие автоматически',
  },

  // Profil
  profile: { uz: 'Profil', ru: 'Профиль' },
  language: { uz: 'Til', ru: 'Язык' },
  my_price_behaviour: { uz: 'Mening narx statistikam', ru: 'Моя статистика по цене' },
  stats_lines: { uz: 'Tasdiqlangan ishlar', ru: 'Подтверждённые работы' },
  stats_reduced: { uz: 'Kamaytirilgan', ru: 'Снижено' },
  stats_avg_reduction: { uz: 'O‘rtacha kamaytirish', ru: 'Среднее снижение' },
  stats_disputes: { uz: 'Nizolar', ru: 'Споры' },
  stats_hint_good: {
    uz: '✅ Siz halol narx qo‘yasiz',
    ru: '✅ Вы ставите честную цену',
  },
  stats_hint_high: {
    uz: '🟡 Narxlaringiz tez-tez kamaytirilmoqda',
    ru: '🟡 Ваши цены часто снижают',
  },
  workshop: { uz: 'Ustaxona', ru: 'Мастерская' },
};

export const STATUS_LABEL: Record<SubmissionStatus, { uz: string; ru: string }> = {
  draft: { uz: '📝 Qoralama', ru: '📝 Черновик' },
  submitted: { uz: '⏳ Tasdiq kutmoqda', ru: '⏳ Ждёт подтверждения' },
  in_review: { uz: '👀 Ko‘rilmoqda', ru: '👀 На рассмотрении' },
  price_negotiation: { uz: '💬 Narx kelishuvida', ru: '💬 Согласование цены' },
  price_disputed: { uz: '⚖️ Nizoda', ru: '⚖️ Спор' },
  reopened: { uz: '↩️ Qaytarilgan', ru: '↩️ Возвращён' },
  approved: { uz: '✅ Tasdiqlangan', ru: '✅ Подтверждён' },
  rejected: { uz: '❌ Rad etilgan', ru: '❌ Отклонён' },
  paid: { uz: '💵 To‘langan', ru: '💵 Выплачен' },
};

let current: Lang = 'uz';

export function setLocale(lang: Lang): void {
  current = lang;
  document.documentElement.lang = lang;
}

export function getLocale(): Lang {
  return current;
}

export function t(key: string, params: Record<string, string | number> = {}): string {
  const entry = T[key];
  let text = entry ? entry[current] : key;
  for (const [name, value] of Object.entries(params)) {
    text = text.replace(`{${name}}`, String(value));
  }
  return text;
}

export function statusLabel(status: SubmissionStatus): string {
  return STATUS_LABEL[status]?.[current] ?? status;
}

export function label(value: { uz: string; ru?: string } | undefined): string {
  if (!value) return '';
  return (current === 'ru' ? value.ru : value.uz) || value.uz;
}
