# python
import math
import numpy as np
import seaborn as sns
import plotly.graph_objects as go
import plotly.io as pio
import tempfile
import webbrowser
import pandas as pd

def plot_with_matplotlib(fig, data_dict, selected_fields, x_axis_column, n_cols):
    num_fields = len(selected_fields)
    n_rows = math.ceil(num_fields / n_cols)
    axes = np.array(fig.subplots(n_rows, n_cols, sharex=True)).flatten().tolist()

    for idx, field in enumerate(selected_fields):
        ax = axes[idx]
        for file_name, df in data_dict.items():
            if field in df.columns:
                ax.plot(df[x_axis_column], df[field], marker='o', markersize=2, alpha=0.7, label=file_name)
        ax.set_title(field)
        ax.grid(True)
        ax.legend(fontsize='small')

    for j in range(len(selected_fields), len(axes)):
        fig.delaxes(axes[j])

    for ax in axes[-n_cols:]:
        ax.set_xlabel(x_axis_column)

    fig.tight_layout()

def plot_with_seaborn(fig, data_dict, selected_fields, x_axis_column, n_cols):
    sns.set(style="whitegrid", rc={'font.sans-serif': 'SimHei'})

    combined = []
    for file_name, df in data_dict.items():
        temp = df.copy()
        temp["__file__"] = file_name
        combined.append(temp)
    df_all = pd.concat(combined)

    num_fields = len(selected_fields)
    n_rows = math.ceil(num_fields / n_cols)
    axes = np.array(fig.subplots(n_rows, n_cols)).flatten().tolist()

    for idx, field in enumerate(selected_fields):
        ax = axes[idx]
        sns.lineplot(data=df_all, x=x_axis_column, y=field, hue="__file__", ax=ax, marker="o", linewidth=1)
        ax.set_title(field, fontdict={'fontsize': 12, 'fontweight': 'bold'})
        ax.set_xlabel(x_axis_column, fontdict={'fontsize': 10})
        ax.set_ylabel(field, fontdict={'fontsize': 10})

    for j in range(len(selected_fields), len(axes)):
        fig.delaxes(axes[j])

    fig.tight_layout()

def plot_with_plotly(fig, data_dict, selected_fields, x_axis_column, n_cols):
    from plotly.subplots import make_subplots
    num_fields = len(selected_fields)
    n_rows = math.ceil(num_fields / n_cols)

    subplot_titles = selected_fields
    fig_plotly = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=subplot_titles)

    for idx, field in enumerate(selected_fields):
        row = idx // n_cols + 1
        col = idx % n_cols + 1
        for file_name, df in data_dict.items():
            if field in df.columns:
                fig_plotly.add_trace(
                    go.Scatter(
                        x=df[x_axis_column],
                        y=df[field],
                        mode='lines+markers',
                        name=f"{file_name}: {field}"
                    ),
                    row=row,
                    col=col
                )

    fig_plotly.update_layout(
        height=None,
        width=None,
        title_text="Plotly交互式绘图"
    )

    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    pio.write_html(fig_plotly, file=tmpfile.name, auto_open=False)
    webbrowser.open(f"file://{tmpfile.name}")
    print(f"Plotly图表已生成并在浏览器打开，临时文件：{tmpfile.name}")