from __future__ import annotations
from .data_reader_json import read_schedule_data
import os
from ortools.sat.python import cp_model
from .gantt_plotter import plot_gantt
# ------------------------------------------------------------------
#  Build MILP model
# ------------------------------------------------------------------
def build_idle_cost_model(data, cost_scale: int = 10):
    model = cp_model.CpModel()
    # ---------- sets ----------
    C = sorted(data["d"].keys())                       # cars
    # gather all job types that appear in any car
    J = sorted({int(j) for jobs in data["d"].values() for j in jobs})
    R = sorted(data["ST"].keys())                      # stations
    OV_cap = data.get("OV_limit", {})

    # eligibility  j → [r, r, …]
    e   = {j: {r: int(v) for r, v in row.items()} for j, row in data["e"].items()}
    JxR = {j: [r for r, ok in e.get(j, {}).items() if ok] for j in J}

    bigM     = sum(dur for car in data["d"].values() for dur in car.values())
    max_time = bigM
    # max_ST = max(data["ST"].values())

    # ---------- variables ----------
    a, start, finish, interval = {}, {}, {}, {}
    for c in C:
        for j in J:
            dur = data["d"][c].get(j, 0)
            if dur == 0:
                continue
            start[c, j]  = model.NewIntVar(0, max_time, f"st_{c}_{j}")
            finish[c, j] = model.NewIntVar(0, max_time, f"fi_{c}_{j}")
            for r in JxR[j]:
                a[c, j, r] = model.NewBoolVar(f"a_{c}_{j}_{r}")
                interval[c, j, r] = model.NewOptionalIntervalVar(
                    start[c, j], dur, finish[c, j], a[c, j, r],
                    f"int_{c}_{j}_{r}")

    fin_last = {r: model.NewIntVar(0, max_time, f"finLast_{r}") for r in R}
    Ov       = {r: model.NewIntVar(0, max_time, f"Ov_{r}")       for r in R}
    Id       = {
        r: model.NewIntVar(0, data["ST"][r] + max_time, f"Id_{r}")
        for r in R
    }
    # ---------- constraints ----------
    # 1. assign every (car, job) to exactly one feasible station
    for c in C:
        for j in J:
            if data["d"][c].get(j, 0) > 0:
                model.Add(sum(a[c, j, r] for r in JxR[j]) == 1)

    # 2. no overlap on a station
    for r in R:
        model.AddNoOverlap([interval[c, j, r]
                            for (c, j, rr) in interval if rr == r])

    # 3. a car can’t be worked on in two places at once
    for c in C:
        car_intervals = [intv
                        for (cc, jj, rr), intv in interval.items()
                        if cc == c]                 # only those that were built
        if len(car_intervals) > 1:                   # no need for NoOverlap on 0/1
            model.AddNoOverlap(car_intervals)

    # 4. finish times propagate to fin_last
    for r in R:
        for (c, j, rr) in a:
            if rr == r:
                model.Add(fin_last[r] >= finish[c, j]).OnlyEnforceIf(a[c, j, r])

        total_proc = sum(data["d"][c][j] * a[c, j, r]
                        for (c, j, rr) in a if rr == r)
        St = data["ST"][r]
        model.Add(Ov[r] >= fin_last[r] - St)
        model.Add(Id[r] >= St + Ov[r] - total_proc)
        if r in OV_cap:
            model.Add(Ov[r] <= OV_cap[r])

    # ---------- objective ----------
    T_scaled = {r: int(round(data["T"][r] * cost_scale)) for r in R}
    I_scaled = {r: int(round(data["I"][r] * cost_scale)) for r in R}
    model.Minimize(sum(T_scaled[r] * Ov[r] + I_scaled[r] * Id[r] for r in R))

    return model, {
        "a": a, "start": start, "finish": finish,
        "Ov": Ov, "Id": Id, "fin_last": fin_last,
        "R": R, "C": C, "J": J,
        "T": T_scaled, "I": I_scaled, "scale": cost_scale,
    }


def solve_and_report(model, v, *, time_limit: int | None = None):
    import pandas as pd
    solver = cp_model.CpSolver()
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = float(time_limit)
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No feasible solution.")
        return None, None, status

    scale      = v['scale']
    total_cost = solver.ObjectiveValue() / scale
    print(f"\nOptimal total idle/overtime cost = {total_cost:,.2f}\n")

    schedule_rows = []
    station_stats = {}
    schedule_by_station = {r: [] for r in v['R']}

    for (c, j, r) in v['a']:
        if solver.Value(v['a'][(c, j, r)]):
            st  = solver.Value(v['start'][(c, j)])
            fin = solver.Value(v['finish'][(c, j)])
            schedule_rows.append(
                {"Station": r, "Car": c, "Job": j,  "Start": st, "Finish": fin})
            schedule_by_station[r].append((st, fin, c, j))

    # ── pretty print & collect stats ─────────────────────────────────────────
    for r in v['R']:
        ov   = solver.Value(v['Ov'][r])
        idle = solver.Value(v['Id'][r])
        cost = (v['T'][r] * ov + v['I'][r] * idle) / scale
        station_stats[r] = (ov, idle, cost)

        # print(f"Station {r:>2}: overtime {ov:>4}, idle {idle:>4}, "
        #     f"cost €{cost:>10.2f}")
        # for st, fin, c, j in sorted(schedule_by_station[r]):
        #     print(f"    Car {c:<3} – job {j:<2} - station {j:<2}:  {st:>5}  ->  {fin:<5}")
        # print()
    return pd.DataFrame(schedule_rows), station_stats, status
        
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(here, "schedule.json")
    data      = read_schedule_data(json_path)        # calls the new reader
    model, vars_=build_idle_cost_model(data)
    df_schedule, stats, _ = solve_and_report(model, vars_)
    if df_schedule is not None:
        plot_gantt(df_schedule, stats,data["ST"],data["OV_limit"], "schedule_gantt.html")

if __name__ == "__main__":
    main()