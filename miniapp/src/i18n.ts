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

  // Pastki navigatsiya — qisqa yorliqlar (emoji alohida beriladi)
  nav_home: { uz: 'Asosiy', ru: 'Главная' },
  nav_reports: { uz: 'Hisobotlar', ru: 'Отчёты' },
  nav_period: { uz: 'Davr', ru: 'Период' },
  nav_team: { uz: 'Xodimlar', ru: 'Сотрудники' },
  nav_profile: { uz: 'Profil', ru: 'Профиль' },

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

  // Konstruktorlar (Faza 2)
  builder: { uz: '🧩 Konstruktor', ru: '🧩 Конструктор' },
  builder_hint: {
    uz: 'Yangi rol va shablon — kod yozmasdan, deploy’siz.',
    ru: 'Новая роль и шаблон — без кода и деплоя.',
  },
  templates: { uz: 'Shablonlar', ru: 'Шаблоны' },
  roles: { uz: 'Rollar', ru: 'Роли' },
  new_template: { uz: '+ Yangi shablon', ru: '+ Новый шаблон' },
  new_role: { uz: '+ Yangi rol', ru: '+ Новая роль' },
  draft: { uz: 'Qoralama', ru: 'Черновик' },
  published: { uz: 'Nashr etilgan', ru: 'Опубликован' },
  publish: { uz: '🚀 Nashr qilish', ru: '🚀 Опубликовать' },
  published_ok: { uz: 'Nashr etildi — endi ko‘rinadi', ru: 'Опубликован — теперь виден' },
  saved_ok: { uz: 'Saqlandi', ru: 'Сохранено' },
  draft_warning: {
    uz: 'Qoralama hech kimga ko‘rinmaydi. Nashr qiling.',
    ru: 'Черновик никому не виден. Опубликуйте его.',
  },
  publish_creates_version: {
    uz: 'Tahrir yangi versiya ochadi — eski hisobotlar buzilmaydi.',
    ru: 'Правка создаёт новую версию — старые отчёты не ломаются.',
  },
  template_code: { uz: 'Kod (lotin, o‘zgarmaydi)', ru: 'Код (латиница, неизменяем)' },
  name_uz: { uz: 'Nomi (o‘zbekcha)', ru: 'Название (узбекский)' },
  name_ru: { uz: 'Nomi (ruscha)', ru: 'Название (русский)' },
  icon: { uz: 'Ikonka', ru: 'Иконка' },
  subject: { uz: 'Ob’ekt', ru: 'Объект' },
  subject_vehicle: { uz: 'Mashina', ru: 'Машина' },
  subject_employee: { uz: 'Xodim', ru: 'Сотрудник' },
  subject_none: { uz: 'Yo‘q', ru: 'Нет' },
  has_money: { uz: 'Pul bor (to‘lovga kiradi)', ru: 'Есть сумма (идёт в выплату)' },
  negotiable: { uz: 'Narx kelishiladi', ru: 'Цена согласуется' },
  fields: { uz: 'Maydonlar', ru: 'Поля' },
  add_field: { uz: '+ Maydon qo‘shish', ru: '+ Добавить поле' },
  field_code: { uz: 'Kod', ru: 'Код' },
  field_type: { uz: 'Turi', ru: 'Тип' },
  field_required: { uz: 'Majburiy', ru: 'Обязательное' },
  photo_min: { uz: 'Eng kam foto', ru: 'Мин. фото' },
  photo_max: { uz: 'Eng ko‘p foto', ru: 'Макс. фото' },
  lines_kind: { uz: 'Qator turi', ru: 'Тип строк' },
  lines_labor: { uz: 'Ish haqi', ru: 'Работа' },
  lines_part: { uz: 'Ehtiyot qism', ru: 'Запчасть' },
  no_fields: { uz: 'Hali maydon yo‘q', ru: 'Полей пока нет' },
  role_kind: { uz: 'Rol turi', ru: 'Тип роли' },
  kind_reporter: { uz: 'Hisobot beruvchi', ru: 'Отчитывающийся' },
  kind_admin: { uz: 'Admin', ru: 'Администратор' },
  kind_accountant: { uz: 'Buxgalter', ru: 'Бухгалтер' },
  role_templates: { uz: 'Ko‘radigan shablonlar', ru: 'Видимые шаблоны' },
  system_role: { uz: 'Tizim roli — turi qulflangan', ru: 'Системная роль — тип заблокирован' },
  field_types: {
    uz: 'matn · son · pul · ha/yo‘q · tanlov · foto · mashina · qatorlar · joylashuv',
    ru: 'текст · число · сумма · да/нет · выбор · фото · машина · строки · геолокация',
  },

  // Davr, to'lovlar, eksport (admin/buxgalter)
  period: { uz: '📅 Davr', ru: '📅 Период' },
  period_open: { uz: 'Ochiq', ru: 'Открыт' },
  period_closed: { uz: 'Yopilgan', ru: 'Закрыт' },
  precheck: { uz: 'Yopishdan oldin', ru: 'Перед закрытием' },
  precheck_clean: { uz: 'To‘siq yo‘q', ru: 'Препятствий нет' },
  precheck_unapproved: { uz: '{n} ta hisobot tasdiqlanmagan', ru: '{n} отчётов не подтверждено' },
  precheck_negotiation: {
    uz: '{n} ta hisobot narx kelishuvida',
    ru: '{n} отчётов в согласовании цены',
  },
  precheck_reopened: {
    uz: '{n} ta hisobot qaytarilgan (tuzatilmagan)',
    ru: '{n} отчётов возвращено (не исправлены)',
  },
  precheck_drafts: {
    uz: '{n} ta qoralama {days} kundan beri turibdi',
    ru: '{n} черновиков висят более {days} дн.',
  },
  close_period: { uz: '🔒 Oyni yopish', ru: '🔒 Закрыть месяц' },
  confirm_close: { uz: 'Ha, yopilsin', ru: 'Да, закрыть' },
  close_blocked: {
    uz: 'To‘siqlar hal qilinmaguncha yopib bo‘lmaydi.',
    ru: 'Пока препятствия не сняты, закрыть нельзя.',
  },
  period_closed_ok: { uz: 'Davr yopildi', ru: 'Период закрыт' },
  payouts: { uz: 'To‘lov varaqalari', ru: 'Ведомости' },
  payouts_after_close: {
    uz: 'Varaqalar oy yopilganda hosil bo‘ladi.',
    ru: 'Ведомости формируются при закрытии месяца.',
  },
  mark_paid: { uz: 'To‘landi deb belgilash', ru: 'Отметить выплаченным' },
  marked_paid: { uz: 'To‘landi deb belgilandi', ru: 'Отмечено как выплачено' },
  paid: { uz: 'To‘langan', ru: 'Выплачено' },
  total: { uz: 'Jami', ru: 'Итого' },
  export: { uz: '📥 Eksport', ru: '📥 Экспорт' },
  export_via_bot: {
    uz: 'Excel botga hujjat bo‘lib keladi.',
    ru: 'Excel придёт документом в бот.',
  },
  export_sent: { uz: 'Excel botga yuborildi', ru: 'Excel отправлен в бот' },
  export_submissions: { uz: 'Hisobotlar', ru: 'Отчёты' },
  export_payouts: { uz: 'To‘lovlar', ru: 'Выплаты' },
  export_savings: { uz: 'Kelishuv tejamkorligi', ru: 'Экономия согласования' },

  // Hisobotlar arxivi (admin/buxgalter)
  all_reports: { uz: '📋 Hisobotlar', ru: '📋 Отчёты' },
  filter_all: { uz: 'Hammasi', ru: 'Все' },
  filter_pending: { uz: 'Kutmoqda', ru: 'Ожидают' },
  filter_negotiation: { uz: 'Kelishuvda', ru: 'В согласовании' },
  filter_approved: { uz: 'Tasdiqlangan', ru: 'Подтверждены' },
  filter_rejected: { uz: 'Rad etilgan', ru: 'Отклонены' },
  load_more: { uz: 'Yana yuklash', ru: 'Показать ещё' },

  // Xodimlar (admin)
  employees: { uz: '👥 Xodimlar', ru: '👥 Сотрудники' },
  new_employee: { uz: '+ Yangi xodim', ru: '+ Новый сотрудник' },
  employee_added: { uz: 'Xodim reyestrga qo‘shildi', ru: 'Сотрудник добавлен в реестр' },
  full_name: { uz: 'F.I.Sh.', ru: 'Ф.И.О.' },
  phone: { uz: 'Telefon', ru: 'Телефон' },
  workshop_optional: { uz: 'Ustaxona nomi (ixtiyoriy)', ru: 'Название мастерской (необяз.)' },
  employee_link_hint: {
    uz: 'Qo‘shgach xodim botga /start bosib SHU raqamni yuborsin — hisob shunda bog‘lanadi.',
    ru: 'После добавления сотрудник нажимает /start в боте и отправляет ЭТОТ номер.',
  },
  no_employees: { uz: 'Reyestr bo‘sh', ru: 'Реестр пуст' },
  not_linked: { uz: 'kutilmoqda', ru: 'ожидается' },
  this_is_you: { uz: 'Bu — sizning hisobingiz', ru: 'Это ваша учётная запись' },
  change_role: { uz: 'Rolni o‘zgartirish', ru: 'Сменить роль' },
  status: { uz: 'Holat', ru: 'Статус' },
  status_active: { uz: 'Faol', ru: 'Активен' },
  status_blocked: { uz: 'Bloklangan', ru: 'Заблокирован' },
  status_fired: { uz: 'Bo‘shatilgan', ru: 'Уволен' },
  fired_keeps_data: {
    uz: 'Bloklash/bo‘shatishda kirish yopiladi, hisobotlar va to‘lovlar qoladi.',
    ru: 'При блокировке/увольнении вход закрыт, отчёты и выплаты остаются.',
  },

  linkable_empty: {
    uz: 'Bu mashina bo‘yicha bog‘lanadigan hisobot yo‘q',
    ru: 'По этой машине связанных отчётов нет',
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

/** Holatning vizual ohangi — ro'yxatdagi rangli belgini tanlaydi. */
export type StatusTone = 'neutral' | 'wait' | 'talk' | 'good' | 'bad';

export const STATUS_TONE: Record<SubmissionStatus, StatusTone> = {
  draft: 'neutral',
  submitted: 'wait',
  in_review: 'wait',
  price_negotiation: 'talk',
  price_disputed: 'bad',
  reopened: 'talk',
  approved: 'good',
  rejected: 'bad',
  paid: 'good',
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

/** Emoji'siz matn — rangli belgida (`StatusBadge`) nuqta emoji o'rnini bosadi. */
export function statusText(status: SubmissionStatus): string {
  return statusLabel(status).replace(/^\S+\s+/, '');
}

export function label(value: { uz: string; ru?: string } | undefined): string {
  if (!value) return '';
  return (current === 'ru' ? value.ru : value.uz) || value.uz;
}
