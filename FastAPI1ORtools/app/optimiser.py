from .OPT import solve_instance
from .OPT.gantt_plotter import plot_gantt

def run_job(payload: dict):
    df, stats, ST, OV_lim, status = solve_instance(payload)
    print(f"Status: {status}")
    if df is None:
        return {
            "error": "No feasible solution found for the given data. "
                "Try reducing your durations, adding shift length, overtime cap or/and eligibilities."
        }
    # ── otherwise build the figure ───────────────────────────────────
    if status == 2:
        fig = plot_gantt(df, stats, ST, OV_lim, return_fig=True)
        return {"figure": fig.to_json(), "stats": stats,
                "warning": "⚠️ Warning: Returned solution is (near)-optimal due to limited server time in this trial version.<br>"
                "Try reducing problem size (e.g., fewer repairs or shorter durations), increase station hours, or contact us for the premium version."
    }
    
    fig = plot_gantt(df, stats, ST, OV_lim, return_fig=True)
    return {"figure": fig.to_json(), "stats": stats}