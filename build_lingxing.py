"""Build standalone daily orders visualization page."""
import json, sys
from datetime import datetime

def main():
    try:
        with open("lingxing_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("lingxing_data.json not found, exiting")
        sys.exit(1)

    lx_json = json.dumps(data, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    data_time = data.get("pull_time", now)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日订单自动可视化</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
// Plugin: show values on all charts
Chart.register({{id:'showValues', afterDatasetsDraw:function(chart){{
  var ctx=chart.ctx, meta, x, y, val;
  ctx.save();
  ctx.font='bold 11px \"Microsoft YaHei\"';
  ctx.textAlign='center';
  ctx.textBaseline='bottom';
  // Line chart: show values above points
  chart.data.datasets.forEach(function(ds,di){{
    meta=chart.getDatasetMeta(di);
    if(!meta||!meta.data)return;
    meta.data.forEach(function(pt,i){{
      val=ds.data[i];
      if(val===undefined||val===null)return;
      x=pt.x; y=pt.y-6;
      if(chart.options.indexAxis!=='y'){{
        ctx.fillStyle='#333';
        ctx.fillText(val.toLocaleString(),x,y);
      }}
    }});
  }});
  // Horizontal bar chart: show values at bar end
  if(chart.options.indexAxis==='y'){{
    chart.data.datasets.forEach(function(ds,di){{
      meta=chart.getDatasetMeta(di);
      if(!meta||!meta.data)return;
      meta.data.forEach(function(bar,i){{
        val=ds.data[i];
        if(val===undefined||val===null||val===0)return;
        x=bar.x; y=bar.y;
        ctx.fillStyle='#333';
        ctx.textAlign='left';
        ctx.textBaseline='middle';
        ctx.fillText(' '+val.toLocaleString(),x,y);
      }});
    }});
  }}
  ctx.restore();
}}, afterDraw:function(chart){{
  if(chart.config.type!=='pie')return;
  var ctx=chart.ctx, meta=chart.getDatasetMeta(0), w=chart.width;
  var total=chart.data.datasets[0].data.reduce(function(a,b){{return a+b;}},0);
  ctx.save();
  meta.data.forEach(function(arc,i){{
    var val=chart.data.datasets[0].data[i];
    if(!val)return;
    var pct=Math.round(val/total*100);
    if(pct<6)return;
    var angle=(arc.startAngle+arc.endAngle)/2;
    var r=arc.outerRadius*0.58;
    var x=arc.x+Math.cos(angle)*r;
    var y=arc.y+Math.sin(angle)*r;
    var dark=pct>25;
    ctx.fillStyle=w<400?'#333':(dark?'#fff':'#333');
    ctx.font=w<400?'bold 9px sans-serif':'bold 12px sans-serif';
    ctx.textAlign='center';
    ctx.textBaseline='bottom';
    ctx.fillText(pct+'%',x,y-2);
    ctx.fillStyle=w<400?'#333':(dark?'rgba(255,255,255,0.85)':'#333');
    ctx.font=w<400?'8px sans-serif':'10px sans-serif';
    ctx.textBaseline='top';
    ctx.fillText(val.toLocaleString()+'单',x,y+2);
  }});
  ctx.restore();
}}}});
</script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Microsoft YaHei', sans-serif; background:#f0f2f5; color:#333; padding:16px; }}
.header {{ text-align:center; margin-bottom:16px; }}
.header h1 {{ font-size:22px; color:#1a1a2e; }}
.header p {{ color:#666; margin-top:2px; font-size:12px; }}
.nav {{ text-align:center; margin-bottom:10px; }}
.nav a {{ color:#4472C4; text-decoration:none; font-size:13px; padding:6px 14px; background:#fff; border-radius:6px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }}
.nav a:hover {{ background:#4472C4; color:#fff; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px; }}
.card {{ background:#fff; border-radius:10px; padding:14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); }}
.card h2 {{ font-size:14px; margin-bottom:8px; border-bottom:2px solid #4472C4; padding-bottom:5px; }}
.chart-wrap {{ position:relative; height:280px; }}
.chart-wrap.tall {{ height:400px; }}
.table-wrap {{ max-height:500px; overflow-y:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:11px; }}
th {{ background:#4472C4; color:#fff; padding:5px 3px; position:sticky; top:0; z-index:1; text-align:center; white-space:nowrap; }}
td {{ padding:3px; text-align:center; border-bottom:1px solid #eee; }}
tr:hover td {{ background:#f5f7fa; }}
td:first-child {{ text-align:left; font-weight:500; }}
.num {{ text-align:right; }}
.total-row td {{ font-weight:bold; background:#FFF2CC; border-top:2px solid #4472C4; }}
.full-width {{ grid-column:1/-1; }}
.summary-bar {{ display:flex; gap:14px; margin-bottom:14px; flex-wrap:wrap; }}
.summary-item {{ flex:1; min-width:140px; background:#fff; border-radius:10px; padding:12px 14px; box-shadow:0 2px 6px rgba(0,0,0,0.06); text-align:center; }}
.summary-item .value {{ font-size:22px; font-weight:bold; color:#4472C4; }}
.summary-item .label {{ font-size:10px; color:#888; margin-top:1px; }}
.footer {{ text-align:right; color:#aaa; font-size:10px; margin-top:8px; }}
@media (max-width:768px) {{ .grid {{ grid-template-columns:1fr; }} .chart-wrap {{ height:340px; }} }}
</style>
</head>
<body>
<div class="header"><h1>每日订单自动可视化</h1><p id="dateRange"></p><button onclick="downloadCSV()" style="margin-top:6px;padding:6px 16px;background:#4472C4;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:13px;">下载数据 (CSV)</button></div>
<div class="summary-bar" id="smLx"></div>

<div class="grid">
  <div class="card"><h2>每日订单趋势</h2><div class="chart-wrap"><canvas id="lxLine"></canvas></div></div>
  <div class="card"><h2>最近7天各品类总订单占比</h2><div class="chart-wrap"><canvas id="lxPie"></canvas></div></div>
</div>

<div class="grid">
  <div class="card full-width"><h2>耳环订单 - 店铺明细</h2><div class="table-wrap" id="tLxCat1"></div></div>
  <div class="card full-width"><h2>新耳环店铺订单 - 店铺明细</h2><div class="table-wrap" id="tLxCat2"></div></div>
</div>
<div class="grid">
  <div class="card full-width"><h2>项链吊坠订单 - 店铺明细</h2><div class="table-wrap" id="tLxCat4"></div></div>
  <div class="card full-width"><h2>手链店铺订单 - 店铺明细</h2><div class="table-wrap" id="tLxCat5"></div></div>
</div>
<div class="grid">
  <div class="card"><h2>Top 15 店铺 (按最近7天总订单数)</h2><div class="chart-wrap tall"><canvas id="lxBar"></canvas></div></div>
  <div class="card"><h2>FBA库存 - 按店铺 Top 20</h2><div class="table-wrap" id="tLxStockByStore"></div></div>
</div>

<div class="footer">数据更新: {data_time} | 页面生成: {now}</div>

<script>
var LX = {lx_json};
document.getElementById('dateRange').textContent = '最近7天 | ' + LX.total_orders.toLocaleString() + ' 单 | ' + LX.shops_count + ' 店铺';

var colors = ['#4472C4','#ED7D31','#70AD47','#FFC000','#5B9BD5','#A5A5A5','#FF6B6B','#4ECDC4','#45B7D1','#96CEB4','#FFEAA7','#DDA0DD','#98D8C8'];

if (LX) {{
  document.getElementById('smLx').innerHTML =
    '<div class="summary-item"><div class="value">'+LX.total_orders.toLocaleString()+'</div><div class="label">最近7天总订单 ('+LX.shops_count+'店铺)</div></div>'+
    '<div class="summary-item"><div class="value">$'+LX.total_amount.toLocaleString()+'</div><div class="label">最近7天订单总额</div></div>'+
    '<div class="summary-item"><div class="value">'+LX.stock_summary.available.toLocaleString()+'</div><div class="label">FBA可售库存</div></div>'+
    '<div class="summary-item"><div class="value">'+LX.stock_summary.inbound.toLocaleString()+'</div><div class="label">在途</div></div>';

  // Daily order line chart
  if(typeof Chart!=='undefined' && LX.dates.length){{
    var dailyOrders = LX.dates.map(function(d){{
      var total = 0;
      Object.values(LX.orders).forEach(function(s){{ total += (s.daily[d]||0); }});
      return total;
    }});
    new Chart(document.getElementById('lxLine'),{{type:'line',
      data:{{labels:LX.dates, datasets:[{{data:dailyOrders, borderColor:'#4472C4', backgroundColor:'rgba(68,114,196,0.1)', fill:true, tension:0.3, pointRadius:5, pointBackgroundColor:'#4472C4'}}]}},
      options:{{responsive:true, maintainAspectRatio:false,
        plugins:{{legend:{{display:false}}, tooltip:{{callbacks:{{label:function(c){{return c.raw+' 单'}}}}}}}},
        scales:{{y:{{beginAtZero:true, grid:{{display:true}}}}}}}}}});
  }}

  // Category pie: 耳环, 项链吊坠, 手链
  if(typeof Chart!=='undefined'){{
    var norm = function(s){{ return s.toLowerCase().replace(/\\s+/g,''); }};
    var earringKw = ['GIORGIA GIBBS','SLMYUER','GIULIA LEONI','varger','KATIE OTTE','ELEBEST','AMELINE','Selroper','SHERRIE DOBBIE','SPLIM','vuiikhir','ALUUYANN','AIGAMIT','Fanglcy','DZCYAN','Degerde','Aidomiya','TONYAUTOPARTS','GLOSOLE','Verniflloga','HaoShuFu','SPACMAG','ENROSE','KFERAXSZ','SPOINT','JADE KOS','CHLOÉ LOVETT','SANDRA REDD','HOBATS','MOMELF','NEARLAND','USESMTLE','Kelli Myers','ongol','Chantel Yorke','COSSA','BANGALO','Kate','Eterbeau','Amoxos','Fureoai','TAKUGI','VESTACE','Fureylenx','BalaBelle','LISHUIHAOMI','Cendyess','worfey','Magifurni','Tuogzzdq','EXRSANCH','VSK','KKR','POHYEOL','CALLIOPE','ESSIE ODILA','YFdeSi','Maodeso','JOZZFEE','nuoxun','Daolianlo','Lageza','iewrsox','Yiidcii','Aolumio','kvvkii','Howe rai','Sincere-ljh','Yezhenhan','SPARSE FOREST','PWQIEE','DOXVO','FOCALLIVE','niratty','YAUVC','Raysam','UUBUUCD','VTEVER','BEAUSPA','gotoeewigs','Lamdesa','SREEOWER','TECYOW','Charmire','Eloqueen','TG544','香港諾迅','鹏宇贸易','TG411','TG400'];
    var braceletKw = ['MELELIFE','KYAYE','HIROM JOINS','Moonfox','Simlayton','STREYANT','LOKFAM','FEGER','CANNCI','CISSIEPERAL','ERIN MARIE','BENOITE','AOZELAN','OR OLD RUBIN','OLD RUBIN','PPRLIFE','Rewizoo','KROMPG','MONA MILANI','PESFIOLO','gcwen','WONRUN','CROCHETFUN','iSunat','CKUSCAPO','UHEPROKIT','LUXCUTY','EYUMOI','Naiswan','LEMKAY','BYBAIZ','YIYEPUTI','Qeces','TOBENO','Yzytdgzy','Rinponain','TUOIXPI','KHFGDS','ODIHUI','LOUISE VELLA','MISSZHI','koolfin','FENMI','GYUYCW','Zikonyou','SUNDINS','香港惠拓','SparkSphere'];

    function matchKw(name, kwList){{
      for(var i=0; i<kwList.length; i++){{ if(norm(name).indexOf(norm(kwList[i]))!==-1) return true; }}
      return false;
    }}

    var allStores = Object.entries(LX.orders);
    var assigned2 = {{}}, earringTotal=0, braceletTotal=0, pendantTotal=0;
    allStores.forEach(function(x){{
      if(assigned2[x[0]]) return;
      if(matchKw(x[0], earringKw)){{ assigned2[x[0]]=true; earringTotal+=x[1].total; }}
    }});
    allStores.forEach(function(x){{
      if(assigned2[x[0]]) return;
      if(matchKw(x[0], braceletKw)){{
        assigned2[x[0]]=true;
        if(x[0].indexOf('手链')!==-1 || norm(x[0]).indexOf(norm('香港惠拓'))!==-1){{ braceletTotal+=x[1].total; }}
        else{{ pendantTotal+=x[1].total; }}
      }}
    }});
    var catTotals = [
      {{label:'耳环', total:earringTotal}},
      {{label:'项链吊坠', total:pendantTotal}},
      {{label:'手链', total:braceletTotal}}
    ];
    var scols = ['#4472C4','#ED7D31','#FFC000'];
    var pieTotal = 0;
    catTotals.forEach(function(x){{ pieTotal += x.total; }});
    var pieLabels = catTotals.map(function(x){{ return x.label; }});
    var pieData = catTotals.map(function(x){{ return x.total; }});
    new Chart(document.getElementById('lxPie'),{{
      type:'pie',
      data:{{ labels:pieLabels, datasets:[{{ data:pieData, backgroundColor:scols }}] }},
      options:{{
        responsive:true,
        maintainAspectRatio:false,
        animation:false,
        plugins:{{ legend:{{ position:'right', labels:{{ font:{{ size:10 }}, padding:6 }} }} }}
      }}
    }});
  }}

  // Top 15 stores by orders
  if(typeof Chart!=='undefined'){{
    var topO = Object.entries(LX.orders).sort(function(a,b){{return b[1].total-a[1].total;}}).slice(0,15);
    new Chart(document.getElementById('lxBar'),{{type:'bar',
      data:{{labels:topO.map(function(x){{return x[0].length>18?x[0].slice(0,17)+'...':x[0];}}),
            datasets:[{{data:topO.map(function(x){{return x[1].total;}}), backgroundColor:colors[0], borderRadius:3}}]}},
      options:{{responsive:true, maintainAspectRatio:false, indexAxis:'y', plugins:{{legend:{{display:false}}}}, scales:{{x:{{grid:{{display:true}}}}}}}}}});
  }}

  // FBA stock grouped by store (top 20)
  (function(){{
    var storeStock = {{}};
    var suffixes = ['美国仓','加拿大仓','北美仓','欧洲仓','英国仓','墨西哥仓','巴西仓'];
    Object.entries(LX.warehouse_stock || {{}}).forEach(function(e){{
      var wname = e[0], stock = e[1];
      var sname = wname;
      suffixes.forEach(function(suf){{ if(sname.endsWith(suf)) sname = sname.slice(0, -suf.length); }});
      if(!storeStock[sname]) storeStock[sname] = {{available:0, pending:0, inbound:0, unsellable:0, skus:0}};
      storeStock[sname].available += stock.available;
      storeStock[sname].pending += stock.pending;
      storeStock[sname].inbound += stock.inbound;
      storeStock[sname].unsellable += stock.unsellable;
      storeStock[sname].skus += stock.skus;
    }});
    var top20 = Object.entries(storeStock).sort(function(a,b){{return b[1].available-a[1].available;}}).slice(0,20);
    var h = '<table><thead><tr><th>店铺</th><th>可售</th><th>待发货</th><th>在途</th><th>SKU数</th></tr></thead><tbody>';
    top20.forEach(function(x){{
      h += '<tr><td>'+x[0]+'</td><td class="num">'+x[1].available.toLocaleString()+'</td><td class="num">'+x[1].pending.toLocaleString()+'</td><td class="num">'+x[1].inbound.toLocaleString()+'</td><td class="num">'+x[1].skus+'</td></tr>';
    }});
    h += '</tbody></table>';
    document.getElementById('tLxStockByStore').innerHTML = h;
  }})();

  // Categorized order detail tables (all stores, order count only)
  (function(){{
    var norm = function(s){{ return s.toLowerCase().replace(/\\s+/g,''); }};
    var cats = [
      {{id:'tLxCat2', kw:['Cendyess','worfey','Magifurni','Tuogzzdq','EXRSANCH','VSK','KKR','POHYEOL','CALLIOPE','ESSIE ODILA','YFdeSi','Maodeso','JOZZFEE','nuoxun','Daolianlo','Lageza','iewrsox','Yiidcii','Aolumio','kvvkii','Howe rai','Sincere-ljh','Yezhenhan','SPARSE FOREST','PWQIEE','DOXVO','FOCALLIVE','niratty','YAUVC','Raysam','UUBUUCD','VTEVER','BEAUSPA','gotoeewigs','Lamdesa','SREEOWER','TECYOW','Charmire','Eloqueen','TG544','香港諾迅','鹏宇贸易','TG411','TG400','TG407']}},
      {{id:'tLxCat1', kw:['GIORGIA GIBBS','SLMYUER','GIULIA LEONI','varger','KATIE OTTE','ELEBEST','AMELINE','Selroper','SHERRIE DOBBIE','SPLIM','vuiikhir','ALUUYANN','AIGAMIT','Fanglcy','DZCYAN','Degerde','Aidomiya','TONYAUTOPARTS','GLOSOLE','Verniflloga','HaoShuFu','SPACMAG','ENROSE','KFERAXSZ','SPOINT','JADE KOS','CHLOÉ LOVETT','SANDRA REDD','HOBATS','MOMELF','NEARLAND','USESMTLE','Kelli Myers','ongol','Chantel Yorke','COSSA','BANGALO','Kate','Eterbeau','Amoxos','Fureoai','TAKUGI','VESTACE','Fureylenx','BalaBelle','LISHUIHAOMI']}},
      {{id:'tLxCat4', kw:['MELELIFE','KYAYE','HIROM JOINS','Moonfox','Simlayton','STREYANT','LOKFAM','FEGER','CANNCI','CISSIEPERAL','ERIN MARIE','BENOITE','AOZELAN','OR OLD RUBIN','OLD RUBIN','PPRLIFE','Rewizoo','KROMPG','MONA MILANI','PESFIOLO','gcwen','WONRUN','CROCHETFUN','iSunat','CKUSCAPO','UHEPROKIT','LUXCUTY','EYUMOI','Naiswan','LEMKAY','BYBAIZ','YIYEPUTI','Qeces','TOBENO','Yzytdgzy','Rinponain','TUOIXPI','KHFGDS','ODIHUI','LOUISE VELLA','MISSZHI','koolfin','FENMI','GYUYCW','Zikonyou','SUNDINS','香港惠拓','SparkSphere']}}
    ];
    var allStores = Object.entries(LX.orders).sort(function(a,b){{return b[1].total-a[1].total;}});
    var assigned = {{}};

    function renderTable(divId, stores){{
      var h = '<table><thead><tr><th>店铺</th>';
      LX.dates.forEach(function(d){{ h += '<th>'+d+'</th>'; }});
      h += '<th>合计</th></tr></thead><tbody>';
      var total = 0;
      stores.forEach(function(x){{
        h += '<tr><td>'+x[0]+'</td>';
        LX.dates.forEach(function(d){{ h += '<td class="num">'+(x[1].daily[d]||0)+'</td>'; }});
        h += '<td class="num" style="font-weight:bold">'+x[1].total+'</td></tr>';
        total += x[1].total;
      }});
      h += '<tr class="total-row"><td>合计 ('+stores.length+'店铺)</td>';
      LX.dates.forEach(function(d){{
        var dt = stores.reduce(function(s,x){{return s+(x[1].daily[d]||0);}},0);
        h += '<td class="num">'+dt+'</td>';
      }});
      h += '<td class="num">'+total+'</td></tr></tbody></table>';
      document.getElementById(divId).innerHTML = stores.length ? h : '<p style="color:#999;text-align:center;padding:20px">暂无数据</p>';
    }}

    cats.forEach(function(cat){{
      var stores = [];
      allStores.forEach(function(x){{
        if(assigned[x[0]]) return;
        var match = false;
        cat.kw.forEach(function(k){{ if(norm(x[0]).indexOf(norm(k)) !== -1) match = true; }});
        if(match){{ assigned[x[0]] = true; stores.push(x); }}
      }});

      if(cat.id === 'tLxCat4'){{
        var bracelet = [];
        var pendant = [];
        stores.forEach(function(x){{
          if(x[0].indexOf('手链') !== -1 || norm(x[0]).indexOf(norm('香港惠拓')) !== -1){{
            bracelet.push(x);
          }} else {{
            pendant.push(x);
          }}
        }});
        renderTable('tLxCat4', pendant);
        renderTable('tLxCat5', bracelet);
      }} else {{
        renderTable(cat.id, stores);
      }}
    }});
  }})();
}

function downloadCSV() {
  var dates = LX.dates;
  var rows = [];
  var header = ['SKU名称'];
  dates.forEach(function(d) { header.push(d + '订单量'); });
  dates.forEach(function(d) { header.push(d + '金额($)'); });
  header.push('总单量', '总金额($)');
  rows.push(header);

  var stores = Object.entries(LX.orders).sort(function(a,b) { return b[1].total - a[1].total; });
  stores.forEach(function(entry) {
    var name = entry[0], data = entry[1];
    var row = [name];
    dates.forEach(function(d) { row.push(data.daily[d] || 0); });
    dates.forEach(function(d) { row.push(data.amount[d] || 0); });
    row.push(data.total, data.total_amount);
    rows.push(row);
  });

  var csv = '﻿' + rows.map(function(r) {
    return r.map(function(v) {
      if (typeof v === 'string' && (v.indexOf(',') !== -1 || v.indexOf('"') !== -1)) {
        return '"' + v.replace(/"/g, '""') + '"';
      }
      return v;
    }).join(',');
  }).join('\n');

  var blob = new Blob([csv], {type: 'text/csv;charset=utf-8'});
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'lingxing_orders.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
</script>
</body>
</html>'''

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[{now}] index.html generated")


if __name__ == "__main__":
    main()
