/**
 * uz (lotin) + uz_cyrl (kirill) + ru — til `employees.lang` da saqlanadi.
 *
 * Kirillcha matnlar lug'atda takrorlanmaydi: `uz` dan avtomatik
 * translitatsiya qilinadi (`translit.ts`). Kerak bo'lsa kalitga
 * `uz_cyrl: '...'` ni qo'lda yozib, avtomatikani bekor qilish mumkin.
 */

import type { DisplayStatus } from './display-status';
import type { Lang } from './types';
import { toCyrillic } from './translit';

type Entry = { uz: string; ru: string; uz_cyrl?: string };
type Dict = Record<string, Entry>;

/** Joriy tildagi matn: kirill uchun — qo'lda yozilgani yoki translitatsiya. */
function resolve(entry: Entry | undefined, lang: Lang, fallback: string): string {
  if (!entry) return fallback;
  if (lang === 'uz_cyrl') return entry.uz_cyrl ?? toCyrillic(entry.uz);
  return entry[lang] || entry.uz;
}

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
  nav_debts: { uz: 'Qarzlar', ru: 'Долги' },
  nav_team: { uz: 'Xodimlar', ru: 'Сотрудники' },
  nav_profile: { uz: 'Profil', ru: 'Профиль' },

  // Bosh ekran
  in_workshop: { uz: 'Ustaxonada', ru: 'В сервисе' },
  drafts: { uz: 'Qoralamalar', ru: 'Черновики' },
  negotiation: { uz: 'Narx kelishuvi', ru: 'Согласование цены' },
  awaiting_review: { uz: 'Tasdiq kutmoqda', ru: 'Ждут подтверждения' },
  approved_month: { uz: 'Bu oy tasdiqlangan', ru: 'Подтверждено за месяц' },
  this_month: { uz: 'Bu oy', ru: 'Этот месяц' },
  more_details: { uz: 'Qo‘shimcha', ru: 'Дополнительно' },
  requested: { uz: 'So‘radim', ru: 'Запросил' },
  approved_sum: { uz: 'Tasdiqlandi', ru: 'Подтверждено' },
  // Hisobot kartochkasidagi to'lov holati — aynan SHU ish bo'yicha (ADR-0015).
  // `payable_total` «Tasdiqlandi» dan katta bo'lishi mumkin: unga «o'z
  // hisobimdan» qismlar ham kiradi (R5).
  payable_total: { uz: 'To‘lanadi', ru: 'К выплате' },
  remaining: { uz: 'Qoldi', ru: 'Осталось' },
  car_arrived: { uz: '🚗 Mashina keldi', ru: '🚗 Машина приехала' },
  my_reports: { uz: 'Hisobotlarim', ru: 'Мои отчёты' },
  no_reports: { uz: 'Hozircha hisobot yo‘q', ru: 'Отчётов пока нет' },
  choose_template: { uz: 'Qaysi hisobot?', ru: 'Какой отчёт?' },

  // Admin
  admin_dashboard: { uz: 'Boshqaruv paneli', ru: 'Панель управления' },
  pending: { uz: 'Tasdiq kutmoqda', ru: 'Ждут подтверждения' },
  cars_in_service: { uz: 'Ustaxonada', ru: 'В сервисе' },
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

  // Qarz daftari, to'lovlar, eksport (admin/buxgalter) — ADR-0015
  tab_debts: { uz: 'Qarzlar', ru: 'Долги' },
  // Avans alohida tabda (2026-08-04): qarzdorlar ro'yxatida «+60 000 Avans»
  // qatorlari turgani «kimga qancha qarzmiz?» degan savolni ko'mib qo'yardi.
  tab_advance: { uz: 'Avans', ru: 'Аванс' },
  tab_paid: { uz: 'To‘langan', ru: 'Выплаты' },
  total_debt: { uz: 'Umumiy qarz', ru: 'Общий долг' },
  total_advance: { uz: 'Umumiy avans', ru: 'Общий аванс' },
  advance: { uz: 'Avans', ru: 'Аванс' },
  advance_hint: {
    uz: 'Yangi ish tasdiqlanganda avansdan avtomatik ushlab qolinadi.',
    ru: 'При подтверждении новой работы аванс списывается автоматически.',
  },
  debtors: { uz: 'Qarzdorlar', ru: 'Должники' },
  advance_holders: { uz: 'Avansi borlar', ru: 'С авансом' },
  no_advance: { uz: 'Avans yo‘q', ru: 'Авансов нет' },
  has_debt: { uz: 'Qarzi: {sum}', ru: 'Долг: {sum}' },
  no_debt: { uz: 'Qarz yo‘q', ru: 'Долгов нет' },
  debt_reports: { uz: 'To‘lanmagan hisobotlar', ru: 'Неоплаченные отчёты' },
  reports_count: { uz: 'ta ish', ru: 'работ' },
  partly_paid: { uz: 'qisman to‘langan', ru: 'частично оплачено' },
  make_payment: { uz: 'To‘lov qilish', ru: 'Выплатить' },
  // Belgilanganlarning yakuni — alohida tugma emas, xulosa qatori: summa
  // maydoni shu qiymatga tenglashadi, to'lov bitta tugma bilan qayd etiladi.
  selected: { uz: 'Belgilangan', ru: 'Выбрано' },
  pay_amount: { uz: 'Summa', ru: 'Сумма' },
  pay_by_amount: { uz: 'To‘lovni qayd etish', ru: 'Записать выплату' },
  // Tasdiq oynasi — summa maydoni ostidagi izohlarning o'rnini bosdi: pul
  // qayerga ketishi qaror qabul qilinadigan lahzada aytiladi. To'lov keyin
  // faqat `void` bilan qaytariladi, shuning uchun tasdiq majburiy.
  // Matn tanlovga qarab o'zgarmaydi: qoida ikkala holatda ham bitta — FIFO,
  // eng eskisidan. Chekbox faqat taqsimot doirasini toraytiradi.
  pay_confirm: {
    uz: '{sum} to‘lansinmi? Eng eski qarzdan boshlab taqsimlanadi.',
    ru: 'Выплатить {sum}? Распределится с самого старого долга.',
  },
  pay_confirm_advance: {
    uz: 'Ortiqcha {sum} avans bo‘lib qoladi.',
    ru: 'Излишек {sum} останется авансом.',
  },
  payment_saved: { uz: 'To‘lov qayd etildi', ru: 'Выплата записана' },
  payment_history: { uz: 'To‘lovlar tarixi', ru: 'История выплат' },
  no_payments: { uz: 'Hozircha to‘lov yo‘q', ru: 'Выплат пока нет' },
  voided: { uz: 'bekor qilingan', ru: 'отменено' },
  // To'lov kartochkasi — tarixdagi qatorni ochganda. To'lov tahrirlanmaydi
  // (P5), shuning uchun bu yer faqat o'qish uchun: pul qaysi ishlarga tushdi.
  payment_date: { uz: 'Sana', ru: 'Дата' },
  payment_covers: { uz: 'Qaysi ishlarga', ru: 'На какие работы' },
  fully_closed: { uz: 'to‘liq yopildi', ru: 'закрыт полностью' },
  partly_closed: { uz: 'qisman yopildi', ru: 'закрыт частично' },
  payment_voided_note: {
    uz: 'To‘lov bekor qilingan — qarz qayta ochilgan.',
    ru: 'Выплата отменена — долг открыт заново.',
  },
  paid: { uz: 'To‘langan', ru: 'Выплачено' },
  total: { uz: 'Jami', ru: 'Итого' },
  export: { uz: '📥 Eksport', ru: '📥 Экспорт' },
  export_hint: {
    uz: 'Excel botga hujjat bo‘lib keladi.',
    ru: 'Excel придёт документом в бот.',
  },
  export_sent: { uz: 'Excel botga yuborildi', ru: 'Excel отправлен в бот' },
  export_submissions: { uz: 'Hisobotlar', ru: 'Отчёты' },
  export_debts: { uz: 'Qarzlar va to‘lovlar', ru: 'Долги и выплаты' },

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

  // E'lon (admin → barcha xodimlar, bot orqali)
  broadcast: { uz: '📢 E‘lon', ru: '📢 Объявление' },
  broadcast_hint: {
    uz: 'Xabar botga bog‘langan barcha faol xodimlarga boradi.',
    ru: 'Сообщение получат все активные сотрудники, привязанные к боту.',
  },
  broadcast_placeholder: {
    uz: 'Masalan: Ertaga ustaxona 9:00 da ochiladi.',
    ru: 'Например: завтра мастерская откроется в 9:00.',
  },
  broadcast_counter: { uz: '{n} / {max}', ru: '{n} / {max}' },
  broadcast_too_long: {
    uz: 'Matn juda uzun — {max} belgidan oshmasin',
    ru: 'Текст слишком длинный — не более {max} символов',
  },
  broadcast_recipients: { uz: 'Qabul qiluvchilar', ru: 'Получатели' },
  broadcast_no_recipients: {
    uz: 'Botga bog‘langan faol xodim yo‘q — yuborib bo‘lmaydi.',
    ru: 'Нет активных сотрудников, привязанных к боту — отправить нельзя.',
  },
  broadcast_send: { uz: '📨 Yuborish', ru: '📨 Отправить' },
  broadcast_confirm: {
    uz: '{n} ta xodimga yuborilsinmi? Buni qaytarib bo‘lmaydi.',
    ru: 'Отправить {n} сотрудникам? Отменить это нельзя.',
  },
  // Qabul qiluvchilar soni ma'lum bo'lmasa (ro'yxat yuklanmadi) — noaniq son
  // aytilmaydi, chunki bu qaytarib bo'lmaydigan amalning tasdig'i.
  broadcast_confirm_any: {
    uz: 'E‘lon barcha faol xodimlarga yuborilsinmi? Buni qaytarib bo‘lmaydi.',
    ru: 'Отправить объявление всем активным сотрудникам? Отменить это нельзя.',
  },
  broadcast_sent: { uz: 'E‘lon {n} ta xodimga yuborildi', ru: 'Объявление отправлено {n} сотрудникам' },
  broadcast_history: { uz: 'Yuborilgan e‘lonlar', ru: 'Отправленные объявления' },
  broadcast_empty: { uz: 'Hali e‘lon yuborilmagan', ru: 'Объявлений пока не было' },
  // ⚠️ Bo'sh ro'yxatdan farqli matn: xatolikni «e'lon yo'q» deb ko'rsatsak,
  // admin yuborilgan e'lonni qaytadan yuboradi.
  broadcast_history_error: {
    uz: 'Tarixni yuklab bo‘lmadi — e‘lon yuborilgan bo‘lishi mumkin.',
    ru: 'Не удалось загрузить историю — объявление могло быть отправлено.',
  },
  broadcast_error: {
    uz: 'E‘lonni yuborib bo‘lmadi. Tarixni tekshiring.',
    ru: 'Не удалось отправить объявление. Проверьте историю.',
  },
  // Tarmoq uzildi: so'rov serverga yetib borgan bo'lishi ham mumkin
  broadcast_unknown: {
    uz: 'Tarmoq uzildi — e‘lon yuborilgan bo‘lishi mumkin. Tarixni tekshiring.',
    ru: 'Связь прервалась — объявление могло уйти. Проверьте историю.',
  },
  broadcast_delivered: { uz: 'yetkazildi', ru: 'доставлено' },
  broadcast_failed: { uz: 'xato', ru: 'ошибка' },
  broadcast_pending: { uz: 'navbatda', ru: 'в очереди' },

  linkable_empty: {
    uz: 'Bu mashina bo‘yicha bog‘lanadigan hisobot yo‘q',
    ru: 'По этой машине связанных отчётов нет',
  },

  // Forma
  form_title: { uz: 'Hisobot', ru: 'Отчёт' },
  step: { uz: 'Qadam', ru: 'Шаг' },
  photo_take: { uz: '📷 Kamera', ru: '📷 Камера' },
  photo_gallery: { uz: '🖼 Galereya', ru: '🖼 Галерея' },
  // ADR-0020: galereya ochildi, lekin taklif qilinadigan yo'l — kamera.
  photo_hint: {
    uz: 'Iloji bo‘lsa shu yerda kamerada oling',
    ru: 'По возможности снимите камерой прямо здесь',
  },
  photo_count: { uz: '{n} / {max} ta foto', ru: '{n} / {max} фото' },
  uploading: { uz: 'Yuklanmoqda…', ru: 'Загрузка…' },
  plate_placeholder: { uz: '01A123BC', ru: '01A123BC' },
  vehicle_not_found: { uz: 'Mashina reyestrda topilmadi', ru: 'Машина не найдена в реестре' },
  works: { uz: 'Bajarilgan ishlar', ru: 'Выполненные работы' },
  parts: { uz: 'Ishlatilgan qismlar', ru: 'Использованные запчасти' },
  my_price: { uz: 'Mening narxim', ru: 'Моя цена' },
  // ⚠️ Raqamli placeholder («250 000») to'ldirilgan qiymatdek ko'rinardi va
  // usta narxni yozmasdan o'tib ketardi (2026-08-05). Endi — matnli ko'rsatma.
  price_placeholder: { uz: 'Summani yozing', ru: 'Впишите сумму' },
  line_name_placeholder: {
    uz: 'Nomini yozing yoki ro‘yxatdan tanlang',
    ru: 'Впишите название или выберите из списка',
  },
  price_hint_own: {
    uz: 'Narxni o‘zingiz belgilaysiz — admin ko‘rib chiqadi',
    ru: 'Цену указываете вы — админ рассмотрит',
  },
  part_price_note: {
    uz: 'ⓘ Narxni faqat o‘z hisobingizdan olgan qism uchun kiritasiz',
    ru: 'ⓘ Цену указываете только для запчастей, купленных за свой счёт',
  },
  self_funded: { uz: 'O‘z hisobimdan oldim', ru: 'Купил за свой счёт' },
  // ADR-0021: chek majburiy emas — talab qilib bo'lmaydigan narsani va'da
  // qilmaymiz, lekin uni so'rashda davom etamiz.
  self_funded_hint: {
    uz: 'Narx kiritiladi va sizga qaytariladi. Chek bo‘lsa — qo‘shing.',
    ru: 'Укажете цену, деньги вернут. Есть чек — приложите.',
  },
  add_work: { uz: '➕ Ish qo‘shish', ru: '➕ Добавить работу' },
  add_part: { uz: '➕ Qism qo‘shish', ru: '➕ Добавить запчасть' },
  total_labor: { uz: 'Mening ish haqim', ru: 'Моя оплата' },
  total_own_parts: { uz: 'O‘z hisobimdan', ru: 'За свой счёт' },
  car_left: { uz: '🚙 Mashina ketdi', ru: '🚙 Машина уехала' },
  submit: { uz: '📤 Yuborish', ru: '📤 Отправить' },
  // ⭐ Bitta tugma (2026-08-05): «Mashina ketdi» va «Yuborish» ikki alohida
  // tugma edi — usta birinchisini bosib to'xtab qolardi, holbuki mashina
  // ketgani hisobot tayyor degani.
  left_and_submit: { uz: '🚙 Mashina ketdi — yuborish', ru: '🚙 Машина уехала — отправить' },
  left_and_submit_confirm: {
    uz: 'Ketish vaqti qayd etilib, hisobot adminga yuborilsinmi?',
    ru: 'Зафиксировать время выезда и отправить отчёт админу?',
  },
  submit_confirm: {
    uz: 'Hisobot adminga yuborilsinmi?',
    ru: 'Отправить отчёт админу?',
  },
  submit_hint: {
    uz: 'Yuborilgach tahrirlab bo‘lmaydi — admin ko‘rib chiqadi.',
    ru: 'После отправки редактировать нельзя — отчёт уйдёт на проверку.',
  },
  // Har qadam mustaqil (2026-08-05): saqlangach ekran yopiladi, keyingi
  // qadamga o'zi o'tmaydi — usta ish bilan band bo'lishi mumkin.
  save_step: { uz: '💾 Saqlash', ru: '💾 Сохранить' },
  save_step_hint: {
    uz: 'Qoralama saqlanadi va ilova yopiladi — keyin qolgan joyidan davom etasiz',
    ru: 'Черновик сохранится и форма закроется — продолжите с того места, где остановились',
  },
  incomplete_step: {
    uz: '{n}-qadamda to‘ldirilmagan maydon bor',
    ru: 'На шаге {n} есть незаполненное поле',
  },
  min_chars: { uz: 'Kamida {n} ta belgi yozing', ru: 'Напишите минимум {n} символа' },
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
  author: { uz: 'Xodim', ru: 'Сотрудник' },
  photos: { uz: 'Fotolar', ru: 'Фото' },
  comment: { uz: 'Izoh', ru: 'Комментарий' },
  history_avg: { uz: 'Tarix (oxirgi {n})', ru: 'История (последние {n})' },
  approve: { uz: '✅ Tasdiqlash', ru: '✅ Подтвердить' },
  reduce_price: { uz: '✏️ Narxni kamaytirish', ru: '✏️ Снизить цену' },
  reopen: { uz: '↩️ Qaytarish', ru: '↩️ Вернуть' },
  reject: { uz: '❌ Rad etish', ru: '❌ Отклонить' },
  new_amount: { uz: 'Yangi summa', ru: 'Новая сумма' },
  reduce_hint: {
    uz: 'Har bir xizmatga o‘z summangizni qo‘ying. Tegilmagani o‘z narxida qoladi.',
    ru: 'Укажите свою сумму по каждой работе. Нетронутые останутся в своей цене.',
  },
  keep_price: { uz: 'O‘zgarishsiz qoldirish', ru: 'Оставить без изменений' },
  unchanged_lines_note: {
    uz: 'Qolgan xizmatlar o‘z narxida qoldi.',
    ru: 'Остальные работы остались в своей цене.',
  },
  reason: { uz: 'Sabab (majburiy)', ru: 'Причина (обязательно)' },
  reason_required: { uz: 'Sabab majburiy', ru: 'Причина обязательна' },
  price_increase_forbidden: {
    uz: 'Narxni oshirib bo‘lmaydi — faqat kamaytirish (R2)',
    ru: 'Повышать цену нельзя — только снижение (R2)',
  },
  send_proposal: { uz: '📨 Taklifni yuborish', ru: '📨 Отправить предложение' },
  quick_choice: { uz: 'Tez tanlov', ru: 'Быстрый выбор' },
  // ⭐ ADR-0023 — «Yakuniy qaror» olib tashlandi. Nizoda adminning ikkita
  // yo'li bor, ikkalasi ham kelishuvni davom ettiradi yoki ustaga beriladi.
  accept_author_price: { uz: '✅ Usta narxiga roziman', ru: '✅ Согласен с ценой мастера' },
  accept_author_price_confirm: {
    uz: 'Usta so‘ragan summa yakuniy bo‘lsinmi? Kamaytirish bekor qilinadi.',
    ru: 'Утвердить сумму, которую просил мастер? Снижение отменится.',
  },
  propose_new_price: { uz: '✏️ Yangi narx berish', ru: '✏️ Предложить новую цену' },
  dispute_admin_hint: {
    uz: 'Usta rozi emas. Yo yangi narx bering, yo uning narxiga rozi bo‘ling — kelishuvni bir tomonlama yopib bo‘lmaydi.',
    ru: 'Мастер не согласен. Предложите новую цену или согласитесь с его — закрыть спор в одностороннем порядке нельзя.',
  },

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
  workshop: { uz: 'Ustaxona', ru: 'Мастерская' },
};

