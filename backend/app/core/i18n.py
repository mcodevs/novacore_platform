"""i18n — uz (lotin) + ru, 1-kundan (docs/03-integrations/02-telegram-bot-miniapp.md §4).

Barcha foydalanuvchi matnlari shu yerda. Kodda "qattiq" matn yozilmaydi.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import structlog

from app.core.config import TASHKENT

_log = structlog.get_logger(__name__)

LANGS = ("uz", "ru")
DEFAULT_LANG = "uz"

T: dict[str, dict[str, str]] = {
    # --- Umumiy ---
    "yes": {"uz": "Ha", "ru": "Да"},
    "no": {"uz": "Yo'q", "ru": "Нет"},
    "cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена"},
    "back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад"},
    "skip": {"uz": "⏭ O'tkazib yuborish", "ru": "⏭ Пропустить"},
    "done": {"uz": "✅ Tayyor", "ru": "✅ Готово"},
    "cancelled": {"uz": "Bekor qilindi.", "ru": "Отменено."},
    "unknown_command": {
        "uz": "Tushunmadim. Menyudan tanlang yoki /yordam ni bosing.",
        "ru": "Не понял. Выберите из меню или нажмите /yordam.",
    },
    "error_generic": {
        "uz": "⚠️ Xatolik yuz berdi. Birozdan keyin qayta urinib ko'ring.",
        "ru": "⚠️ Произошла ошибка. Попробуйте ещё раз позже.",
    },
    "currency": {"uz": "so'm", "ru": "сум"},
    "nothing_found": {"uz": "Hech narsa topilmadi.", "ru": "Ничего не найдено."},
    "sum_short": {"uz": "so'm", "ru": "сум"},
    # --- Ro'yxatdan o'tish ---
    "start_greeting": {
        "uz": (
            "👋 <b>NovaCore</b> — xodimlar platformasiga xush kelibsiz.\n\n"
            "Bu yerda ta'mir hisobotlari yuboriladi, narx kelishiladi va ish haqi "
            "hisoblanadi.\n\n"
            "ℹ️ Tizim saqlaydi: F.I.Sh., telefon raqami, Telegram ID, hisobotlaringiz "
            "va fotolar. Passport yoki JSHSHIR <b>saqlanmaydi</b>.\n\n"
            "Davom etish uchun telefon raqamingizni yuboring 👇"
        ),
        "ru": (
            "👋 Добро пожаловать в <b>NovaCore</b> — платформу для сотрудников.\n\n"
            "Здесь отправляются отчёты о ремонте, согласуется цена и считается "
            "оплата.\n\n"
            "ℹ️ Система хранит: Ф.И.О., номер телефона, Telegram ID, ваши отчёты и "
            "фото. Паспорт и ПИНФЛ <b>не хранятся</b>.\n\n"
            "Для продолжения отправьте свой номер телефона 👇"
        ),
    },
    "btn_share_phone": {"uz": "📱 Raqamni yuborish", "ru": "📱 Отправить номер"},
    "contact_mismatch": {
        "uz": "❌ Bu sizning raqamingiz emas. Faqat <b>o'z</b> raqamingizni yuboring.",
        "ru": "❌ Это не ваш номер. Отправьте <b>свой</b> номер телефона.",
    },
    "not_in_registry": {
        "uz": (
            "❌ Siz xodimlar reyestrida yo'qsiz.\n\n"
            "Raqam: <code>{phone}</code>\nAdminga murojaat qiling."
        ),
        "ru": (
            "❌ Вас нет в реестре сотрудников.\n\n"
            "Номер: <code>{phone}</code>\nОбратитесь к администратору."
        ),
    },
    "employee_blocked": {
        "uz": "⛔️ Sizning kirishingiz vaqtincha bloklangan. Adminga murojaat qiling.",
        "ru": "⛔️ Ваш доступ временно заблокирован. Обратитесь к администратору.",
    },
    "employee_fired": {
        "uz": "⛔️ Siz endi faol xodim emassiz. Kirish yopilgan.",
        "ru": "⛔️ Вы больше не активный сотрудник. Доступ закрыт.",
    },
    "account_taken": {
        "uz": "❌ Bu raqam boshqa Telegram akkauntga biriktirilgan. Adminga murojaat qiling.",
        "ru": "❌ Этот номер привязан к другому Telegram-аккаунту. Обратитесь к админу.",
    },
    "registered": {
        "uz": "✅ Xush kelibsiz, <b>{name}</b>!\nRolingiz: {icon} <b>{role}</b>",
        "ru": "✅ Добро пожаловать, <b>{name}</b>!\nВаша роль: {icon} <b>{role}</b>",
    },
    "need_start": {
        "uz": "Avval /start buyrug'ini bosing.",
        "ru": "Сначала нажмите /start.",
    },
    # --- Menyu ---
    "menu_title": {"uz": "{icon} <b>NovaCore — {role}</b>", "ru": "{icon} <b>NovaCore — {role}</b>"},
    "menu_car_arrived": {"uz": "🚗 Mashina keldi", "ru": "🚗 Машина приехала"},
    "menu_drafts": {"uz": "📝 Qoralamalar", "ru": "📝 Черновики"},
    "menu_negotiation": {"uz": "💬 Narx kelishuvi", "ru": "💬 Согласование цены"},
    "menu_my_reports": {"uz": "📋 Hisobotlarim", "ru": "📋 Мои отчёты"},
    "menu_my_money": {"uz": "💰 Bu oy", "ru": "💰 Этот месяц"},
    "menu_pending": {"uz": "⏳ Tasdiq kutmoqda", "ru": "⏳ Ждут подтверждения"},
    "menu_daily": {"uz": "📊 Bugungi hisobot", "ru": "📊 Отчёт за сегодня"},
    "menu_period": {"uz": "📅 Davr", "ru": "📅 Период"},
    "menu_export": {"uz": "📥 Eksport", "ru": "📥 Экспорт"},
    "menu_lang": {"uz": "🌐 Til", "ru": "🌐 Язык"},
    "menu_help": {"uz": "❓ Yordam", "ru": "❓ Помощь"},
    "menu_app": {"uz": "🧩 Mini App", "ru": "🧩 Mini App"},
    "open_app": {"uz": "🧩 Ochish", "ru": "🧩 Открыть"},
    "app_not_configured": {
        "uz": "Mini App hali sozlanmagan. Barcha amallar shu bot orqali bajariladi.",
        "ru": "Mini App пока не настроен. Все действия доступны в этом боте.",
    },
    # --- Til ---
    "lang_choose": {"uz": "Tilni tanlang:", "ru": "Выберите язык:"},
    "lang_changed": {"uz": "✅ Til o'zgartirildi.", "ru": "✅ Язык изменён."},
    # --- Yordam ---
    "help_reporter": {
        "uz": (
            "<b>Qanday ishlaydi</b>\n\n"
            "Barcha ishlar <b>Mini App</b> ichida: <b>🧩 Mini App</b> tugmasini bosing.\n\n"
            "1️⃣ Mashina keldi → ilovada <b>🚗 Mashina keldi</b>\n"
            "2️⃣ Forma ketma-ket so'raydi: raqam, foto, probeg, muammo\n"
            "3️⃣ Bajarilgan ishlar va <b>o'z narxingiz</b>\n"
            "4️⃣ Ish tugadi → <b>🚙 Mashina ketdi</b> → <b>📤 Yuborish</b>\n"
            "5️⃣ Admin narxni kamaytirsa — shu yerga xabar keladi, "
            "<b>Ochish</b> tugmasi orqali javob berasiz\n\n"
            "⏱ 48 soat javob bermasangiz — avtomatik rozilik hisoblanadi.\n\n"
            "Bu botda faqat: kirish, til, yordam va bildirishnomalar."
        ),
        "ru": (
            "<b>Как это работает</b>\n\n"
            "Вся работа — внутри <b>Mini App</b>: нажмите <b>🧩 Mini App</b>.\n\n"
            "1️⃣ Машина приехала → в приложении <b>🚗 Машина приехала</b>\n"
            "2️⃣ Форма спросит по шагам: номер, фото, пробег, проблема\n"
            "3️⃣ Выполненные работы и <b>ваша цена</b>\n"
            "4️⃣ Работа окончена → <b>🚙 Машина уехала</b> → <b>📤 Отправить</b>\n"
            "5️⃣ Если админ снизит цену — уведомление придёт сюда, "
            "ответите через кнопку <b>Открыть</b>\n\n"
            "⏱ Без ответа 48 часов — согласие засчитывается автоматически.\n\n"
            "В боте только: вход, язык, справка и уведомления."
        ),
    },
    "help_admin": {
        "uz": (
            "<b>Admin imkoniyatlari</b> — hammasi <b>Mini App</b> ichida\n\n"
            "• Tasdiq navbati, kartochkada tarixiy narx\n"
            "• ✅ tasdiqlash · ✏️ narxni kamaytirish (sabab majburiy) · "
            "↩️ qaytarish · ❌ rad etish\n"
            "• 📋 Hisobotlar arxivi · 📅 Davr va oy yopilishi · 📥 Excel eksport\n"
            "• 👥 Xodimlar · 🧩 Rol va shablon konstruktori\n\n"
            "⚠️ Narxni <b>faqat kamaytirish</b> mumkin (R2). O'z hisobotingiz "
            "avtomatik tasdiqlanadi (R1a).\n\n"
            "Excel botga hujjat bo'lib keladi."
        ),
        "ru": (
            "<b>Возможности администратора</b> — всё внутри <b>Mini App</b>\n\n"
            "• Очередь на подтверждение, история цен в карточке\n"
            "• ✅ подтвердить · ✏️ снизить цену (причина обязательна) · "
            "↩️ вернуть · ❌ отклонить\n"
            "• 📋 Архив отчётов · 📅 Период и закрытие месяца · 📥 Экспорт\n"
            "• 👥 Сотрудники · 🧩 Конструктор ролей и шаблонов\n\n"
            "⚠️ Цену можно <b>только снижать</b> (R2). Свой отчёт "
            "подтверждается автоматически (R1a).\n\n"
            "Excel приходит документом в бот."
        ),
    },
    "help_accountant": {
        "uz": (
            "<b>Buxgalter imkoniyatlari</b> — hammasi <b>Mini App</b> ichida\n\n"
            "• 📋 Hisobotlar arxivi\n"
            "• 📅 Davr: yopishdan oldingi tekshiruv, oyni yopish\n"
            "• 💰 To'lov varaqalari (faqat tasdiqlangan summa bo'yicha)\n"
            "• 📥 Excel eksport — botga hujjat bo'lib keladi"
        ),
        "ru": (
            "<b>Возможности бухгалтера</b> — всё внутри <b>Mini App</b>\n\n"
            "• 📋 Архив отчётов\n"
            "• 📅 Период: проверка перед закрытием, закрытие месяца\n"
            "• 💰 Ведомости (только по подтверждённым суммам)\n"
            "• 📥 Экспорт в Excel — придёт документом в бот"
        ),
    },
    # --- Hisobot yaratish ---
    "no_templates": {
        "uz": "Sizning rolingizga hech qanday shablon biriktirilmagan. Adminga murojaat qiling.",
        "ru": "К вашей роли не привязан ни один шаблон. Обратитесь к администратору.",
    },
    "choose_template": {"uz": "Qaysi hisobot?", "ru": "Какой отчёт?"},
    "arrived_registered": {
        "uz": (
            "🚗 <b>Mashina keldi</b> — {time}\n"
            "Hisobot: <code>{number}</code>\n\n"
            "Endi bir necha savolga javob bering."
        ),
        "ru": (
            "🚗 <b>Машина приехала</b> — {time}\n"
            "Отчёт: <code>{number}</code>\n\n"
            "Теперь ответьте на несколько вопросов."
        ),
    },
    "draft_exists": {
        "uz": "Sizda tugallanmagan hisobot bor: <code>{number}</code>. Davom etamizmi?",
        "ru": "У вас есть незавершённый отчёт: <code>{number}</code>. Продолжим?",
    },
    "draft_continue": {"uz": "▶️ Davom ettirish", "ru": "▶️ Продолжить"},
    "draft_new": {"uz": "➕ Yangi hisobot", "ru": "➕ Новый отчёт"},
    "draft_delete": {"uz": "🗑 Qoralamani o'chirish", "ru": "🗑 Удалить черновик"},
    "draft_deleted": {"uz": "🗑 Qoralama o'chirildi.", "ru": "🗑 Черновик удалён."},
    "no_drafts": {"uz": "Qoralamalar yo'q.", "ru": "Черновиков нет."},
    "drafts_title": {"uz": "📝 <b>Qoralamalar</b>", "ru": "📝 <b>Черновики</b>"},
    # --- Maydonlar ---
    "field_required": {"uz": "Bu maydon majburiy.", "ru": "Это поле обязательно."},
    "ask_plate": {
        "uz": "🚘 <b>Mashina raqamini</b> yozing (masalan <code>01A123BC</code>):",
        "ru": "🚘 Введите <b>гос. номер</b> (например <code>01A123BC</code>):",
    },
    "vehicle_not_found": {
        "uz": (
            "❌ <code>{plate}</code> reyestrda topilmadi.\n"
            "Raqamni tekshiring yoki adminga murojaat qiling."
        ),
        "ru": (
            "❌ <code>{plate}</code> не найден в реестре.\n"
            "Проверьте номер или обратитесь к администратору."
        ),
    },
    "vehicle_found": {
        "uz": "✅ <b>{title}</b>{extra}",
        "ru": "✅ <b>{title}</b>{extra}",
    },
    "vehicle_ctx_last_repair": {
        "uz": "\n🕓 Oxirgi ta'mir: {days} kun oldin",
        "ru": "\n🕓 Последний ремонт: {days} дн. назад",
    },
    "vehicle_ctx_month_count": {
        "uz": "\n⚠️ Bu oyda {n}-marta ta'mirda",
        "ru": "\n⚠️ {n}-й ремонт в этом месяце",
    },
    "vehicle_ctx_driver": {"uz": "\n👤 Haydovchi: {name}", "ru": "\n👤 Водитель: {name}"},
    "ask_photo": {
        "uz": (
            "📷 <b>{label}</b>\n{hint}"
            "\n\nFotoni <b>shu yerda kamerada olib</b> yuboring. "
            "Kerakli soni: {min}–{max}. Yuklanganda “{done}” tugmasini bosing."
        ),
        "ru": (
            "📷 <b>{label}</b>\n{hint}"
            "\n\nСнимите фото <b>камерой прямо сейчас</b> и отправьте. "
            "Нужно: {min}–{max}. Когда закончите — нажмите «{done}»."
        ),
    },
    "photo_saved": {
        "uz": "📷 Saqlandi ({n}/{max}).",
        "ru": "📷 Сохранено ({n}/{max}).",
    },
    "photo_need_more": {
        "uz": "Kamida {min} ta foto kerak (hozir {n} ta).",
        "ru": "Нужно минимум {min} фото (сейчас {n}).",
    },
    "photo_max_reached": {
        "uz": "Maksimal {max} ta foto. “{done}” tugmasini bosing.",
        "ru": "Максимум {max} фото. Нажмите «{done}».",
    },
    "photo_expected": {
        "uz": "Foto kutilmoqda. Rasm yuboring yoki “{done}” tugmasini bosing.",
        "ru": "Ожидается фото. Отправьте снимок или нажмите «{done}».",
    },
    "ask_number": {"uz": "🔢 <b>{label}</b>\n{hint}", "ru": "🔢 <b>{label}</b>\n{hint}"},
    "ask_text": {"uz": "✍️ <b>{label}</b>\n{hint}", "ru": "✍️ <b>{label}</b>\n{hint}"},
    "ask_money": {"uz": "💰 <b>{label}</b>\n{hint}", "ru": "💰 <b>{label}</b>\n{hint}"},
    "ask_select": {"uz": "📋 <b>{label}</b>\n{hint}", "ru": "📋 <b>{label}</b>\n{hint}"},
    "linkable_empty": {
        "uz": "🔗 <b>{label}</b>\nBu mashina bo'yicha bog'lanadigan hisobot topilmadi.",
        "ru": "🔗 <b>{label}</b>\nПо этой машине связанных отчётов не найдено.",
    },
    "ask_bool": {"uz": "❔ <b>{label}</b>\n{hint}", "ru": "❔ <b>{label}</b>\n{hint}"},
    "invalid_number": {"uz": "Faqat son kiriting.", "ru": "Введите только число."},
    "invalid_money": {
        "uz": "Summani son bilan kiriting, masalan <code>250000</code>.",
        "ru": "Введите сумму числом, например <code>250000</code>.",
    },
    "value_too_small": {"uz": "Qiymat {min} dan kichik bo'lmasin.", "ru": "Значение не меньше {min}."},
    "value_too_big": {"uz": "Qiymat {max} dan katta bo'lmasin.", "ru": "Значение не больше {max}."},
    "text_too_short": {
        "uz": "Kamida {min} ta belgi yozing (hozir {n}).",
        "ru": "Напишите минимум {min} символов (сейчас {n}).",
    },
    "odometer_decreased": {
        "uz": "⚠️ Probeg oldingi qiymatdan kichik ({prev} km). Tekshirib qayta kiriting.",
        "ru": "⚠️ Пробег меньше предыдущего ({prev} км). Проверьте и введите заново.",
    },
    # --- Qatorlar (lines) ---
    "lines_labor_title": {
        "uz": "🔧 <b>Bajarilgan ishlar</b>\n\nHar bir ish uchun <b>o'z narxingizni</b> kiritasiz.",
        "ru": "🔧 <b>Выполненные работы</b>\n\nПо каждой работе укажите <b>свою цену</b>.",
    },
    "lines_part_title": {
        "uz": (
            "📦 <b>Ishlatilgan qismlar</b> (ixtiyoriy)\n\n"
            "ⓘ Qism narxini siz kiritmaysiz — uni ta'minotchi/admin kiritadi."
        ),
        "ru": (
            "📦 <b>Использованные запчасти</b> (необязательно)\n\n"
            "ⓘ Цену запчасти вы не вводите — её вносит снабженец/админ."
        ),
    },
    "lines_current": {"uz": "\n\n<b>Qo'shilgan:</b>\n{list}", "ru": "\n\n<b>Добавлено:</b>\n{list}"},
    "lines_empty": {"uz": "\n\n<i>Hali qo'shilmagan.</i>", "ru": "\n\n<i>Пока пусто.</i>"},
    "line_add": {"uz": "➕ Qo'shish", "ru": "➕ Добавить"},
    "line_del": {"uz": "🗑 O'chirish", "ru": "🗑 Удалить"},
    "line_ask_name": {
        "uz": "Ish nomini yozing yoki ro'yxatdan tanlang (qidirish uchun matn yozing):",
        "ru": "Введите название работы или выберите из списка (введите текст для поиска):",
    },
    "line_ask_name_part": {
        "uz": "Qism nomini yozing yoki ro'yxatdan tanlang:",
        "ru": "Введите название запчасти или выберите из списка:",
    },
    "line_ask_qty": {
        "uz": "Nechta / qancha? (son, masalan <code>1</code>)",
        "ru": "Сколько? (число, например <code>1</code>)",
    },
    "line_ask_price": {
        "uz": (
            "💰 <b>{name}</b>\nO'z narxingizni yozing (so'm), masalan <code>250000</code>:"
            "{own_history}"
        ),
        "ru": (
            "💰 <b>{name}</b>\nУкажите свою цену (сум), например <code>250000</code>:"
            "{own_history}"
        ),
    },
    "own_price_history": {
        "uz": "\n\nⓘ Siz bu ishga oxirgi marta {amount} so'ragan edingiz.",
        "ru": "\n\nⓘ В прошлый раз вы просили за эту работу {amount}.",
    },
    "line_added": {"uz": "✅ Qo'shildi: {name} — {amount}", "ru": "✅ Добавлено: {name} — {amount}"},
    "line_added_part": {"uz": "✅ Qo'shildi: {name} ×{qty}", "ru": "✅ Добавлено: {name} ×{qty}"},
    "line_removed": {"uz": "🗑 O'chirildi.", "ru": "🗑 Удалено."},
    "lines_need_one": {
        "uz": "Kamida bitta ish qo'shing.",
        "ru": "Добавьте хотя бы одну работу.",
    },
    "line_use_custom": {
        "uz": "✍️ O'z nomim: {name}",
        "ru": "✍️ Своё название: {name}",
    },
    "catalog_search_hint": {
        "uz": "Ro'yxatdan tanlang yoki o'z nomingizni yozing:",
        "ru": "Выберите из списка или напишите своё название:",
    },
    # --- Mashina ketdi / yuborish ---
    "form_complete": {
        "uz": (
            "✅ Forma to'ldirildi.\n\n"
            "Ish tugagach <b>🚙 Mashina ketdi</b> tugmasini bosing — "
            "shu lahza qayd etiladi."
        ),
        "ru": (
            "✅ Форма заполнена.\n\n"
            "Когда работа окончена — нажмите <b>🚙 Машина уехала</b>, "
            "этот момент будет зафиксирован."
        ),
    },
    "btn_car_left": {"uz": "🚙 Mashina ketdi", "ru": "🚙 Машина уехала"},
    "btn_submit": {"uz": "📤 Yuborish", "ru": "📤 Отправить"},
    "btn_preview": {"uz": "👁 Ko'rish", "ru": "👁 Посмотреть"},
    "left_registered": {
        "uz": "🚙 <b>Mashina ketdi</b> — {time}\nUstaxonada bo'lgan vaqt: <b>{downtime}</b>",
        "ru": "🚙 <b>Машина уехала</b> — {time}\nВремя в сервисе: <b>{downtime}</b>",
    },
    "need_left_first": {
        "uz": "Avval <b>🚙 Mashina ketdi</b> tugmasini bosing.",
        "ru": "Сначала нажмите <b>🚙 Машина уехала</b>.",
    },
    "submit_blocked": {
        "uz": "❌ Yuborib bo'lmadi:\n{errors}",
        "ru": "❌ Не удалось отправить:\n{errors}",
    },
    "submitted_ok": {
        "uz": (
            "📤 <b>Yuborildi!</b>\n\n"
            "Hisobot: <code>{number}</code>\n"
            "So'ralgan ish haqi: <b>{amount}</b>\n\n"
            "Admin ko'rib chiqadi. Natijani shu yerda xabar qilamiz."
        ),
        "ru": (
            "📤 <b>Отправлено!</b>\n\n"
            "Отчёт: <code>{number}</code>\n"
            "Запрошенная оплата: <b>{amount}</b>\n\n"
            "Администратор рассмотрит. Результат придёт сюда."
        ),
    },
    "submitted_auto_approved": {
        "uz": (
            "✅ <b>Avtomatik tasdiqlandi</b>\n\n"
            "Hisobot: <code>{number}</code>\nSumma: <b>{amount}</b>\n\n"
            "ⓘ Admin hisoboti tasdiqlovchisiz avtomatik tasdiqlanadi (R1a) va "
            "oylik hisobotda alohida ko'rsatiladi."
        ),
        "ru": (
            "✅ <b>Подтверждено автоматически</b>\n\n"
            "Отчёт: <code>{number}</code>\nСумма: <b>{amount}</b>\n\n"
            "ⓘ Отчёт администратора подтверждается автоматически (R1a) и "
            "показывается отдельной строкой в месячном отчёте."
        ),
    },
    # --- Hisobot kartochkasi ---
    "card_header": {
        "uz": "<b>{number}</b> · {status}\n👤 {author}",
        "ru": "<b>{number}</b> · {status}\n👤 {author}",
    },
    "card_vehicle": {"uz": "🚘 {title}", "ru": "🚘 {title}"},
    "card_times": {
        "uz": "🕓 Keldi: {arrived} · Ketdi: {left} ({downtime})",
        "ru": "🕓 Приехала: {arrived} · Уехала: {left} ({downtime})",
    },
    "card_odometer": {"uz": "📊 Probeg: {km} km", "ru": "📊 Пробег: {km} км"},
    "card_labor": {"uz": "\n💰 <b>Ish haqi</b>", "ru": "\n💰 <b>Оплата работы</b>"},
    "card_parts": {"uz": "\n📦 <b>Qismlar</b>", "ru": "\n📦 <b>Запчасти</b>"},
    "card_comment": {"uz": "\n💬 {text}", "ru": "\n💬 {text}"},
    "card_total_proposed": {"uz": "So'raldi: <b>{amount}</b>", "ru": "Запрошено: <b>{amount}</b>"},
    "card_total_approved": {
        "uz": "Tasdiqlandi: <b>{amount}</b>",
        "ru": "Подтверждено: <b>{amount}</b>",
    },
    "card_auto_approved": {
        "uz": "⚙️ <i>Avtomatik tasdiqlangan (admin hisoboti)</i>",
        "ru": "⚙️ <i>Подтверждено автоматически (отчёт админа)</i>",
    },
    "card_no_photos": {"uz": "📷 Foto yo'q", "ru": "📷 Фото нет"},
    # --- Statuslar ---
    "st_draft": {"uz": "📝 Qoralama", "ru": "📝 Черновик"},
    "st_submitted": {"uz": "⏳ Tasdiq kutmoqda", "ru": "⏳ Ждёт подтверждения"},
    "st_in_review": {"uz": "👀 Ko'rilmoqda", "ru": "👀 На рассмотрении"},
    "st_price_negotiation": {"uz": "💬 Narx kelishuvida", "ru": "💬 Согласование цены"},
    "st_price_disputed": {"uz": "⚖️ Nizoda", "ru": "⚖️ Спор"},
    "st_reopened": {"uz": "↩️ Qaytarilgan", "ru": "↩️ Возвращён"},
    "st_approved": {"uz": "✅ Tasdiqlangan", "ru": "✅ Подтверждён"},
    "st_rejected": {"uz": "❌ Rad etilgan", "ru": "❌ Отклонён"},
    "st_paid": {"uz": "💵 To'langan", "ru": "💵 Выплачен"},
    # --- Admin: ko'rib chiqish ---
    "pending_empty": {
        "uz": "✅ Tasdiq kutayotgan hisobot yo'q.",
        "ru": "✅ Нет отчётов, ожидающих подтверждения.",
    },
    "pending_title": {
        "uz": "⏳ <b>Tasdiq kutmoqda: {n} ta</b>",
        "ru": "⏳ <b>Ждут подтверждения: {n}</b>",
    },
    "btn_approve": {"uz": "✅ Tasdiqlash", "ru": "✅ Подтвердить"},
    "btn_reduce": {"uz": "✏️ Narxni kamaytirish", "ru": "✏️ Снизить цену"},
    "btn_reopen": {"uz": "↩️ Qaytarish", "ru": "↩️ Вернуть"},
    "btn_reject": {"uz": "❌ Rad etish", "ru": "❌ Отклонить"},
    "btn_photos": {"uz": "📷 Fotolar", "ru": "📷 Фото"},
    "btn_history": {"uz": "🧾 Kelishuv tarixi", "ru": "🧾 История согласования"},
    "price_context": {
        "uz": (
            "\n📊 <i>Tarix (oxirgi {n} marta): o'rtacha {avg}"
            " · eng past {min} · eng yuqori {max}</i>"
        ),
        "ru": (
            "\n📊 <i>История (последние {n}): среднее {avg}"
            " · мин {min} · макс {max}</i>"
        ),
    },
    "price_context_author": {
        "uz": "\n👤 <i>{name}: o'rtacha {avg} · narxi {pct}% hollarda kamaytirilgan</i>",
        "ru": "\n👤 <i>{name}: среднее {avg} · цену снижали в {pct}% случаев</i>",
    },
    "price_context_none": {
        "uz": "\n📊 <i>Bu ish bo'yicha tarix yo'q — birinchi marta.</i>",
        "ru": "\n📊 <i>По этой работе истории нет — впервые.</i>",
    },
    "choose_line_to_reduce": {
        "uz": "Qaysi ish narxini kamaytirasiz?",
        "ru": "По какой работе снизить цену?",
    },
    "ask_new_amount": {
        "uz": (
            "✏️ <b>{name}</b>\nUsta so'radi: <b>{proposed}</b>\n\n"
            "Yangi summani yozing (faqat kamaytirish mumkin):"
        ),
        "ru": (
            "✏️ <b>{name}</b>\nМастер просит: <b>{proposed}</b>\n\n"
            "Введите новую сумму (можно только снизить):"
        ),
    },
    "quick_amounts": {"uz": "Tez tanlov:", "ru": "Быстрый выбор:"},
    "price_increase_forbidden": {
        "uz": (
            "❌ Narxni <b>oshirib bo'lmaydi</b> (R2). So'ralgan: {proposed}.\n"
            "Usta kam so'ragan bo'lsa — hisobotni ↩️ qaytaring."
        ),
        "ru": (
            "❌ Цену <b>повышать нельзя</b> (R2). Запрошено: {proposed}.\n"
            "Если мастер попросил мало — ↩️ верните отчёт."
        ),
    },
    "ask_reason": {
        "uz": "Sabab majburiy. Nima uchun kamaytiryapsiz?",
        "ru": "Причина обязательна. Почему снижаете?",
    },
    "ask_reject_reason": {"uz": "Rad etish sababi:", "ru": "Причина отклонения:"},
    "ask_reopen_reason": {"uz": "Qaytarish sababi:", "ru": "Причина возврата:"},
    "reason_too_short": {
        "uz": "Sababni batafsilroq yozing (kamida 5 ta belgi).",
        "ru": "Опишите причину подробнее (минимум 5 символов)."
    },
    "price_proposed_admin": {
        "uz": "📨 Taklif yuborildi. Ustaga xabar berildi.",
        "ru": "📨 Предложение отправлено. Мастер уведомлён.",
    },
    "approved_admin": {
        "uz": "✅ <code>{number}</code> tasdiqlandi: <b>{amount}</b>",
        "ru": "✅ <code>{number}</code> подтверждён: <b>{amount}</b>",
    },
    "rejected_admin": {"uz": "❌ <code>{number}</code> rad etildi.", "ru": "❌ <code>{number}</code> отклонён."},
    "reopened_admin": {
        "uz": "↩️ <code>{number}</code> ustaga qaytarildi.",
        "ru": "↩️ <code>{number}</code> возвращён мастеру.",
    },
    "self_approval_forbidden": {
        "uz": "❌ O'z hisobotingizni qo'lda tasdiqlay olmaysiz (R1).",
        "ru": "❌ Нельзя вручную подтверждать собственный отчёт (R1).",
    },
    # --- Narx kelishuvi (usta tomoni) ---
    "negotiation_empty": {
        "uz": "✅ Javob kutayotgan narx taklifi yo'q.",
        "ru": "✅ Нет предложений, ожидающих ответа.",
    },
    "negotiation_card": {
        "uz": (
            "💬 <b>Narx bo'yicha taklif</b>\n"
            "<code>{number}</code> · {vehicle}\n\n{lines}\n"
            "💬 Admin izohi: <i>{reason}</i>\n\n"
            "⏱ {hours} soat javob bermasangiz — avtomatik rozilik hisoblanadi."
        ),
        "ru": (
            "💬 <b>Предложение по цене</b>\n"
            "<code>{number}</code> · {vehicle}\n\n{lines}\n"
            "💬 Комментарий админа: <i>{reason}</i>\n\n"
            "⏱ Без ответа {hours} ч — согласие засчитается автоматически."
        ),
    },
    "negotiation_line": {
        "uz": "🔧 {name}\n   Siz so'radingiz: <b>{proposed}</b>\n   Admin taklifi: <b>{approved}</b>",
        "ru": "🔧 {name}\n   Вы просили: <b>{proposed}</b>\n   Предложение админа: <b>{approved}</b>",
    },
    "btn_accept_price": {"uz": "✅ Roziman", "ru": "✅ Согласен"},
    "btn_dispute_price": {"uz": "❌ Rozi emasman", "ru": "❌ Не согласен"},
    "price_accepted": {
        "uz": "✅ Rozilik qabul qilindi. <code>{number}</code> tasdiqlandi: <b>{amount}</b>",
        "ru": "✅ Согласие принято. <code>{number}</code> подтверждён: <b>{amount}</b>",
    },
    "ask_dispute_comment": {
        "uz": "Nima uchun rozi emassiz? Izoh yozing — admin qayta ko'rib chiqadi.",
        "ru": "Почему не согласны? Напишите комментарий — админ пересмотрит.",
    },
    "price_disputed_ok": {
        "uz": "📨 Izohingiz adminga yuborildi. U qayta ko'rib chiqadi.",
        "ru": "📨 Ваш комментарий отправлен админу. Он пересмотрит.",
    },
    "btn_final_decision": {"uz": "⚖️ Yakuniy qaror", "ru": "⚖️ Окончательное решение"},
    "ask_final_comment": {
        "uz": "Yakuniy qaror izohi (majburiy):",
        "ru": "Комментарий к окончательному решению (обязательно):",
    },
    # --- Bildirishnomalar ---
    "notify_new_submission": {
        "uz": (
            "📥 <b>Yangi hisobot</b>\n"
            "<code>{number}</code> · {vehicle}\n"
            "👤 {author}\n💰 So'raldi: <b>{amount}</b>{context}"
        ),
        "ru": (
            "📥 <b>Новый отчёт</b>\n"
            "<code>{number}</code> · {vehicle}\n"
            "👤 {author}\n💰 Запрошено: <b>{amount}</b>{context}"
        ),
    },
    "notify_price_proposed": {
        "uz": (
            "💬 <b>Admin narxni kamaytirdi</b>\n"
            "<code>{number}</code> · {vehicle}\n\n"
            "Siz so'radingiz: <b>{proposed}</b>\n"
            "Admin taklifi: <b>{approved}</b>\n\n"
            "💬 <i>{reason}</i>\n\n"
            "⏱ {hours} soat ichida javob bering."
        ),
        "ru": (
            "💬 <b>Админ снизил цену</b>\n"
            "<code>{number}</code> · {vehicle}\n\n"
            "Вы просили: <b>{proposed}</b>\n"
            "Предложение админа: <b>{approved}</b>\n\n"
            "💬 <i>{reason}</i>\n\n"
            "⏱ Ответьте в течение {hours} ч."
        ),
    },
    "notify_price_reminder": {
        "uz": (
            "⏰ <b>Eslatma:</b> <code>{number}</code> bo'yicha narx taklifiga javob "
            "bermadingiz. {hours} soatdan keyin avtomatik rozilik hisoblanadi."
        ),
        "ru": (
            "⏰ <b>Напоминание:</b> вы не ответили на предложение по цене "
            "<code>{number}</code>. Через {hours} ч согласие засчитается автоматически."
        ),
    },
    "notify_price_disputed": {
        "uz": (
            "⚖️ <b>Usta narxga rozi bo'lmadi</b>\n"
            "<code>{number}</code> · 👤 {author}\n\n💬 <i>{comment}</i>"
        ),
        "ru": (
            "⚖️ <b>Мастер не согласен с ценой</b>\n"
            "<code>{number}</code> · 👤 {author}\n\n💬 <i>{comment}</i>"
        ),
    },
    "notify_approved": {
        "uz": "✅ <b>Hisobotingiz tasdiqlandi</b>\n<code>{number}</code> · <b>{amount}</b>",
        "ru": "✅ <b>Ваш отчёт подтверждён</b>\n<code>{number}</code> · <b>{amount}</b>",
    },
    "notify_auto_accepted": {
        "uz": (
            "⏱ <code>{number}</code> — 48 soat javob bo'lmagani uchun narx "
            "avtomatik qabul qilindi: <b>{amount}</b>"
        ),
        "ru": (
            "⏱ <code>{number}</code> — цена принята автоматически, так как "
            "не было ответа 48 ч: <b>{amount}</b>"
        ),
    },
    "notify_rejected": {
        "uz": "❌ <b>Hisobot rad etildi</b>\n<code>{number}</code>\n\n💬 <i>{comment}</i>",
        "ru": "❌ <b>Отчёт отклонён</b>\n<code>{number}</code>\n\n💬 <i>{comment}</i>",
    },
    "notify_reopened": {
        "uz": (
            "↩️ <b>Hisobot qaytarildi — tuzatish kerak</b>\n"
            "<code>{number}</code>\n\n💬 <i>{comment}</i>"
        ),
        "ru": (
            "↩️ <b>Отчёт возвращён — нужно исправить</b>\n"
            "<code>{number}</code>\n\n💬 <i>{comment}</i>"
        ),
    },
    "btn_fix": {"uz": "✏️ Tuzatish", "ru": "✏️ Исправить"},
    "notify_draft_stale": {
        "uz": "📝 <code>{number}</code> qoralamasi {hours} soatdan beri tugallanmagan.",
        "ru": "📝 Черновик <code>{number}</code> не завершён уже {hours} ч.",
    },
    "notify_long_service": {
        "uz": "🔧 <b>{vehicle}</b> {hours} soatdan beri ustaxonada (<code>{number}</code>).",
        "ru": "🔧 <b>{vehicle}</b> в сервисе уже {hours} ч (<code>{number}</code>).",
    },
    "notify_period_closing": {
        "uz": "📅 <b>{period}</b> davri {days} kundan keyin yopiladi. Tekshiring: /davr",
        "ru": "📅 Период <b>{period}</b> закрывается через {days} дн. Проверьте: /davr",
    },
    "notify_fleet_sync": {
        "uz": "{summary}",
        "ru": "{summary}",
    },
    # --- Statistika ---
    "my_month": {
        "uz": (
            "💰 <b>{period}</b>\n\n"
            "Yuborilgan hisobotlar: <b>{count}</b>\n"
            "So'radim: <b>{proposed}</b>\n"
            "Tasdiqlandi: <b>{approved}</b>\n"
            "Kamaytirildi: <b>{reduction}</b> ({pct}%)\n\n"
            "⏳ Tasdiq kutmoqda: {pending}\n💬 Kelishuvda: {negotiating}"
        ),
        "ru": (
            "💰 <b>{period}</b>\n\n"
            "Отправлено отчётов: <b>{count}</b>\n"
            "Запросил: <b>{proposed}</b>\n"
            "Подтверждено: <b>{approved}</b>\n"
            "Снижено: <b>{reduction}</b> ({pct}%)\n\n"
            "⏳ Ждут подтверждения: {pending}\n💬 В согласовании: {negotiating}"
        ),
    },
    "my_reports_title": {"uz": "📋 <b>Hisobotlarim</b>", "ru": "📋 <b>Мои отчёты</b>"},
    "my_reports_empty": {"uz": "Hozircha hisobot yo'q.", "ru": "Отчётов пока нет."},
    "daily_report": {
        "uz": (
            "📊 <b>Bugun — {date}</b>\n\n"
            "📥 Yuborilgan: <b>{submitted}</b>\n"
            "✅ Tasdiqlangan: <b>{approved}</b> ({approved_sum})\n"
            "💬 Kelishuvda: <b>{negotiating}</b>\n"
            "🔧 Hozir ustaxonada: <b>{in_service}</b> mashina\n\n"
            "<b>{period}</b> oyi bo'yicha:\n"
            "So'raldi: {m_proposed}\nTasdiqlandi: {m_approved}\n"
            "💰 Kelishuv tejamkorligi: <b>{m_saved}</b> ({m_pct}%)"
        ),
        "ru": (
            "📊 <b>Сегодня — {date}</b>\n\n"
            "📥 Отправлено: <b>{submitted}</b>\n"
            "✅ Подтверждено: <b>{approved}</b> ({approved_sum})\n"
            "💬 В согласовании: <b>{negotiating}</b>\n"
            "🔧 Сейчас в сервисе: <b>{in_service}</b> авто\n\n"
            "За <b>{period}</b>:\n"
            "Запрошено: {m_proposed}\nПодтверждено: {m_approved}\n"
            "💰 Экономия согласования: <b>{m_saved}</b> ({m_pct}%)"
        ),
    },
    # --- Davr ---
    "period_card": {
        "uz": (
            "📅 <b>Davr: {period}</b> — {status}\n\n"
            "Hisobotlar: {total}\nTasdiqlangan: {approved}\n"
            "So'raldi: {proposed}\nTasdiqlangan summa: {approved_sum}\n"
            "💰 Tejaldi: <b>{saved}</b>"
        ),
        "ru": (
            "📅 <b>Период: {period}</b> — {status}\n\n"
            "Отчётов: {total}\nПодтверждено: {approved}\n"
            "Запрошено: {proposed}\nПодтверждённая сумма: {approved_sum}\n"
            "💰 Сэкономлено: <b>{saved}</b>"
        ),
    },
    "period_status_open": {"uz": "🟢 ochiq", "ru": "🟢 открыт"},
    "period_status_locking": {"uz": "🟡 yopilmoqda", "ru": "🟡 закрывается"},
    "period_status_closed": {"uz": "🔒 yopilgan", "ru": "🔒 закрыт"},
    "btn_precheck": {"uz": "🔍 Tekshirish", "ru": "🔍 Проверить"},
    "btn_close_period": {"uz": "🔒 Oyni yopish", "ru": "🔒 Закрыть месяц"},
    "precheck_clean": {
        "uz": "✅ To'sqinlik yo'q — oyni yopish mumkin.",
        "ru": "✅ Блокировок нет — месяц можно закрыть.",
    },
    "precheck_blockers": {
        "uz": "❌ <b>To'sqinlik qiluvchi:</b>\n{items}",
        "ru": "❌ <b>Блокирующие:</b>\n{items}",
    },
    "precheck_warnings": {
        "uz": "\n⚠️ <b>Ogohlantirish:</b>\n{items}",
        "ru": "\n⚠️ <b>Предупреждения:</b>\n{items}",
    },
    "precheck_unapproved": {
        "uz": "• {n} ta hisobot tasdiqlanmagan",
        "ru": "• {n} отчётов не подтверждено",
    },
    "precheck_negotiation": {
        "uz": "• {n} ta hisobot narx kelishuvida",
        "ru": "• {n} отчётов в согласовании цены",
    },
    "precheck_reopened": {
        "uz": "• {n} ta hisobot qaytarilgan (tuzatilmagan)",
        "ru": "• {n} отчётов возвращено (не исправлены)",
    },
    "precheck_drafts": {
        "uz": "• {n} ta qoralama {days} kundan beri turibdi",
        "ru": "• {n} черновиков висят более {days} дн.",
    },
    "period_closed_ok": {
        "uz": "🔒 <b>{period}</b> yopildi. To'lov varaqalari tayyor: {n} ta xodim.",
        "ru": "🔒 <b>{period}</b> закрыт. Ведомости готовы: {n} сотрудников.",
    },
    "period_close_blocked": {
        "uz": "❌ Yopib bo'lmaydi — avval to'sqinliklarni hal qiling.",
        "ru": "❌ Закрыть нельзя — сначала устраните блокировки.",
    },
    "payout_line": {
        "uz": "👤 {name}: {count} ta · {total}",
        "ru": "👤 {name}: {count} шт · {total}",
    },
    # --- Eksport ---
    "export_choose": {"uz": "Qaysi hisobotni yuklaymiz?", "ru": "Какой отчёт выгрузить?"},
    "export_submissions": {"uz": "📄 Ta'mirlar", "ru": "📄 Ремонты"},
    "export_payouts": {"uz": "💵 To'lov varaqalari", "ru": "💵 Ведомости"},
    "export_savings": {"uz": "💰 Kelishuv tejamkorligi", "ru": "💰 Экономия согласования"},
    "export_building": {"uz": "⏳ Fayl tayyorlanmoqda…", "ru": "⏳ Файл готовится…"},
    "export_empty": {"uz": "Bu davr uchun ma'lumot yo'q.", "ru": "Нет данных за этот период."},
    # --- Ruxsat ---
    "forbidden": {"uz": "⛔️ Bu amal sizga ruxsat etilmagan.", "ru": "⛔️ Действие вам не разрешено."},
    "not_found": {"uz": "Topilmadi.", "ru": "Не найдено."},
    "period_closed_err": {
        "uz": "🔒 Davr yopilgan — o'zgartirib bo'lmaydi (R4).",
        "ru": "🔒 Период закрыт — изменения невозможны (R4).",
    },
    "invalid_state": {
        "uz": "Bu holatda bu amal mumkin emas.",
        "ru": "В этом состоянии действие невозможно.",
    },
}


class _Missing(dict):
    """Yetishmagan kalit butun xabarni buzmasin — faqat o'sha joyda «—».

    Ilgari `text.format(**kwargs)` `KeyError` da **xom shablonni** qaytarardi:
    bitta yetishmagan kalit tufayli foydalanuvchi `{number} · {vehicle}` degan
    xabarni ko'rardi (2026-08-01 da ustaga aynan shunday ketgan).
    """

    def __missing__(self, key: str) -> str:
        _log.warning("i18n_missing_param", param=key)
        return "—"


def t(key: str, lang: str = DEFAULT_LANG, /, **kwargs: object) -> str:
    """Tarjima. Kalit topilmasa — kalitning o'zi (dev'da darhol ko'rinadi)."""
    entry = T.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            return text.format_map(_Missing(kwargs))
        except (IndexError, ValueError):  # nosoz shablon — xom qaytaramiz
            _log.warning("i18n_bad_template", key=key)
            return text
    return text


