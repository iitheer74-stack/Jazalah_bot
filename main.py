import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8868617949:AAFHkBSU-WD9ZXHzEFnj4lvtrOVGHeMpqRs"
GROUP_CHAT_ID = -1004382101606

STATS_FILE = "stats.json"

def load_data():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_hours": 0.0, "tasks": {}, "users": {}}

def save_data(data):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_info(user):
    name = user.first_name if user.first_name else "مستخدم"
    username = f"@{user.username}" if user.username else None
    return name, username

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "أهلاً بك في منصة جزالة لتبادل الوقت والمهارات! ⏳✨\n\n"
            "اكتب تفاصيل طلبك مباشرة في هذه المحادثة (مثال: أحتاج شرح اختبار تاء في الإحصاء).\n"
            "وسيقوم البوت بنشر بطاقتك تلقائياً في القناة مع الحفاظ التام على خصوصيتك."
        )

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    text = update.message.text
    name, username = get_user_info(user)

    data = load_data()
    task_id = str(len(data["tasks"]) + 1)

    keyboard = [
        [InlineKeyboardButton("🤝 أنا مستعد للمساعدة", callback_data=f"help_{task_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # نص القناة: اسم مجرد للحفاظ على الخصوصية التامة
    card_text = (
        f"📌 طلب تبادل مهارة جديد #{task_id}\n\n"
        f"👤 الطالب: {name}\n"
        f"📝 المطلوب: {text}\n"
        f"⏱ الوقت المقدر: نصف ساعة (30 دقيقة)\n"
        f"🔘 الحالة: 🟢 متاح للتقديم"
    )

    try:
        sent_msg = await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=card_text,
            reply_markup=reply_markup
        )

        data["tasks"][task_id] = {
            "requester_id": user.id,
            "requester_name": name,
            "requester_username": username,
            "details": text,
            "message_id": sent_msg.message_id,
            "status": "open",
            "volunteer_name": None,
            "volunteer_username": None
        }
        save_data(data)

        await update.message.reply_text("✅ تم نشر طلبك في القناة بنجاح! ستصلك رسالة خاصة هنا فور تطوع أحد الزملاء لمساعدتك.")
    except Exception as e:
        await update.message.reply_text("عذراً، حدث خطأ أثناء نشر الطلب. يرجى المحاولة لاحقاً.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    action, task_id = query.data.split("_")

    if task_id not in data["tasks"]:
        return

    task = data["tasks"][task_id]
    volunteer = query.from_user
    vol_name, vol_username = get_user_info(volunteer)

    if action == "help":
        if task["status"] != "open":
            await query.answer("هذا الطلب قيد التنفيذ أو مكتمل بالفعل!", show_alert=True)
            return

        task["status"] = "in_progress"
        task["volunteer_name"] = vol_name
        task["volunteer_username"] = vol_username
        save_data(data)

        # تحديث القناة
        keyboard = [
            [InlineKeyboardButton(f"⏳ قيد التنفيذ بواسطة {vol_name}", callback_data="none")]
        ]
        new_text = (
            f"📌 طلب تبادل مهارة #{task_id}\n\n"
            f"👤 الطالب: {task['requester_name']}\n"
            f"📝 المطلوب: {task['details']}\n"
            f"⏱ الوقت المقدر: نصف ساعة (30 دقيقة)\n"
            f"🔘 الحالة: ⏳ قيد التنفيذ بواسطة {vol_name}"
        )
        await query.edit_message_text(new_text, reply_markup=InlineKeyboardMarkup(keyboard))

        # إرسال بيانات المتطوع للطالب في الخاص
        vol_contact = vol_username if vol_username else f"الاسم: {vol_name} (يمكنك مراسلته مباشرة إذا بدأ هو بالحديث معك)"
        student_buttons = []
        if vol_username:
            student_buttons.append([InlineKeyboardButton(f"💬 مراسلة المتطوع ({vol_name})", url=f"https://t.me/{vol_username[1:]}")])
        student_buttons.append([InlineKeyboardButton("✅ تم استلام الخدمة واحتساب الوقت", callback_data=f"done_{task_id}")])

        try:
            await context.bot.send_message(
                chat_id=task["requester_id"],
                text=f"🎉 تقدم المتطوع **{vol_name}** لمساعدتك في طلبك #{task_id}!\n\nحساب المتطوع: {vol_contact}",
                reply_markup=InlineKeyboardMarkup(student_buttons)
            )
        except Exception:
            pass

        # إرسال بيانات الطالب للمتطوع في الخاص
        req_contact = task['requester_username'] if task['requester_username'] else f"الاسم: {task['requester_name']}"
        vol_buttons = []
        if task['requester_username']:
            vol_buttons.append([InlineKeyboardButton(f"💬 مراسلة صاحب الطلب ({task['requester_name']})", url=f"https://t.me/{task['requester_username'][1:]}")])

        try:
            await context.bot.send_message(
                chat_id=volunteer.id,
                text=f"✨ شكراً لمبادرتك بمساعدة زميلك في طلب #{task_id}!\n\nحساب الطالب: {req_contact}",
                reply_markup=InlineKeyboardMarkup(vol_buttons) if vol_buttons else None
            )
        except Exception:
            pass

    elif action == "done":
        if str(query.from_user.id) != str(task["requester_id"]):
            await query.answer("فقط صاحب الطلب يمكنه تأكيد الإنجاز!", show_alert=True)
            return

        task["status"] = "completed"
        data["total_hours"] = round(data.get("total_hours", 0.0) + 0.5, 1)
        v_name = task["volunteer_name"]
        data["users"][v_name] = round(data.get("users", {}).get(v_name, 0.0) + 0.5, 1)
        save_data(data)

        completed_text = (
            f"📌 طلب تبادل مهارة #{task_id}\n\n"
            f"👤 الطالب: {task['requester_name']}\n"
            f"📝 المطلوب: {task['details']}\n"
            f"🔘 الحالة: 🏁 مكتملة وموثقة بنجاح ✨\n"
            f"🌟 المتطوع: {v_name} (+0.5 ساعة)"
        )
        await context.bot.edit_message_text(
            chat_id=GROUP_CHAT_ID,
            message_id=task["message_id"],
            text=completed_text
        )
        await query.edit_message_text("✨ شكراً لك! تم توثيق النصف ساعة وإضافتها إلى رصيد المتطوع بنجاح.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    total = data.get("total_hours", 0.0)
    users = data.get("users", {})
    top_list = "\n".join([f"• {u}: {h} ساعة" for u, h in sorted(users.items(), key=lambda x: x[1], reverse=True)[:5]])
    
    report = (
        f"📊 إحصائيات مبادرة جزالة لبنك الوقت:\n\n"
        f"⏱ إجمالي الساعات المتبادلة: {total} ساعة\n\n"
        f"🏆 أبرز المساهمين بالعطاء:\n{top_list if top_list else 'لا توجد ساعات مسجلة بعد.'}"
    )
    await update.message.reply_text(report)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_private_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
