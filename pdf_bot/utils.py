import os
import tempfile

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError
from telegram import (
    ChatAction,
    Update,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import MAX_FILESIZE_DOWNLOAD, MAX_FILESIZE_UPLOAD
from telegram.ext import ConversationHandler, CallbackContext
from threading import Lock

from pdf_bot.constants import (
    PDF_OK,
    PDF_INVALID_FORMAT,
    PDF_TOO_LARGE,
    PDF_INFO,
    CHANNEL_NAME,
    PAYMENT,
)
from pdf_bot.language import set_lang
from pdf_bot.stats import update_stats


def cancel(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Action cancelled"), reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def check_pdf(update, context, send_msg=True):
    """
    Validate the PDF file
    Args:
        update: the update object
        context: the context object
        send_msg: the bool indicating to send a message or not

    Returns:
        The variable indicating the validation result
    """
    pdf_status = PDF_OK
    message = update.effective_message
    pdf_file = message.document
    _ = set_lang(update, context)

    if not pdf_file.mime_type.endswith("pdf"):
        pdf_status = PDF_INVALID_FORMAT
        if send_msg:
            message.reply_text(_("The file you sent is not a PDF file, try again"))
    elif pdf_file.file_size >= MAX_FILESIZE_DOWNLOAD:
        pdf_status = PDF_TOO_LARGE
        if send_msg:
            message.reply_text(
                _(
                    "The PDF file you sent is too large for me to download\n\n"
                    "I've cancelled your action"
                )
            )

    return pdf_status


def check_user_data(
    update: Update, context: CallbackContext, key: str, lock: Lock = None
) -> bool:
    """
    Check if the specified key exists in user_data
    Args:
        update: the update object
        context: the context object
        key: the string of key

    Returns:
        The boolean indicating if the key exists or not
    """
    data_ok = True
    if lock is not None:
        lock.acquire()

    if key not in context.user_data:
        data_ok = False
        _ = set_lang(update, context)
        update.effective_message.reply_text(_("Something went wrong, start over again"))

    if lock is not None:
        lock.release()

    return data_ok


def process_pdf(
    update,
    context,
    file_type,
    encrypt_pw=None,
    rotate_degree=None,
    scale_by=None,
    scale_to=None,
):
    """
    Process different PDF file manipulations
    Args:
        update: the update object
        context: the context object
        file_type: the string of file type
        encrypt_pw: the string of encryption password
        rotate_degree: the int of rotation degree
        scale_by: the tuple of scale by values
        scale_to: the tuple of scale to values

    Returns:
        None
    """
    with tempfile.NamedTemporaryFile() as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]

        if encrypt_pw is not None:
            pdf_reader = open_pdf(update, context, file_id, tf.name, file_type)
        else:
            pdf_reader = open_pdf(update, context, file_id, tf.name)

        if pdf_reader is not None:
            pdf_writer = PdfFileWriter()
            for page in pdf_reader.pages:
                if rotate_degree is not None:
                    pdf_writer.addPage(page.rotateClockwise(rotate_degree))
                elif scale_by is not None:
                    page.scale(scale_by[0], scale_by[1])
                    pdf_writer.addPage(page)
                elif scale_to is not None:
                    page.scaleTo(scale_to[0], scale_to[1])
                    pdf_writer.addPage(page)
                else:
                    pdf_writer.addPage(page)

            if encrypt_pw is not None:
                pdf_writer.encrypt(encrypt_pw)

            # Send result file
            write_send_pdf(update, context, pdf_writer, file_name, file_type)

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]


def open_pdf(update, context, file_id, file_name, file_type=None):
    """
    Download, open and validate PDF file
    Args:
        update: the update object
        context: the context object
        file_id: the string of the file ID
        file_name: the string of the file name
        file_type: the string of the file type

    Returns:
        The PdfFileReader object or None
    """
    _ = set_lang(update, context)
    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=file_name)
    pdf_reader = None

    try:
        pdf_reader = PdfFileReader(open(file_name, "rb"))
    except PdfReadError:
        update.effective_message.reply_text(
            _(
                "Your PDF file seems to be invalid and I couldn't open and read it\n\n"
                "I've cancelled your action"
            )
        )

    if pdf_reader is not None and pdf_reader.isEncrypted:
        if file_type is not None:
            if file_type == "encrypted":
                text = _("Your PDF file is already encrypted")
            else:
                text = _(
                    "Your {} PDF file is encrypted and you'll have to decrypt it first\n\n"
                    "I've cancelled your action"
                ).format(file_type)
        else:
            text = _(
                "Your PDF file is encrypted and you'll have to decrypt it first\n\n"
                "I've cancelled your action"
            )

        pdf_reader = None
        update.effective_message.reply_text(text)

    return pdf_reader


def send_file_names(update, context, file_names, file_type):
    """
    Send a list of file names to user
    Args:
        update: the update object
        context: the context object
        file_names: the list of file names
        file_type: the string of file type

    Returns:
        None
    """
    _ = set_lang(update, context)
    text = _("You've sent me these {} so far:\n").format(file_type)
    for i, filename in enumerate(file_names):
        text += f"{i + 1}: {filename}\n"

    update.effective_message.reply_text(text)


def write_send_pdf(update, context, pdf_writer, file_name, task):
    """
    Write and send result PDF file to user
    Args:
        update: the update object
        context: the context object
        pdf_writer: the PdfFileWriter object
        file_name: the string of the file name
        task: the string of the task

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as dir_name:
        new_fn = f"{task.title()}_{file_name}"
        out_fn = os.path.join(dir_name, new_fn)

        with open(out_fn, "wb") as f:
            pdf_writer.write(f)

        send_result_file(update, context, out_fn, task)


def send_result_file(update, context, out_fn, task):
    """
    Send result file to user
    Args:
        update: the update object
        context: the context object
        out_fn: the string of the output file name
        task: the string of the task

    Returns:
        None
    """
    _ = set_lang(update, context)
    message = update.effective_message
    reply_markup = get_support_markup(update, context)

    if os.path.getsize(out_fn) >= MAX_FILESIZE_UPLOAD:
        message.reply_text(
            _("The result file is too large for me to send to you"),
            reply_markup=reply_markup,
        )
    else:
        if out_fn.endswith(".png"):
            message.chat.send_action(ChatAction.UPLOAD_PHOTO)
            message.reply_photo(
                open(out_fn, "rb"),
                caption=_("Here is your result file"),
                reply_markup=reply_markup,
            )
        else:
            message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
            message.reply_document(
                document=open(out_fn, "rb"),
                caption=_("Here is your result file"),
                reply_markup=reply_markup,
            )

    update_stats(update, task)


def get_support_markup(update, context):
    """
    Create the reply markup
    Returns:
        The reply markup object
    """
    _ = set_lang(update, context)
    keyboard = [
        [
            InlineKeyboardButton(_("Join Channel"), f"https://t.me/{CHANNEL_NAME}"),
            InlineKeyboardButton(_("Support PDF Bot"), callback_data=PAYMENT),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    return reply_markup