def fmt_money(value: Decimal | float | int | None, lang: str = DEFAULT_LANG) -> str:
    """250000 → «250 000 so'm»."""
    if value is None:
        value = 0
    amount = Decimal(str(value)).quantize(Decimal("1"))
    grouped = f"{amount:,}".replace(",", " ")
    return f"{grouped} {t('currency', lang)}"


def fmt_dt(value: dt.datetime | None, lang: str = DEFAULT_LANG, with_year: bool = False) -> str:
    """UTC → Asia/Tashkent, «29.07 09:14»."""
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    local = value.astimezone(TASHKENT)
    return local.strftime("%d.%m.%Y %H:%M" if with_year else "%d.%m %H:%M")


def fmt_duration(seconds: int | None, lang: str = DEFAULT_LANG) -> str:
    """12600 → «3 s 30 daq»."""
    if seconds is None:
        return "—"
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    h = "s" if lang == "uz" else "ч"
    m = "daq" if lang == "uz" else "мин"
    if hours and minutes:
        return f"{hours} {h} {minutes} {m}"
    if hours:
        return f"{hours} {h}"
    return f"{minutes} {m}"


STATUS_KEYS = {
    "draft": "st_draft",
    "submitted": "st_submitted",
    "in_review": "st_in_review",
    "price_negotiation": "st_price_negotiation",
    "price_disputed": "st_price_disputed",
    "reopened": "st_reopened",
    "approved": "st_approved",
    "rejected": "st_rejected",
    "paid": "st_paid",
}


def status_label(status: object, lang: str = DEFAULT_LANG) -> str:
    value = getattr(status, "value", status)
    return t(STATUS_KEYS.get(str(value), str(value)), lang)