// ⚠️ `partly_paid` — serverda YO'Q, ko'rsatish holati (`display-status.ts`).
export const STATUS_LABEL: Record<DisplayStatus, Entry> = {
  draft: { uz: '📝 Qoralama', ru: '📝 Черновик' },
  submitted: { uz: '⏳ Tasdiq kutmoqda', ru: '⏳ Ждёт подтверждения' },
  in_review: { uz: '👀 Ko‘rilmoqda', ru: '👀 На рассмотрении' },
  price_negotiation: { uz: '💬 Narx kelishuvida', ru: '💬 Согласование цены' },
  price_disputed: { uz: '⚖️ Nizoda', ru: '⚖️ Спор' },
  reopened: { uz: '↩️ Qaytarilgan', ru: '↩️ Возвращён' },
  approved: { uz: '✅ Tasdiqlangan', ru: '✅ Подтверждён' },
  rejected: { uz: '❌ Rad etilgan', ru: '❌ Отклонён' },
  partly_paid: { uz: '🧾 Qisman to‘langan', ru: '🧾 Частично выплачен' },
  paid: { uz: '💵 To‘langan', ru: '💵 Выплачен' },
};

/** Holatning vizual ohangi — ro'yxatdagi rangli belgini tanlaydi. */
export type StatusTone = 'neutral' | 'wait' | 'talk' | 'good' | 'bad';

