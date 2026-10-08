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
    return {"total_hours": 0, "tasks": {}, "users": {}}

def save_data(data):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "أهلاً بك في منصة جزالة لتبادل الوقت والمهارات! ⏳✨\n\n"
            "اكتب تفاصيل طلبك مباشرة في هذه المحادثة (مثال: أحتاج شرح اختبار تاء في الإحصاء لمدة ساعة).\n"
            "وسيقوم البوت بنشر بطاقتك تلقائياً في القناة المخصصة."
        )

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    text = update.message.text
    username = f"@{user.username}" if user.username else user.first_name

    data = load_data()
    task_id = str(len(data["tasks"]) + 1)

    keyboard = [
        [InlineKeyboardButton("🤝 أنا مستعد للمساعدة", callback_data=f"help_{task_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    card_text = (
        f"📌 **طلب تبادل مهارة جديد** #{task_id}\n\n"
        f"👤 **الطالب:** {username}\n"
        f"📝 **المطلوب:** {text}\n"
        f"⏱ **الوقت المقدر:** 1 ساعة\n"
        f"🔘 **الحالة:** 🟢 متاح للتقديم"
    )

    sent_msg = await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=card_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    data["tasks"][task_id] = {
        "requester_id": user.id,
        "requester_name": username,
        "details": text,
        "message_id": sent_msg.message_id,
        "status": "open",
        "volunteer_name": None
    }
    save_data(data)

    await update.message.reply_text("✅ تم نشر طلبك في القناة بنجاح! ستصلك رسالة هنا بمجرد تقدم متطوع لمساعدتك.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    action, task_id = query.data.split("_")

    if task_id not in data["tasks"]:
        return

    task = data["tasks"][task_id]
    volunteer = query.from_user
    vol_username = f"@{volunteer.username}" if volunteer.username else volunteer.first_name

    if action == "help":
        if task["status"] != "open":
            await query.answer("هذا الطلب قيد التنفيذ أو مكتمل بالفعل!", show_alert=True)
            return

        task["status"] = "in_progress"
        task["volunteer_name"] = vol_username
        save_data(data)

        keyboard = [
            [InlineKeyboardButton(f"⏳ قيد التنفيذ بواسطة {vol_username}", callback_data="none")]
        ]
        new_text = (
            f"📌 **طلب تبادل مهارة** #{task_id}\n\n"
            f"👤 **الطالب:** {task['requester_name']}\n"
            f"📝 **المطلوب:** {task['details']}\n"
            f"🔘 **الحالة:** ⏳ قيد التنفيذ بواسطة {vol_username}"
        )
        await query.edit_message_text(new_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        finish_keyboard = [
            [InlineKeyboardButton("✅ تم استلام الخدمة واحتساب الساعة", callback_data=f"done_{task_id}")]
        ]
        try:
            await context.bot.send_message(
                chat_id=task["requester_id"],
                text=f"🎉 تقدم المتطوع {vol_username} لمساعدتك في طلبك #{task_id}!\nتواصل معه لإتمام الجلسة، وعند الانتهاء اضغط الزر أدناه لتوثيق الساعة في رصيده:",
                reply_markup=InlineKeyboardMarkup(finish_keyboard)
            )
        except Exception:
            pass

    elif action == "done":
        if str(query.from_user.id) != str(task["requester_id"]):
            await query.answer("فقط صاحب الطلب يمكنه تأكيد الإنجاز!", show_alert=True)
            return

        task["status"] = "completed"
        data["total_hours"] += 1
        vol_name = task["volunteer_name"]
        data["users"][vol_name] = data["users"].get(vol_name, 0) + 1
        save_data(data)

        completed_text = (
            f"📌 **طلب تبادل مهارة** #{task_id}\n\n"
            f"👤 **الطالب:** {task['requester_name']}\n"
            f"📝 **المطلوب:** {task['details']}\n"
            f"🔘 **الحالة:** 🏁 مكتملة وموثقة بنجاح ✨\n"
            f"🌟 **المتطوع:** {vol_name} (+1 ساعة)"
        )
        await context.bot.edit_message_text(
            chat_id=GROUP_CHAT_ID,
            message_id=task["message_id"],
            text=completed_text,
            parse_mode="Markdown"
        )
        await query.edit_message_text("✨ شكراً لك! تم توثيق الساعة وإضافتها إلى رصيد المتطوع بنجاح.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    total = data.get("total_hours", 0)
    users = data.get("users", {})
    top_list = "\n".join([f"• {u}: {h} ساعة" for u, h in sorted(users.items(), key=lambda x: x[1], reverse=True)[:5]])
    
    report = (
        f"📊 **إحصائيات مبادرة جزالة لبنك الوقت:**\n\n"
        f"⏱ **إجمالي الساعات المتبادلة:** {total} ساعة\n\n"
        f"🏆 **أبرز المساهمين بالعطاء:**\n{top_list if top_list else 'لا توجد ساعات مسجلة بعد.'}"
    )
    await update.message.reply_text(report, parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_private_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
