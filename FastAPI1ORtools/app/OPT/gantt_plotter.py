import pandas as pd
import plotly.express as px

def _complete_with_idle(
    df: pd.DataFrame,
    station_stats: dict[int, tuple[int, int, float]],
    ST: dict[int, int],
) -> pd.DataFrame:
    parts = [df]
    seen = set(df["Station"])
    for s in station_stats:
        if s not in seen:
            shift_len = ST[s]
            parts.append(pd.DataFrame([{
                "Station": s,
                "Car":     "-",
                "Job":     "-",
                "Start":   0,
                "Finish":  shift_len,
                "Label":   f"idle = {shift_len} m"
            }]))
    return pd.concat(parts, ignore_index=True)

def _insert_idle_rows(df: pd.DataFrame, ST: dict[int, int]) -> pd.DataFrame:
    out: list[dict] = []
    for station, grp in df.groupby("Station", sort=False):
        grp = grp.sort_values("Start")
        prev_end = 0
        shift_len = ST.get(station, 0)
        for _, r in grp.iterrows():
            if r.Start > prev_end:
                out.append({
                    "Station": station,
                    "Car":     "-",
                    "Job":     "-",
                    "Start":   prev_end,
                    "Finish":  r.Start,
                    "Label":   f"idle = {r.Start - prev_end} m"
                })
            out.append({
                "Station": station,
                "Car":     r.Car,
                "Job":     r.Job,
                "Start":   r.Start,
                "Finish":  r.Finish,
                "Label":   f"car {r.Car}"
            })
            prev_end = r.Finish
        # tail idle until end of shift
        if prev_end < shift_len:
            out.append({
                "Station": station,
                "Car":     "-",
                "Job":     "-",
                "Start":   prev_end,
                "Finish":  shift_len,
                "Label":   f"idle = {shift_len - prev_end} m"
            })
    return pd.DataFrame(out)

def plot_gantt(
    df: pd.DataFrame,
    station_stats: dict[int, tuple[int, int, float]],
    ST: dict[int, int],
    OV_limit: dict[int, int],
    html_out: str = "gantt_chart.html",
    origin_date: str = "2025-01-01 08:00",
    *,
    return_fig: bool = False
) -> None:

    # 1) drop zero-length tasks
    df = df.loc[df.Finish > df.Start].copy()

    # 2) ensure each station has at least one bar
    df = _complete_with_idle(df, station_stats, ST)
    df_plot = _insert_idle_rows(df, ST)

    # 3) categorical y-axis in descending order (Station 1 at top)
    df_plot["Station_cat"] = df_plot["Station"].astype(str)
    station_order = [str(s) for s in sorted(station_stats, reverse=True)]

    # 4) convert times to datetimes
    origin = pd.to_datetime(origin_date)
    df_plot["Start_dt"]  = origin + pd.to_timedelta(df_plot["Start"],  unit="m")
    df_plot["Finish_dt"] = origin + pd.to_timedelta(df_plot["Finish"], unit="m")

    # 5) build colour map: one hue per car, white for Idle
    palette = px.colors.qualitative.Safe
    cars = sorted({c for c in df_plot.Car if c != "-"})
    repeats = -(-len(cars) // len(palette))
    full_palette = (palette * repeats)[: len(cars)]
    colour_map = {car: full_palette[i] for i, car in enumerate(cars)}
    colour_map["-"] = "#FFFFFF"
    car_categories = cars + ["-"]
    df_plot["Car"] = pd.Categorical(df_plot["Car"],
                                    categories=car_categories,
                                    ordered=True)

    df_plot["Hover"] = df_plot.apply(lambda row: (
        f"Idle block<br>"
        f"Start:&nbsp;{row.Start}<br>"
        f"Finish:&nbsp;{row.Finish}<br>"
        f"Duration:&nbsp;{row.Finish - row.Start} min"
    ) if row.Car == "-" else (
        f"Car&nbsp;{row.Car}<br>"
        f"Repair Type&nbsp;{row.Job}<br>"
        f"Start:&nbsp;{row.Start}<br>"
        f"Finish:&nbsp;{row.Finish}"
    ), axis=1)
    # 6) build the timeline figure
    fig = px.timeline(
        df_plot,
        x_start="Start_dt",
        x_end="Finish_dt",
        y="Station_cat",
        color="Car",
        text="Label",
        custom_data=["Hover"],  
        color_discrete_map=colour_map,
        category_orders={"Station_cat": station_order , "Car": car_categories},
        # title="Repair-Shop Gantt Chart"
    )
    fig.update_traces(
        hovertemplate="%{customdata[0]}<extra></extra>"
    )
    fig.update_traces(
        textposition="inside",
        insidetextanchor="middle",
        insidetextfont=dict(color="black", size=14)
    )
    fig.update_xaxes(tickformat="%H:%M", title="Time of day")
    fig.update_yaxes(
        title="Station",
        tickmode="array",
        tickvals=station_order,
        ticktext=station_order
    )
    fig.update_layout(
    legend=dict(
        orientation="h",   # horizontal instead of vertical
        yanchor="top",     # anchor the box’s *top*…
        y=-0.20,           # …then drop it below the x-axis
        xanchor="center",  # center-align
        x=0.5              # 50 % across the plot
    )
    )

    # 7) add per-station annotation boxes
    for s, (ov, idle, cost) in station_stats.items():
        last = max(df.loc[df.Station == s, "Finish"].max(), ST[s])
        x_txt = origin + pd.to_timedelta(last + 1, unit="m")
        fig.add_annotation(
            x=x_txt,
            y=str(s-1), yref="y",
            text=(
                f"cost {cost:.1f}<br>"
                f"OT {ov}m<br>"
                f"idle {idle}m<br>"
                f"Max {ST[s] + OV_limit[s]}m"
            ),
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            font=dict(color="black", size=9)
        )
    # 8) output
    if return_fig:
        return fig
    fig.write_html(html_out, include_plotlyjs="cdn")
    print(f"Gantt chart written to {html_out}")
