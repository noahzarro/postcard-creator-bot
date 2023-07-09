import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, constants
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from postcard_creator.postcard_creator import PostcardCreator, Postcard, Token, Recipient, Sender
import logging
import schedule

logging.basicConfig(level=10, filename="log.log", filemode="w")

logger = logging.getLogger('postcard_creator')

# database

default_user = {
    "username": "",
    "password": "",
    "sender": {
        "prename": "",
        "lastname": "",
        "street": "",
        "place": "",
        "zip": 0000,
    },
    "recipient": {
        "prename": "",
        "lastname": "",
        "street": "",
        "place": "",
        "zip": 0000,
    },
    "answer": "", # which answer the user will give after a button prompt
    "next_photo_id" : 0,
    "photos_cache": [],
    "photos_to_send": []

}

def get_all_user_ids():
    with open("users.json", "r") as f:
        users = json.load(f)
    return list(users.keys())

def get_user(id):
    id = str(id)
    with open("users.json", "r") as f:
        users = json.load(f)
    if str(id) in users:
        return users[id]
    else:
        set_user(id, default_user)
        return default_user


def set_user(id, user):
    id = str(id)

    with open("users.json", "r") as f:
        users = json.load(f)

    users[id] = user

    with open("users.json", "w") as f:
        json.dump(users, f)


def get_formatted_status(id):
    user = get_user(id)
    if user == None:
        return ""
    else:
        sender = "Prename: {prename}\nLastname: {lastname}\nStreet: {street}\nPlace: {place} {zip}".format(
            prename=user["sender"]["prename"], lastname=user["sender"]["lastname"], street=user["sender"]["street"], place=user["sender"]["place"], zip=user["sender"]["zip"])
        recipient = "Prename: {prename}\nLastname: {lastname}\nStreet: {street}\nPlace: {place} {zip}".format(
            prename=user["recipient"]["prename"], lastname=user["recipient"]["lastname"], street=user["recipient"]["street"], place=user["recipient"]["place"], zip=user["recipient"]["zip"])
        nr_of_cards = len(user["photos_cache"])
        return "**Sender:**\n{sender}\n\n**Recipient:**\n{recipient}\n\nNumber of queued postcards: {nr_of_cards}".format(sender=sender, recipient=recipient, nr_of_cards=nr_of_cards)


# create Bot
with open("token.json", "r") as read_file:
    TOKEN = json.load(read_file)["token"]
app = ApplicationBuilder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Send me your photos and then /send to send them as postcards. Use /config to enter swiss post username and password, and /sender, /recipient to set each name and address, use /status to see your current sender and recipient"
    )


async def new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    status = get_formatted_status(update.message.from_user.id)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Send me your photos. Current configuration is:\n{status}\n\n type /send to send postcards".format(status=status
        ),
        parse_mode=constants.ParseMode.MARKDOWN_V2
    )


