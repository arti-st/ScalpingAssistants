import matplotlib.pyplot as plt
import pandas as pd
import mplfinance as mpf

def plot_ohlcv_and_cumdelta(symbol, c_time, c_open, c_high, c_low, c_close, cumulative_delta, save_path='chart.png'):
    # Convert timestamp to datetime
    time_index = pd.to_datetime(c_time, unit='ms')

    # Create OHLCV DataFrame
    df = pd.DataFrame({
        'Open': c_open,
        'High': c_high,
        'Low': c_low,
        'Close': c_close
    }, index=time_index)

    # Prepare figure
    fig = plt.figure(figsize=(10, 4), dpi=100)
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.05)

    # Upper plot: OHLCV using mplfinance
    ax1 = fig.add_subplot(gs[0])
    mpf.plot(df, type='candle', ax=ax1, xrotation=0, style='charles', show_nontrading=True)

    # Lower plot: cumulative delta
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.plot(time_index, cumulative_delta, color='blue', linewidth=1)
    ax2.set_ylabel(symbol, fontsize=8)
    ax2.grid(True)
    ax2.tick_params(axis='x', labelsize=6)
    ax2.tick_params(axis='y', labelsize=6)

    # Clean x-axis on top plot
    plt.setp(ax1.get_xticklabels(), visible=False)

    # Save or show
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()
