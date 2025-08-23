from datetime import datetime
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt  # Add this import
import os


def save_triangle_chart(coin, c_time, c_open, c_high, c_low, c_close, indexes, flag_type, tf, direction) -> str:
    # беремо весь масив даних
    li = len(c_time) - 1

    # беремо дані від найдавнішої точки до li
    chart_start = max(0, li - max(indexes) - 100)  # додаємо 100 точок для контексту

    # Створюємо DataFrame для mplfinance
    chart_data = {
        'Open': c_open[chart_start:li + 1],
        'High': c_high[chart_start:li + 1],
        'Low': c_low[chart_start:li + 1],
        'Close': c_close[chart_start:li + 1]
    }

    # Створюємо індекс з датами
    timestamps = [datetime.fromtimestamp(float(ts) / 1000) for ts in c_time[chart_start:li + 1]]
    df = pd.DataFrame(chart_data, index=pd.DatetimeIndex(timestamps))

    # координати точок трикутника відносно поточного індексу li
    xs = indexes

    # Створюємо точки для додавання на графік
    scatter_points = []
    lines = []

    if flag_type == "hlhl":
        # HLHL: High, Low, High, Low
        points_data = []
        for i, idx in enumerate(indexes):
            chart_idx = li - xs[i] - chart_start
            if 0 <= chart_idx < len(df):
                if i in [0, 2]:  # High points
                    y_val = c_high[chart_start + chart_idx + 1]
                    points_data.append((chart_idx + 1, y_val, "red"))
                else:  # Low points
                    y_val = c_low[chart_start + chart_idx + 1]
                    points_data.append((chart_idx + 1, y_val, "green"))

        # Лінії
        if len(points_data) >= 4:
            # Верхня лінія (з'єднує максимуми)
            h1_idx, h1_val = points_data[0][0], points_data[0][1]
            h2_idx, h2_val = points_data[2][0], points_data[2][1]
            lines.append({
                'x1': timestamps[h1_idx], 'y1': h1_val,
                'x2': timestamps[h2_idx], 'y2': h2_val,
                'color': 'red', 'linestyle': '-', 'linewidth': 1
            })

            # Нижня лінія (з'єднує мінімуми)
            l1_idx, l1_val = points_data[1][0], points_data[1][1]
            l2_idx, l2_val = points_data[3][0], points_data[3][1]
            lines.append({
                'x1': timestamps[l1_idx], 'y1': l1_val,
                'x2': timestamps[l2_idx], 'y2': l2_val,
                'color': 'green', 'linestyle': '-', 'linewidth': 1
            })

    else:  # lhlh
        # LHLH: Low, High, Low, High
        points_data = []
        for i, idx in enumerate(indexes):
            chart_idx = li - xs[i] - chart_start
            if 0 <= chart_idx < len(df):
                if i in [1, 3]:  # High points
                    y_val = c_high[chart_start + chart_idx + 1]
                    points_data.append((chart_idx + 1, y_val, "red"))
                else:  # Low points
                    y_val = c_low[chart_start + chart_idx + 1]
                    points_data.append((chart_idx + 1, y_val, "green"))

        # Лінії
        if len(points_data) >= 4:
            # Верхня лінія (з'єднує максимуми)
            h1_idx, h1_val = points_data[1][0], points_data[1][1]
            h2_idx, h2_val = points_data[3][0], points_data[3][1]
            lines.append({
                'x1': timestamps[h1_idx], 'y1': h1_val,
                'x2': timestamps[h2_idx], 'y2': h2_val,
                'color': 'red', 'linestyle': '-', 'linewidth': 1
            })

            # Нижня лінія (з'єднує мінімуми)
            l1_idx, l1_val = points_data[0][0], points_data[0][1]
            l2_idx, l2_val = points_data[2][0], points_data[2][1]
            lines.append({
                'x1': timestamps[l1_idx], 'y1': l1_val,
                'x2': timestamps[l2_idx], 'y2': l2_val,
                'color': 'green', 'linestyle': '-', 'linewidth': 1
            })

    # Створюємо точки для відображення
    scatter_data = []
    for chart_idx, y_val, color in points_data:
        scatter_data.append(mpf.make_addplot(
            [y_val if i == chart_idx else float('nan') for i in range(len(df))],
            type='scatter',
            markersize=30,
            marker='o',
            color=color,
            secondary_y=False
        ))

    # Створюємо лінії
    line_plots = []
    for line_info in lines:
        # Створюємо масив для лінії
        line_data = [float('nan')] * len(df)

        # Знаходимо індекси для початку та кінця лінії
        start_idx = df.index.get_loc(line_info['x1'])
        end_idx = df.index.get_loc(line_info['x2'])

        # Інтерполюємо лінію між двома точками
        for i in range(min(start_idx, end_idx), max(start_idx, end_idx) + 1):
            if start_idx == end_idx:
                line_data[i] = line_info['y1']
            else:
                progress = (i - start_idx) / (end_idx - start_idx)
                line_data[i] = line_info['y1'] + progress * (line_info['y2'] - line_info['y1'])

        line_plots.append(mpf.make_addplot(
            line_data,
            color=line_info['color'],
            linestyle=line_info['linestyle'],
            width=line_info['linewidth']
        ))

    # Об'єднуємо всі додаткові елементи
    addplot = scatter_data + line_plots if scatter_data or line_plots else None

    # Створюємо ім'я файлу
    fname = f"{coin}_{tf}_{flag_type.upper()}.png"

    # Створюємо директорію
    out_path = os.path.join("triangles", fname)
    os.makedirs("triangles", exist_ok=True)

    fig, axlist = mpf.plot(
        df,
        type='candle',
        style='charles',
        title='',
        ylabel='',
        addplot=addplot,
        returnfig=True,
        figsize=(15, 6),
        show_nontrading=False,
    )

    # вимикаємо осі та ticks
    for ax in axlist:
        ax.set_axis_off()

    # прибираємо відступи
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # додаємо ватермарку через annotate на першій осі
    ax = axlist[0]
    ax.annotate(
        f"{tf} {coin} {direction}",
        xy=(0.5, 0.5),  # координати у відносних одиницях осі (0-1)
        xycoords='axes fraction',
        fontsize=50,
        color='gray',
        alpha=0.3,
        ha='center',
        va='center',
        rotation=0
    )

    # зберігаємо файл
    fig.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return out_path
