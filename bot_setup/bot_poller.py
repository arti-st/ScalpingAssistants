import asyncio
from aiogram import types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from bot_setup.bot_setup import bot, bot_dispatcher
from database_v2 import get_open_sizes, get_all_sizes
from mutual_variables.dictionaries import starting_parameters


def escape_markdown(text):
    chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in chars else char for char in str(text))


@bot_dispatcher.message(Command(commands=("coins")))
async def comm_coins(message: types.Message):
    t = starting_parameters['upd_time']
    c = starting_parameters['coins']

    if c is None:
        msg = 'Coins is not ready yet!'
    else:
        msg = "\n".join(
            f"{coin}: ts {params['tick_size']:.3f}%, atr {params['avg_atr']:.1f}%"
            for coin, params in c.items()
        )

    updated_time = t.strftime("%H:%M:%S") if t else ""

    text = f"`Updated: {updated_time}\n\n{msg}\n`"

    await message.answer(text, parse_mode='MarkdownV2')

@bot_dispatcher.message(Command(commands=("short_list")))
async def comm_short_list(message: types.Message):
    rows = await asyncio.to_thread(get_open_sizes)

    if not rows:
        await message.answer("Open sizes not found.")
        return

    headers = [
        "Coin",
        "DOM",
        "Dist",
        "Count",
    ]

    data = []

    for row in rows:
        direction = "↑" if row["direction"] == 1 else "↓"

        data.append([
            row["coin"],
            f"{row['dom']:.7g}",
            f"{direction}{row['distance']:.2f}",
            f"{row['continuous_count']}/{row['total_count']}",
        ])

    # Визначаємо максимальну ширину кожної колонки
    widths = []

    for i, header in enumerate(headers):
        max_width = display_width(header)

        for row in data:
            max_width = max(max_width, display_width(row[i]))

        widths.append(max_width)

    lines = []

    # Заголовок
    lines.append(
        "`" +
        "  ".join(
            pad_column(header, widths[i])
            for i, header in enumerate(headers)
        ) +
        "`"
    )

    # Розділювач
    lines.append(
        "`" +
        "  ".join(
            "-" * widths[i]
            for i in range(len(headers))
        ) +
        "`"
    )

    # Дані
    for row in data:
        lines.append(
            "`" +
            "  ".join(
                pad_column(value, widths[i])
                for i, value in enumerate(row)
            ) +
            "`"
        )

    text = "\n".join(lines)

    await message.answer(
        text,
        parse_mode="MarkdownV2"
    )


def display_width(value):
    value = str(value)

    width = 0

    for char in value:
        # Emoji та інші символи поза BMP займають 2 позиції
        if ord(char) > 0xFFFF:
            width += 2
        else:
            width += 1

    return width


def pad_column(value, width):
    value = "" if value is None else str(value)

    return value + " " * max(0, width - display_width(value))


def format_full_list(rows):
    headers = [
        "Date",
        "Coin",
        "DOM",
        "Chart",
        "Current",
        "Distance",
        "S-vs-DOM",
        "S-vs-Avg",
        "First",
        "Recent",
        "Count",
        "Status",
    ]

    data = []

    for row in rows:
        if row["direction"] == 1:
            distance = f"📈 {row['distance']}"
        else:
            distance = f"📉 {row['distance']}"

        data.append([
            row["date"],
            row["coin"],
            row["dom"],
            row["chart"],
            row["current_price"],
            distance,
            row["size_vs_dom"],
            row["size_vs_avg"],
            row["first_signal"],
            row["last_fixation"],
            f"{row['continuous_count']} ({row['total_count']})",
            STATUS_LABELS.get(row["status"], str(row["status"])),
        ])

    # Перетворюємо всі значення в текст
    data = [
        ["" if value is None else str(value) for value in row]
        for row in data
    ]

    # Ширина кожної колонки = найдовше значення
    # серед заголовка та всіх рядків
    widths = []

    for i, header in enumerate(headers):
        max_width = display_width(header)

        for row in data:
            max_width = max(max_width, display_width(row[i]))

        widths.append(max_width)

    lines = []

    # Заголовок
    lines.append(
        "  ".join(
            pad_column(header, widths[i])
            for i, header in enumerate(headers)
        )
    )

    # Розділювач
    lines.append(
        "  ".join(
            "-" * widths[i]
            for i in range(len(headers))
        )
    )

    # Дані
    for row in data:
        lines.append(
            "  ".join(
                pad_column(value, widths[i])
                for i, value in enumerate(row)
            )
        )

    return "\n".join(lines)


@bot_dispatcher.message(Command(commands=("full_list",)))
async def comm_full_list(message: types.Message):
    rows = await asyncio.to_thread(get_all_sizes)

    if not rows:
        await message.answer("No data.")
        return

    text = format_full_list(rows)

    document = BufferedInputFile(
        text.encode("utf-8"),
        filename="full_list.txt"
    )

    await message.answer_document(document)
    await message.answer_document(document)


@bot_dispatcher.message(Command(commands=("params",)))
async def comm_params(message: types.Message):
    try:
        with open("envs/params.env", encoding="utf-8") as file:
            params = file.read().strip()

        if not params:
            await message.answer("params.env is empty")
            return

        await message.answer(
            f"<pre>{params}</pre>",
            parse_mode="HTML"
        )

    except FileNotFoundError:
        await message.answer("File envs/params.env not found")
    except Exception as e:
        await message.answer(f"Error reading params.env: {e}")


async def poll():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot_dispatcher.start_polling(bot, polling_timeout=10, )

    except Exception as e:
        await asyncio.sleep(5)
        await poll()
