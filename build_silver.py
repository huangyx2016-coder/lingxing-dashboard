"""Generate silver_data.json and silver.html — standalone silver dashboard."""
import json
from datetime import datetime

def main():
    with open("silver_data.json", "r", encoding="utf-8") as f:
        silver_data = json.load(f)

    with open("silver_data.json", "w", encoding="utf-8") as f:
        json.dump(silver_data, f, ensure_ascii=False)

    # Build HTML with embedded data
    sj = json.dumps(silver_data, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    data_time = silver_data.get("pull_time", now)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>银饰订单 - 店铺明细</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Microsoft YaHei', sans-serif; background:#f0f2f5; color:#333; padding:16px; }}
.header {{ text-align:center; margin-bottom:16px; }}
.header h1 {{ font-size:22px; color:#1a1a2e; }}
.header p {{ color:#666; margin-top:2px; font-size:12px; }}
.nav {{ text-align:center; margin-bottom:16px; }}
.nav a {{ color:#4472C4; text-decoration:none; font-size:13px; padding:6px 14px; background:#fff; border-radius:6px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }}
.nav a:hover {{ background:#4472C4; color:#fff; }}
.card {{ background:#fff; border-radius:10px; padding:14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); margin-bottom:14px; max-width:1100px; margin-left:auto; margin-right:auto; }}
.card h2 {{ font-size:14px; margin-bottom:8px; border-bottom:2px solid #70AD47; padding-bottom:5px; }}
.table-wrap {{ max-height:600px; overflow-y:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:11px; }}
th {{ background:#70AD47; color:#fff; padding:5px 3px; position:sticky; top:0; z-index:1; text-align:center; white-space:nowrap; }}
td {{ padding:3px; text-align:center; border-bottom:1px solid #eee; }}
tr:hover td {{ background:#f5f7fa; }}
td:first-child {{ text-align:left; font-weight:500; }}
.num {{ text-align:right; }}
.total-row td {{ font-weight:bold; background:#FFF2CC; border-top:2px solid #70AD47; }}
.chart-wrap {{ position:relative; height:400px; margin-bottom:14px; max-width:1100px; margin-left:auto; margin-right:auto; }}
.summary-bar {{ display:flex; gap:14px; margin-bottom:14px; max-width:1100px; margin-left:auto; margin-right:auto; }}
.summary-item {{ flex:1; background:#fff; border-radius:10px; padding:12px 14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); text-align:center; }}
.summary-item .value {{ font-size:22px; font-weight:bold; color:#70AD47; }}
.summary-item .label {{ font-size:10px; color:#888; margin-top:1px; }}
.footer {{ text-align:right; color:#aaa; font-size:10px; margin-top:8px; }}
</style>
</head>
<body>
<div class="header"><h1>银饰订单 - 店铺明细</h1><p id="dateRange"></p></div>
<div class="nav">
  <a href="index.html">← 返回主仪表盘</a>
</div>
<div class="summary-bar" id="sm"></div>
<div class="chart-wrap"><canvas id="silverBar"></canvas></div>
<div class="card">
  <h2>全部银饰店铺</h2>
  <div class="table-wrap" id="tbl"></div>
</div>
<div class="footer">数据更新: {data_time} | 页面生成: {now}</div>

<script>
var LX = {sj};
var colors = ['#4472C4','#ED7D31','#70AD47','#FFC000','#5B9BD5'];

document.getElementById('dateRange').textContent = LX.dates[0] + ' — ' + LX.dates[LX.dates.length-1] + ' | ' + LX.total_orders.toLocaleString() + ' 单 | ' + LX.shops_count + ' 店铺';
document.getElementById('sm').innerHTML =
  '<div class="summary-item"><div class="value">'+LX.total_orders.toLocaleString()+'</div><div class="label">银饰总订单</div></div>'+
  '<div class="summary-item"><div class="value">'+LX.shops_count+'</div><div class="label">店铺数</div></div>';

if(typeof Chart!=='undefined'){{
  var allStores = Object.entries(LX.orders).sort(function(a,b){{return b[1].total-a[1].total;}});
  var top = allStores.slice(0,15);
  new Chart(document.getElementById('silverBar'),{{type:'bar',
    data:{{labels:top.map(function(x){{return x[0].length>18?x[0].slice(0,17)+'...':x[0];}}),
          datasets:[{{data:top.map(function(x){{return x[1].total;}}), backgroundColor:colors[2], borderRadius:3}}]}},
    options:{{responsive:true, maintainAspectRatio:false, indexAxis:'y', plugins:{{legend:{{display:false}}}}, scales:{{x:{{grid:{{display:true}}}}}}}}}});
}}

var h = '<table><thead><tr><th>店铺</th>';
LX.dates.forEach(function(d){{ h += '<th>'+d+'</th>'; }});
h += '<th>合计</th></tr></thead><tbody>';
allStores.forEach(function(x){{
  h += '<tr><td>'+x[0]+'</td>';
  LX.dates.forEach(function(d){{ h += '<td class="num">'+(x[1].daily[d]||0)+'</td>'; }});
  h += '<td class="num" style="font-weight:bold">'+x[1].total+'</td></tr>';
}});
h += '<tr class="total-row"><td>合计 ('+allStores.length+'店铺)</td>';
LX.dates.forEach(function(d){{
  var dt = allStores.reduce(function(s,x){{return s+(x[1].daily[d]||0);}},0);
  h += '<td class="num">'+dt+'</td>';
}});
h += '<td class="num">'+LX.total_orders+'</td></tr></tbody></table>';
document.getElementById('tbl').innerHTML = allStores.length ? h : '<p style="color:#999;text-align:center;padding:20px">暂无数据</p>';
</script>
</body>
</html>'''

    with open("silver.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[{now}] silver.html + silver_data.json generated ({silver_data["total_orders"]} orders, {silver_data["shops_count"]} stores)")


if __name__ == "__main__":
    main()