export const STATUS_TONE: Record<DisplayStatus, StatusTone> = {
  draft: 'neutral',
  submitted: 'wait',
  in_review: 'wait',
  price_negotiation: 'talk',
  price_disputed: 'bad',
  reopened: 'talk',
  approved: 'good',
  rejected: 'bad',
  // Ish tugagan, lekin pul to'liq berilmagan — «kutish» ohangi: yashil bo'lsa
  // qarz qolgani ko'zga tashlanmaydi.
  partly_paid: 'wait',
  paid: 'good',
};

let current: Lang = 'uz';

export function setLocale(lang: Lang): void {
  current = lang;
  // HTML atributi BCP 47 bo'lishi kerak: uz_cyrl → uz-Cyrl
  document.documentElement.lang = lang === 'uz_cyrl' ? 'uz-Cyrl' : lang;
}

export function getLocale(): Lang {
  return current;
}

export function t(key: string, params: Record<string, string | number> = {}): string {
  const entry = T[key];
  let text = resolve(entry, current, key);
  for (const [name, value] of Object.entries(params)) {
    text = text.replace(`{${name}}`, String(value));
  }
  return text;
}

export function statusLabel(status: DisplayStatus): string {
  return resolve(STATUS_LABEL[status], current, status);
}

/** Emoji'siz matn — rangli belgida (`StatusBadge`) nuqta emoji o'rnini bosadi. */
export function statusText(status: DisplayStatus): string {
  return statusLabel(status).replace(/^\S+\s+/, '');
}

/** Backenddan kelgan ikki tilli nom (shablon, maydon yorlig'i…). */
export function label(value: { uz: string; ru?: string } | undefined): string {
  if (!value) return '';
  if (current === 'ru') return value.ru || value.uz;
  if (current === 'uz_cyrl') return toCyrillic(value.uz);
  return value.uz;
}
