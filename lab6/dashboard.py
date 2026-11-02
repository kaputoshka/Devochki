"""Мини-BI: дашборд потоковых данных. Читает ClickHouse, обновляется автоматически (раз в 3 с) и по кнопке.
Запуск: uvicorn dashboard:app --port 8050  ->  http://localhost:8050"""
import os

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

CH = os.getenv("CLICKHOUSE_URL", "http://127.0.0.1:8123")
app = FastAPI(title="Stream dashboard")


def q(sql: str) -> list[dict]:
    r = requests.post(CH, params={"default_format": "JSON"}, data=sql.encode(), timeout=10)
    r.raise_for_status()
    return r.json()["data"]


@app.get("/api/data")
def data(windows: int = 30):
    series = q(f"""
        SELECT * FROM (
            SELECT window_start, window_end, total_clicks, total_views, total_purchases, total_revenue,
                   greatest(dateDiff('second', window_start, window_end), 1) AS secs,
                   round((total_clicks + total_views + total_purchases) / secs, 2) AS events_per_sec
            FROM analytics.stream_aggregates ORDER BY window_start DESC LIMIT {int(windows)}
        ) ORDER BY window_start""")
    totals = q("""SELECT count() AS windows, sum(total_clicks) AS clicks, sum(total_views) AS views,
                         sum(total_purchases) AS purchases, sum(total_revenue) AS revenue
                  FROM analytics.stream_aggregates""")[0]
    return {"series": series, "totals": totals}


PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Потоковые события — дашборд</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
body{font-family:Segoe UI,Arial,sans-serif;background:#f4f6fa;margin:0;color:#1f2937}
header{background:#1e3a5f;color:#fff;padding:14px 24px;display:flex;justify-content:space-between;align-items:center}
h1{font-size:20px;margin:0} button{background:#fff;border:0;border-radius:6px;padding:8px 14px;cursor:pointer;font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;padding:18px 24px 0}
.kpi{background:#fff;border-radius:10px;padding:14px 18px;box-shadow:0 1px 3px #0002}
.kpi small{color:#6b7280}.kpi b{display:block;font-size:26px;margin-top:4px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:14px 24px}
.card{background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 3px #0002}
.card h3{margin:0 0 8px;font-size:15px}.wide{grid-column:span 2}
#upd{font-size:12px;opacity:.8;margin-right:12px}
</style></head><body>
<header><h1>Потоковая аналитика пользовательских событий (Kafka → ClickHouse)</h1>
<div><span id="upd"></span><button onclick="load()">Обновить</button></div></header>
<div class="kpis">
 <div class="kpi"><small>Окон агрегации</small><b id="k0">–</b></div>
 <div class="kpi"><small>Клики</small><b id="k1">–</b></div>
 <div class="kpi"><small>Просмотры</small><b id="k2">–</b></div>
 <div class="kpi"><small>Покупки</small><b id="k3">–</b></div>
 <div class="kpi"><small>Выручка</small><b id="k4">–</b></div>
</div>
<div class="grid">
 <div class="card"><h3>События по типам в последних окнах</h3><canvas id="c1" height="150"></canvas></div>
 <div class="card"><h3>Динамика выручки по окнам</h3><canvas id="c2" height="150"></canvas></div>
 <div class="card wide"><h3>Интенсивность потока, событий в секунду</h3><canvas id="c3" height="70"></canvas></div>
</div>
<script>
const fmt=n=>Number(n).toLocaleString('ru-RU',{maximumFractionDigits:2});
const mk=(id,cfg)=>new Chart(document.getElementById(id),cfg);
const opt={animation:false,plugins:{legend:{position:'bottom'}},scales:{x:{ticks:{maxTicksLimit:8}}}};
const c1=mk('c1',{type:'bar',data:{labels:[],datasets:[
 {label:'click',backgroundColor:'#3b82f6',data:[]},{label:'view',backgroundColor:'#9ca3af',data:[]},{label:'purchase',backgroundColor:'#f59e0b',data:[]}]},
 options:{...opt,scales:{x:{stacked:true,ticks:{maxTicksLimit:8}},y:{stacked:true}}}});
const c2=mk('c2',{type:'line',data:{labels:[],datasets:[{label:'Выручка, ₽',borderColor:'#10b981',backgroundColor:'#10b98133',fill:true,tension:.25,data:[]}]},options:opt});
const c3=mk('c3',{type:'line',data:{labels:[],datasets:[{label:'events/sec',borderColor:'#ef4444',tension:.25,data:[]}]},options:opt});
async function load(){
 const d=await (await fetch('/api/data?windows=30')).json(), s=d.series, t=d.totals;
 const lab=s.map(r=>r.window_start.slice(11));
 c1.data.labels=lab;c1.data.datasets[0].data=s.map(r=>r.total_clicks);c1.data.datasets[1].data=s.map(r=>r.total_views);c1.data.datasets[2].data=s.map(r=>r.total_purchases);
 c2.data.labels=lab;c2.data.datasets[0].data=s.map(r=>r.total_revenue);
 c3.data.labels=lab;c3.data.datasets[0].data=s.map(r=>r.events_per_sec);
 [c1,c2,c3].forEach(c=>c.update());
 k0.textContent=fmt(t.windows);k1.textContent=fmt(t.clicks);k2.textContent=fmt(t.views);k3.textContent=fmt(t.purchases);k4.textContent=fmt(t.revenue)+' ₽';
 upd.textContent='обновлено '+new Date().toLocaleTimeString('ru-RU');
}
load();setInterval(load,3000);
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE
