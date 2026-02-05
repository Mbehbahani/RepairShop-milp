from .Idle_Overtime import build_idle_cost_model, solve_and_report
from .data_reader_json import read_schedule_data
import json, os, tempfile

def _to_tmp_file(payload: dict) -> str:
    tmp = tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False)
    json.dump(payload, tmp); tmp.flush()
    return tmp.name

def solve_instance(payload: dict, *, time_limit: int | None = 15):
    path = _to_tmp_file(payload)
    data = read_schedule_data(path)
    os.unlink(path)

    model, v      = build_idle_cost_model(data)
    df, st_stats, status   = solve_and_report(model, v, time_limit=time_limit)
    return df, st_stats, data["ST"], data["OV_limit"], status