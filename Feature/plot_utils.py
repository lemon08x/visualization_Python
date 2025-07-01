# python
import math
import numpy as np
import seaborn as sns
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio
import tempfile
import webbrowser
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.cm as cm
from .plot_styles import DEFAULT_STYLE

def plot_with_matplotlib(fig, data_dict, selected_fields, x_axis_column, n_cols, right_y_axis=None, style=None):
    if style is None:
        style = DEFAULT_STYLE

    plt.rcParams['font.sans-serif'] = [style['font']]
    plt.rcParams['axes.unicode_minus'] = False

    num_fields = len(selected_fields)
    n_rows = math.ceil(num_fields / n_cols)
    axes = np.array(fig.subplots(n_rows, n_cols, sharex=True)).flatten().tolist()

    cmap = cm.get_cmap(style['color_palette'])
    color_idx = 0

    for idx, field in enumerate(selected_fields):
        ax = axes[idx]
        for file_idx, (file_name, df) in enumerate(data_dict.items()):
            if field in df.columns:
                ax.plot(df[x_axis_column], df[field],
                        marker='o', markersize=style['marker_size'],
                        linewidth=style['line_width'], alpha=style['alpha'],
                        label=file_name, color=cmap(file_idx))
        ax.set_title(field, fontsize=style['title_size'])
        ax.set_ylabel(field, fontsize=style['label_size'])
        ax.grid(True)
        ax.legend(fontsize=8)

        if right_y_axis and isinstance(right_y_axis, list) and len(right_y_axis) > 0:
            ax2 = ax.twinx()
            for field in right_y_axis:
                for file_name, df in data_dict.items():
                    if field in df.columns:
                        ax2.plot(df[x_axis_column], df[field], linestyle='--',
                                 linewidth=style['line_width'], alpha=0.6,
                                 label=f"{file_name}: {field}")
            ax2.set_ylabel(" / ".join(right_y_axis), fontsize=style['label_size'] + 1,
                           color='firebrick', fontweight='bold', labelpad=12)
            # # 合并图例
            # lines, labels = ax.get_legend_handles_labels()
            # lines2, labels2 = ax2.get_legend_handles_labels()
            # ax2.legend(lines + lines2, labels + labels2, fontsize='small')

    for j in range(len(selected_fields), len(axes)):
        fig.delaxes(axes[j])
    for ax in axes[-n_cols:]:
        ax.set_xlabel(x_axis_column, fontsize=style['label_size'])

    fig.tight_layout()

def plot_with_seaborn(fig, data_dict, selected_fields, x_axis_column, n_cols, right_y_axis=None, style=None):
    if style is None:
        style = DEFAULT_STYLE

    import seaborn as sns
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    sns.set_theme(style="whitegrid", font=style['font'])

    combined = []
    for file_name, df in data_dict.items():
        temp = df.copy()
        temp["__file__"] = file_name
        combined.append(temp)
    df_all = pd.concat(combined)

    num_fields = len(selected_fields)
    n_rows = math.ceil(num_fields / n_cols)
    axes = np.array(fig.subplots(n_rows, n_cols)).flatten().tolist()

    main_palette = sns.color_palette(style['color_palette'], len(data_dict))

    for idx, field in enumerate(selected_fields):
        ax = axes[idx]

        # 主图字段绘制
        sns.lineplot(
            data=df_all[df_all[field].notna()],
            x=x_axis_column, y=field,
            hue="__file__",
            ax=ax,
            errorbar=None,  # <-- Corrected parameter
            estimator=None,
            linewidth=style['line_width'],
            marker='o',
            palette=main_palette,
            legend=(idx == 0)
        )
        ax.set_title(field, fontsize=style['title_size'])
        ax.set_xlabel(x_axis_column, fontsize=style['label_size'])
        ax.set_ylabel(field, fontsize=style['label_size'])

        if right_y_axis and isinstance(right_y_axis, list):
            ax2 = ax.twinx()
            for ry_field in right_y_axis:
                if ry_field in df_all.columns:
                    for file_name in data_dict.keys():
                        df_file = df_all[df_all["__file__"] == file_name]
                        if ry_field in df_file.columns:
                            ax2.plot(
                                df_file[x_axis_column],
                                df_file[ry_field],
                                label=f"{file_name}: {ry_field}",
                                linestyle='--',
                                linewidth=style['line_width'],
                                color='firebrick',
                                alpha=0.5
                            )
            ax2.set_ylabel(" / ".join(right_y_axis), fontsize=style['label_size'], color='firebrick')

        if idx == 0:
            ax.legend(fontsize=8, loc='best')

    # 清除多余 subplot
    for j in range(len(selected_fields), len(axes)):
        fig.delaxes(axes[j])

    fig.tight_layout()


def plot_with_plotly(fig, data_dict, selected_fields, x_axis_column, n_cols, right_y_axis=None, style=None):
    if style is None:
        style = DEFAULT_STYLE

    num_fields = len(selected_fields)
    n_rows = math.ceil(num_fields / n_cols)

    subplot_titles = selected_fields
    specs = [[{"secondary_y": True} for _ in range(n_cols)] for _ in range(n_rows)]
    fig_plotly = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=subplot_titles, specs=specs)

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
                        name=f"{file_name}: {field}",
                        marker=dict(size=style['marker_size']),
                        line=dict(width=style['line_width']),
                        opacity=style['alpha']
                    ),
                    row=row, col=col, secondary_y=False
                )

        # 右轴多字段绘制
        if right_y_axis and isinstance(right_y_axis, list):
            for ry_field in right_y_axis:
                for file_name, df in data_dict.items():
                    if ry_field in df.columns:
                        fig_plotly.add_trace(
                            go.Scatter(
                                x=df[x_axis_column],
                                y=df[ry_field],
                                mode='lines',
                                name=f"{file_name}: {ry_field}",
                                line=dict(color='firebrick', dash='dot', width=style['line_width']),
                                opacity=style['alpha']
                            ),
                            row=row, col=col, secondary_y=True
                        )

        fig_plotly.update_yaxes(title_text=field, row=row, col=col, secondary_y=False)
        if right_y_axis:
            fig_plotly.update_yaxes(title_text=" / ".join(right_y_axis), row=row, col=col, secondary_y=True)
        fig_plotly.update_xaxes(title_text=x_axis_column, row=row, col=col)

    fig_plotly.update_layout(
        title_text="Plotly交互式绘图",
        height=max(600, 300 * n_rows),
        showlegend=True,
        hovermode='x unified',
        font=dict(family=style['font'], size=style['label_size'] + 2)
    )

    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    pio.write_html(fig_plotly, file=tmpfile.name, auto_open=False)
    webbrowser.open(f"file://{tmpfile.name}")
