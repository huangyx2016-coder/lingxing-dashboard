"""Build payment summary visualization page."""
import json, sys
from datetime import datetime

def main():
    try:
        with open("payment_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("payment_data.json not found, exiting")
        sys.exit(1)

    pj = json.dumps(data, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    data_time = data.get("pull_time", now)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>打款汇总 Dashboard</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Microsoft YaHei', sans-serif; background:#f0f2f5; color:#333; padding:16px; }}
.header {{ text-align:center; margin-bottom:16px; }}
.header h1 {{ font-size:22px; color:#1a1a2e; }}
.header p {{ color:#666; margin-top:2px; font-size:12px; }}
.summary-bar {{ display:flex; gap:10px; margin-bottom:16px; flex-wrap:wrap; }}
.summary-item {{ flex:1; min-width:150px; background:#fff; border-radius:10px; padding:12px 14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); text-align:center; }}
.summary-item .value {{ font-size:20px; font-weight:bold; color:#4472C4; }}
.summary-item .label {{ font-size:10px; color:#888; margin-top:1px; }}
.card {{ background:#fff; border-radius:10px; padding:14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); margin-bottom:14px; }}
.card h2 {{ font-size:15px; margin-bottom:10px; border-bottom:2px solid #4472C4; padding-bottom:5px; }}
.card h2 span {{ font-size:12px; color:#888; font-weight:normal; }}
.table-wrap {{ max-height:600px; overflow-y:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:11px; }}
th {{ background:#4472C4; color:#fff; padding:6px 4px; position:sticky; top:0; z-index:1; text-align:center; white-space:nowrap; }}
td {{ padding:4px; border-bottom:1px solid #eee; }}
tr:hover td {{ background:#f5f7fa; }}
td:nth-child(1) {{ text-align:left; font-weight:500; min-width:200px; }}
td:nth-child(2) {{ text-align:left; font-size:10px; }}
td:nth-child(3) {{ text-align:right; }}
td:nth-child(4) {{ text-align:right; }}
td:nth-child(5) {{ text-align:right; }}
td:nth-child(6) {{ text-align:right; }}
.total-row td {{ font-weight:bold; background:#FFF2CC; border-top:2px solid #4472C4; }}
.red-cell {{ background:#FF6B6B; color:#fff; font-weight:bold; }}
.footer {{ text-align:right; color:#aaa; font-size:10px; margin-top:8px; }}
@media (max-width:768px) {{ .summary-item {{ min-width:120px; }} }}
</style>
</head>
<body>
<div class="header">
  <h1>打款汇总</h1>
  <p>各账户打款统计 | 目标日期: 07/16/2026</p>
</div>

<div class="summary-bar" id="sm"></div>
<div id="sheets"></div>
<div class="footer">数据更新: {data_time} | 页面生成: {now}</div>

<script>
var D = {pj};
(function(){{
  var orders = ['境外账户','耳环账户','银饰账户','手链','项链.戒指'];
  var grandC = 0, grandE = 0, grandF = 0, grandRows = 0;
  var html = '';

  orders.forEach(function(sn){{
    if(!D.sheets[sn]) return;
    var rows = D.sheets[sn];
    var sumC = 0, sumE = 0, sumF = 0;
    var dataRows = 0;

    var t = '<div class="card"><h2>'+sn+' <span>('+rows.length+'行)</span></h2><div class="table-wrap"><table>';
    t += '<thead><tr><th>账户</th><th>银行卡尾号信息</th><th>最近一次已打款金额</th><th>即将打款时间</th><th>对应打款金额</th><th>店铺余额</th></tr></thead><tbody>';

    rows.forEach(function(r, i){{
      var isTotal = r.A === '合计';
      var c = r.C, e = r.E, f = r.F;
      var cNum = (typeof c === 'number') ? c : 0;
      var eNum = (typeof e === 'number') ? e : 0;
      var fNum = (typeof f === 'number') ? f : 0;

      if(!isTotal) {{
        sumC += cNum; sumE += eNum; sumF += fNum;
        dataRows++;
      }}

      var cClass = '';
      if(typeof c === 'number' && c <= 0) cClass = ' class="red-cell"';
      else if(c === null || c === '' || (typeof c === 'string' && c.trim() === '无')) cClass = ' class="red-cell"';

      var rowClass = isTotal ? ' class="total-row"' : '';
      var cDisplay = (c === null || c === undefined) ? '' : (typeof c === 'number' ? c.toFixed(2).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',') : c);
      var eDisplay = (e === null || e === undefined) ? '' : (typeof e === 'number' ? e.toFixed(2).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',') : e);
      var fDisplay = (f === null || f === undefined) ? '' : (typeof f === 'number' ? f.toFixed(2).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',') : f);

      t += '<tr'+rowClass+'>';
      t += '<td>'+r.A+'</td>';
      t += '<td>'+r.B+'</td>';
      t += '<td'+cClass+'>'+cDisplay+'</td>';
      t += '<td>'+r.D+'</td>';
      t += '<td>'+eDisplay+'</td>';
      t += '<td>'+fDisplay+'</td>';
      t += '</tr>';
    }});

    t += '</tbody></table></div></div>';
    html += t;

    grandC += sumC; grandE += sumE; grandF += sumF; grandRows += dataRows;
  }});

  document.getElementById('sheets').innerHTML = html;

  document.getElementById('sm').innerHTML =
    '<div class="summary-item"><div class="value">'+grandRows+'</div><div class="label">总账户数</div></div>'+
    '<div class="summary-item"><div class="value">$'+grandC.toFixed(2).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',')+'</div><div class="label">最近一次已打款合计</div></div>'+
    '<div class="summary-item"><div class="value">$'+grandE.toFixed(2).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',')+'</div><div class="label">即将打款合计</div></div>'+
    '<div class="summary-item"><div class="value">$'+grandF.toFixed(2).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',')+'</div><div class="label">店铺余额合计</div></div>';
}})();
</script>
</body>
</html>'''

    with open("payment.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[{now}] payment.html generated")


if __name__ == "__main__":
    main()