async def config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Username", callback_data="await_username")],
        [InlineKeyboardButton("Password", callback_data="await_password")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("What do you want to edit?", reply_markup=reply_markup)


async def sender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Prename", callback_data="await_sender_prename"),
         InlineKeyboardButton("Lastname", callback_data="await_sender_lastname")],
        [InlineKeyboardButton("Street", callback_data="await_sender_street"),
         InlineKeyboardButton("Place", callback_data="await_sender_place")],
        [InlineKeyboardButton("Zip", callback_data="await_sender_zip"),
         InlineKeyboardButton("All", callback_data="await_sender_all")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("What do you want to edit?", reply_markup=reply_markup)

async def recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Prename", callback_data="await_recipient_prename"),
         InlineKeyboardButton("Lastname", callback_data="await_recipient_lastname")],
        [InlineKeyboardButton("Street", callback_data="await_recipient_street"),
         InlineKeyboardButton("Place", callback_data="await_recipient_place")],
        [InlineKeyboardButton("Zip", callback_data="await_recipient_zip")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("What do you want to edit?", reply_markup=reply_markup)

# gets called after a user pressed a button prompt
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.callback_query.from_user.id

    user = get_user(user_id)

    match query.data:
        case "await_username":
            user["answer"] = "await_username"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in your SwissID username")
        case "await_password":
            user["answer"] = "await_password"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in your SwissID password. Note: The password is stored in an unencrypted way. No guarantees")
        case "await_sender_prename":
            user["answer"] = "await_sender_prename"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in the senders prename")
        case "await_sender_lastname":
            user["answer"] = "await_sender_lastname"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in the senders lastname")
        case "await_sender_street":
            user["answer"] = "await_sender_street"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in the senders street and house number")
        case "await_sender_place":
            user["answer"] = "await_sender_place"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in the senders city")
        case "await_sender_zip":
            user["answer"] = "await_sender_zip"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in the senders zip code")
        case "await_recipient_prename":
            user["answer"] = "await_recipient_prename"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in the recipients prename")
        case "await_recipient_lastname":
            user["answer"] = "await_recipient_lastname"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in the recipients lastname")
        case "await_recipient_street":
            user["answer"] = "await_recipient_street"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in the recipients street and house number")
        case "await_recipient_place":
            user["answer"] = "await_recipient_place"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in the recipients city")
        case "await_recipient_zip":
            user["answer"] = "await_recipient_zip"
            set_user(user_id, user)
            await query.edit_message_text(text=f"Type in the recipients zip code")

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    user = get_user(user_id)
    photo_id = user["next_photo_id"]
    user["next_photo_id"] = user["next_photo_id"] + 1
    set_user(user_id, user)

    new_file = await update.message.effective_attachment[-1].get_file()

    user = get_user(user_id)
    user["photos_cache"].append(str(photo_id)+"."+new_file.file_path.split(".")[-1])
    set_user(user_id, user)

    os.makedirs("photos/"+str(user_id), exist_ok=True)
    await new_file.download_to_drive("photos/"+str(user_id)+"/"+str(photo_id)+"."+new_file.file_path.split(".")[-1])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Current config is\n"+get_formatted_status(user_id)+"\nUse /send to send postcards",
        parse_mode=constants.ParseMode.MARKDOWN_V2
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Current data:\n"+get_formatted_status(update.message.from_user.id),
        parse_mode=constants.ParseMode.MARKDOWN_V2
    )


async def send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user = get_user(user_id)

    photos = user["photos_cache"]
    user["photos_cache"] = []

    for photo in photos:
        to_send = {"sender": user["sender"], "recipient": user["recipient"], "photo": photo}
        user["photos_to_send"].append(to_send)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sending postcards"
    )

# gets called after an user sent a text answer after a button prompt
async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    received_data = update.message.text
    user = get_user(user_id)
    answer = user["answer"]
    user["answer"] = ""

    match answer:
        case "await_username":
            user["username"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Username updated")
        case "await_password":
            user["password"] = received_data
            set_user(user_id, user)
            await update.message.delete()
            await context.bot.send_message(user_id, "Password updated")
        case "await_sender_prename":
            user["sender"]["prename"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Sender Prename updated")
        case "await_sender_lastname":
            user["sender"]["lastname"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Sender Lastname updated")
        case "await_sender_street":
            user["sender"]["street"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Sender Street updated")
        case "await_sender_place":
            user["sender"]["place"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Sender Place updated")
        case "await_sender_zip":
            user["sender"]["zip"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Sender ZIP updated")
        case "await_recipient_prename":
            user["recipient"]["prename"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Recipient Prename updated")
        case "await_recipient_lastname":
            user["recipient"]["lastname"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Recipient Lastname updated")
        case "await_recipient_street":
            user["recipient"]["street"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Recipient Street updated")
        case "await_recipient_place":
            user["recipient"]["place"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Recipient Place updated")
        case "await_recipient_zip":
            user["recipient"]["zip"] = received_data
            set_user(user_id, user)
            await context.bot.send_message(user_id, "Recipient ZIP updated")


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Current config is\n"+get_formatted_status(user_id)+"\nUse /send to send postcards",
        parse_mode=constants.ParseMode.MARKDOWN_V2
    )


def send_cards():
    user_ids = get_all_user_ids()
    for user_id in user_ids:
        user = get_user(user_id)
        print(user_id)
        token = Token()
        token.fetch_token(user["username"], user["password"])
        w = PostcardCreator(token)
        has_free_postcard = w.impl.has_free_postcard()
        print(has_free_postcard)



app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("new", new))
app.add_handler(CommandHandler("config", config))
app.add_handler(CommandHandler("sender", sender))
app.add_handler(CommandHandler("recipient", recipient))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("send", send))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.PHOTO, photo))
app.add_handler(MessageHandler(filters.ALL, answer))

#token = Token()
#token.fetch_token(username='calmo.pfadiattila@gmail.com', password='Z_$Amw_i6QFv?VJ', method="swissid")
#print(token.to_json())
send_cards()

app.run_polling()
