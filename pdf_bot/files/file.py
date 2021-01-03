from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters

from pdf_bot.constants import *
from pdf_bot.files.crop import (
    ask_crop_type,
    ask_crop_value,
    check_crop_percent,
    check_crop_size,
)
from pdf_bot.files.crypto import (
    ask_decrypt_pw,
    ask_encrypt_pw,
    decrypt_pdf,
    encrypt_pdf,
)
from pdf_bot.files.document import ask_doc_task
from pdf_bot.files.ocr import add_ocr_to_pdf
from pdf_bot.files.photo import (
    get_pdf_preview,
    get_pdf_photos,
    pdf_to_photos,
    ask_photo_results_type,
    process_photo_task,
    ask_photo_task,
)
from pdf_bot.files.rename import ask_pdf_new_name, rename_pdf
from pdf_bot.files.rotate import ask_rotate_degree, check_rotate_degree
from pdf_bot.files.scale import (
    ask_scale_type,
    ask_scale_value,
    check_scale_percent,
    check_scale_dimension,
)
from pdf_bot.files.split import ask_split_range, split_pdf
from pdf_bot.files.text import ask_text_type, get_pdf_text
from pdf_bot.files.compress import compress_pdf
from pdf_bot.language import set_lang
from pdf_bot.utils import cancel


def file_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.document, check_doc, run_async=True),
            MessageHandler(Filters.photo, check_photo, run_async=True),
        ],
        states={
            WAIT_DOC_TASK: [
                MessageHandler(TEXT_FILTER, check_doc_task, run_async=True)
            ],
            WAIT_PHOTO_TASK: [
                MessageHandler(TEXT_FILTER, check_photo_task, run_async=True)
            ],
            WAIT_CROP_TYPE: [
                MessageHandler(TEXT_FILTER, check_crop_task, run_async=True)
            ],
            WAIT_CROP_PERCENT: [
                MessageHandler(TEXT_FILTER, check_crop_percent, run_async=True)
            ],
            WAIT_CROP_OFFSET: [
                MessageHandler(TEXT_FILTER, check_crop_size, run_async=True)
            ],
            WAIT_DECRYPT_PW: [MessageHandler(TEXT_FILTER, decrypt_pdf, run_async=True)],
            WAIT_ENCRYPT_PW: [MessageHandler(TEXT_FILTER, encrypt_pdf, run_async=True)],
            WAIT_FILE_NAME: [MessageHandler(TEXT_FILTER, rename_pdf, run_async=True)],
            WAIT_ROTATE_DEGREE: [
                MessageHandler(TEXT_FILTER, check_rotate_degree, run_async=True)
            ],
            WAIT_SPLIT_RANGE: [MessageHandler(TEXT_FILTER, split_pdf, run_async=True)],
            WAIT_TEXT_TYPE: [
                MessageHandler(TEXT_FILTER, check_text_task, run_async=True)
            ],
            WAIT_SCALE_TYPE: [
                MessageHandler(TEXT_FILTER, check_scale_task, run_async=True)
            ],
            WAIT_SCALE_PERCENT: [
                MessageHandler(TEXT_FILTER, check_scale_percent, run_async=True)
            ],
            WAIT_SCALE_DIMENSION: [
                MessageHandler(TEXT_FILTER, check_scale_dimension, run_async=True)
            ],
            WAIT_EXTRACT_PHOTO_TYPE: [
                MessageHandler(TEXT_FILTER, check_get_photos_task, run_async=True)
            ],
            WAIT_TO_PHOTO_TYPE: [
                MessageHandler(TEXT_FILTER, check_to_photos_task, run_async=True)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel, run_async=True)],
        allow_reentry=True,
    )

    return conv_handler


def check_doc(update, context):
    doc = update.effective_message.document
    if doc.mime_type.startswith("image"):
        return ask_photo_task(update, context, doc)
    elif not doc.mime_type.endswith("pdf"):
        return ConversationHandler.END
    elif doc.file_size >= MAX_FILESIZE_DOWNLOAD:
        _ = set_lang(update, context)
        update.effective_message.reply_text(
            _(
                "Your PDF file is too big for me to download\n\nI can't perform any tasks on it"
            )
        )

        return ConversationHandler.END

    context.user_data[PDF_INFO] = doc.file_id, doc.file_name

    return ask_doc_task(update, context)


def check_photo(update, context):
    return ask_photo_task(update, context, update.effective_message.photo[-1])


def check_doc_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(CROP):
        return ask_crop_type(update, context)
    elif text == _(DECRYPT):
        return ask_decrypt_pw(update, context)
    elif text == _(ENCRYPT):
        return ask_encrypt_pw(update, context)
    elif text in [_(EXTRACT_PHOTO), _(TO_PHOTO)]:
        return ask_photo_results_type(update, context)
    elif text == _(PREVIEW):
        return get_pdf_preview(update, context)
    elif text == _(RENAME):
        return ask_pdf_new_name(update, context)
    elif text == _(ROTATE):
        return ask_rotate_degree(update, context)
    elif text in [_(SCALE)]:
        return ask_scale_type(update, context)
    elif text == _(SPLIT):
        return ask_split_range(update, context)
    elif text == _(EXTRACT_TEXT):
        return ask_text_type(update, context)
    elif text == OCR:
        return add_ocr_to_pdf(update, context)
    elif text == COMPRESS:
        return compress_pdf(update, context)
    elif text == _(CANCEL):
        return cancel(update, context)


def check_photo_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BEAUTIFY), _(TO_PDF)]:
        return process_photo_task(update, context)
    elif text == _(CANCEL):
        return cancel(update, context)


def check_crop_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BY_PERCENT), _(BY_SIZE)]:
        return ask_crop_value(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)


def check_scale_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BY_PERCENT), _(TO_DIMENSIONS)]:
        return ask_scale_value(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)


def check_text_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(TEXT_MESSAGE):
        return get_pdf_text(update, context, is_file=False)
    elif text == _(TEXT_FILE):
        return get_pdf_text(update, context, is_file=True)
    elif text == _(BACK):
        return ask_doc_task(update, context)


def check_get_photos_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(PHOTOS), _(COMPRESSED)]:
        return get_pdf_photos(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)


def check_to_photos_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(PHOTOS), _(COMPRESSED)]:
        return pdf_to_photos(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)
