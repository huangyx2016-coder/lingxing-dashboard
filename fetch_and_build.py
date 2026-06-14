"""GitHub Actions: 领星 API 拉数据 → 处理 → 生成 HTML.
Usage: python fetch_and_build.py
Env vars: LINGXING_APP_ID, LINGXING_APP_SECRET
"""
import json, os, time
from datetime import datetime, timedelta
from collections import defaultdict

from lingxing import LingxingClient

SKIP_KW = ['合计', '总计', '销售', '月份', '平均', '汇总', '小计', '总数', 'sum', 'total']


def fetch_from_lingxing(app_id, app_secret, days=7):
    """拉取领星订单 + FBA 库存，返回原始 dict"""
    client = LingxingClient(app_id, app_secret)
    print(f"[{datetime.now()}] 连接 {client.host} ...")

    # 店铺列表
    print("[1/4] 获取店铺列表...")
    all_shops = client.get("/erp/sc/data/seller/lists").get("data", [])
    shops = [s for s in all_shops if s.get("status") == 1]
    print(f"  总 {len(all_shops)}，授权正常 {len(shops)}")

    # 订单
    sids = [s["sid"] for s in shops]
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    print(f"[2/4] 拉取订单 {start_date} ~ {end_date} ...")

    all_orders = []
    batch_size = 20
    for i in range(0, len(sids), batch_size):
        batch = sids[i:i + batch_size]
        offset = 0
        while True:
            resp = client.post("/erp/sc/data/mws/orders", body={
                "sid_list": batch, "start_date": start_date,
                "end_date": end_date, "date_type": 1,
                "offset": offset, "length": 5000,
            })
            data = resp.get("data", [])
            orders = data if isinstance(data, list) else data.get("list", [])
            total = resp.get("total", 0)
            all_orders.extend(orders)
            offset += len(orders)
            if offset >= total or len(orders) == 0:
                break
        time.sleep(1)
    print(f"  {len(all_orders)} 订单")

    # FBA 库存
    print("[3/4] 拉取 FBA 库存...")
    sid_str = ",".join(str(s["sid"]) for s in shops)
    stocks = []
    offset = 0
    while True:
        resp = client.post("/erp/sc/routing/fba/fbaStock/fbaList", body={
            "sid": sid_str, "offset": offset, "length": 200,
        })
        data = resp.get("data", {})
        items = data.get("list", []) if isinstance(data, dict) else []
        total = data.get("total", 0) if isinstance(data, dict) else resp.get("total", 0)
        stocks.extend(items)
        offset += len(items)
        if offset >= total or len(items) == 0:
            break
    print(f"  {len(stocks)} SKU")

    return {
        "pull_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "orders": all_orders,
        "stocks": stocks,
    }


def process(raw, days=7):
    """处理原始数据 → lingxing_data.json 格式"""
    orders = raw.get("orders", [])
    stocks = raw.get("stocks", [])

    # 按店铺×日期聚合
    shop_daily = defaultdict(lambda: {
        "daily": defaultdict(int), "amount": defaultdict(float),
        "total": 0, "total_amount": 0.0,
    })
    status_counts = defaultdict(int)
    dates_set = set()

    for o in orders:
        d = (o.get("purchase_date_local") or "")[:10]
        if not d:
            continue
        dates_set.add(d)
        name = o.get("seller_name", "?")
        amt = float(o.get("order_total_amount", 0) or 0)
        shop_daily[name]["daily"][d] += 1
        shop_daily[name]["amount"][d] += amt
        shop_daily[name]["total"] += 1
        shop_daily[name]["total_amount"] += amt
        status_counts[o.get("order_status", "?")] += 1

    dates = sorted(dates_set)[-days:] if len(dates_set) > days else sorted(dates_set)
    fmt_dates = [datetime.strptime(d, "%Y-%m-%d").strftime("%m/%d") for d in dates]

    orders_data = {}
    for name, d in sorted(shop_daily.items(), key=lambda x: x[1]["total"], reverse=True):
        orders_data[name] = {
            "daily": {fmt_dates[i]: d["daily"].get(date, 0) for i, date in enumerate(dates)},
            "amount": {fmt_dates[i]: round(d["amount"].get(date, 0), 2) for i, date in enumerate(dates)},
            "total": d["total"],
            "total_amount": round(d["total_amount"], 2),
        }

    # FBA 库存摘要
    def _int(v):
        try: return int(v) if v else 0
        except: return 0

    stock_summary = {
        "total_skus": len(stocks),
        "available": sum(_int(s.get("afn_fulfillable_quantity")) for s in stocks),
        "pending": sum(_int(s.get("reserved_customerorders")) for s in stocks),
        "inbound": sum(_int(s.get("afn_inbound_shipped_quantity")) for s in stocks),
        "unsellable": sum(_int(s.get("afn_unsellable_quantity")) for s in stocks),
    }

    warehouse_stock = defaultdict(lambda: {"available": 0, "pending": 0, "inbound": 0, "unsellable": 0, "skus": 0})
    for s in stocks:
        w = s.get("wname") or s.get("name", "?")
        warehouse_stock[w]["available"] += _int(s.get("afn_fulfillable_quantity"))
        warehouse_stock[w]["pending"] += _int(s.get("reserved_customerorders"))
        warehouse_stock[w]["inbound"] += _int(s.get("afn_inbound_shipped_quantity"))
        warehouse_stock[w]["unsellable"] += _int(s.get("afn_unsellable_quantity"))
        warehouse_stock[w]["skus"] += 1

    warehouse_data = dict(sorted(warehouse_stock.items(), key=lambda x: x[1]["available"], reverse=True))

    return {
        "pull_time": raw.get("pull_time", ""),
        "dates": fmt_dates,
        "dates_raw": dates,
        "orders": orders_data,
        "status": dict(status_counts),
        "stock_summary": stock_summary,
        "warehouse_stock": warehouse_data,
        "total_orders": len(orders),
        "total_amount": round(sum(float(o.get("order_total_amount", 0) or 0) for o in orders), 2),
        "shops_count": len(orders_data),
    }


def build_html(data):
    """从 lingxing_data.json 格式数据生成 index.html"""
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
Chart.register({{id:'showValues', afterDatasetsDraw:function(chart){{
  var ctx=chart.ctx, meta, x, y, val;
  ctx.save();
  ctx.font='bold 11px "Microsoft YaHei"';
  ctx.textAlign='center';
  ctx.textBaseline='bottom';
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
<div class="header"><h1>每日订单自动可视化</h1><p id="dateRange"></p></div>
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
  <div class="card full-width"><h2>银饰店铺订单 - 店铺明细</h2><div class="table-wrap" id="tLxCat3"></div></div>
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

  if(typeof Chart!=='undefined'){{
    var norm = function(s){{ return s.toLowerCase().replace(/\\s+/g,''); }};
    var earringKw = ['GIORGIA GIBBS','SLMYUER','GIULIA LEONI','varger','KATIE OTTE','ELEBEST','AMELINE','Selroper','SHERRIE DOBBIE','SPLIM','vuiikhir','ALUUYANN','AIGAMIT','Fanglcy','DZCYAN','Degerde','Aidomiya','TONYAUTOPARTS','GLOSOLE','Verniflloga','HaoShuFu','SPACMAG','ENROSE','KFERAXSZ','SPOINT','JADE KOS','CHLOÉ LOVETT','SANDRA REDD','HOBATS','MOMELF','NEARLAND','USESMTLE','Kelli Myers','ongol','Chantel Yorke','COSSA','BANGALO','Kate','Eterbeau','Amoxos','Fureoai','TAKUGI','VESTACE','Fureylenx','BalaBelle','LISHUIHAOMI','Cendyess','worfey','Magifurni','Tuogzzdq','EXRSANCH','VSK','KKR','POHYEOL','CALLIOPE','ESSIE ODILA','YFdeSi','Maodeso','JOZZFEE','nuoxun','Daolianlo','Lageza','iewrsox','Yiidcii','Aolumio','kvvkii','Howe rai','Sincere-ljh','Yezhenhan','SPARSE FOREST','PWQIEE','DOXVO','FOCALLIVE','niratty','YAUVC','Raysam','UUBUUCD','VTEVER','BEAUSPA','gotoeewigs','Lamdesa','SREEOWER','TECYOW','Charmire','Eloqueen','TG544','香港諾迅','鹏宇贸易','TG411','TG400'];
    var silverKw = ['LIEBLICH','ESSIE','Annamate','CHICLOVE','Billie Bijoux','Van Chloe','ANNIS MUNN','ANNIS','AmorAime','BlingGem','NinaMaid','WISHMISS'];
    var braceletKw = ['MELELIFE','KYAYE','HIROM JOINS','Moonfox','Simlayton','STREYANT','LOKFAM','FEGER','CANNCI','CISSIEPERAL','ERIN MARIE','BENOITE','AOZELAN','OR OLD RUBIN','OLD RUBIN','PPRLIFE','Rewizoo','KROMPG','MONA MILANI','PESFIOLO','gcwen','WONRUN','CROCHETFUN','iSunat','CKUSCAPO','UHEPROKIT','LUXCUTY','EYUMOI','Naiswan','LEMKAY','BYBAIZ','YIYEPUTI','Qeces','TOBENO','Yzytdgzy','Rinponain','TUOIXPI','KHFGDS','ODIHUI','LOUISE VELLA','MISSZHI','koolfin','FENMI','GYUYCW','Zikonyou','SUNDINS','香港惠拓','SparkSphere'];

    function matchKw(name, kwList){{
      for(var i=0; i<kwList.length; i++){{ if(norm(name).indexOf(norm(kwList[i]))!==-1) return true; }}
      return false;
    }}

    var allStores = Object.entries(LX.orders);
    var assigned2 = {{}}, earringTotal=0, silverTotal=0, braceletTotal=0, pendantTotal=0;
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
    allStores.forEach(function(x){{
      if(assigned2[x[0]]) return;
      if(matchKw(x[0], silverKw)){{ assigned2[x[0]]=true; silverTotal+=x[1].total; }}
    }});
    var catTotals = [
      {{label:'耳环', total:earringTotal}},
      {{label:'项链吊坠', total:pendantTotal}},
      {{label:'手链', total:braceletTotal}},
      {{label:'银饰', total:silverTotal}}
    ];
    var scols = ['#4472C4','#ED7D31','#FFC000','#70AD47'];
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

  if(typeof Chart!=='undefined'){{
    var topO = Object.entries(LX.orders).sort(function(a,b){{return b[1].total-a[1].total;}}).slice(0,15);
    new Chart(document.getElementById('lxBar'),{{type:'bar',
      data:{{labels:topO.map(function(x){{return x[0].length>18?x[0].slice(0,17)+'...':x[0];}}),
            datasets:[{{data:topO.map(function(x){{return x[1].total;}}), backgroundColor:colors[0], borderRadius:3}}]}},
      options:{{responsive:true, maintainAspectRatio:false, indexAxis:'y', plugins:{{legend:{{display:false}}}}, scales:{{x:{{grid:{{display:true}}}}}}}}}});
  }}

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

  (function(){{
    var norm = function(s){{ return s.toLowerCase().replace(/\\s+/g,''); }};
    var cats = [
      {{id:'tLxCat2', kw:['Cendyess','worfey','Magifurni','Tuogzzdq','EXRSANCH','VSK','KKR','POHYEOL','CALLIOPE','ESSIE ODILA','YFdeSi','Maodeso','JOZZFEE','nuoxun','Daolianlo','Lageza','iewrsox','Yiidcii','Aolumio','kvvkii','Howe rai','Sincere-ljh','Yezhenhan','SPARSE FOREST','PWQIEE','DOXVO','FOCALLIVE','niratty','YAUVC','Raysam','UUBUUCD','VTEVER','BEAUSPA','gotoeewigs','Lamdesa','SREEOWER','TECYOW','Charmire','Eloqueen','TG544','香港諾迅','鹏宇贸易','TG411','TG400','TG407']}},
      {{id:'tLxCat1', kw:['GIORGIA GIBBS','SLMYUER','GIULIA LEONI','varger','KATIE OTTE','ELEBEST','AMELINE','Selroper','SHERRIE DOBBIE','SPLIM','vuiikhir','ALUUYANN','AIGAMIT','Fanglcy','DZCYAN','Degerde','Aidomiya','TONYAUTOPARTS','GLOSOLE','Verniflloga','HaoShuFu','SPACMAG','ENROSE','KFERAXSZ','SPOINT','JADE KOS','CHLOÉ LOVETT','SANDRA REDD','HOBATS','MOMELF','NEARLAND','USESMTLE','Kelli Myers','ongol','Chantel Yorke','COSSA','BANGALO','Kate','Eterbeau','Amoxos','Fureoai','TAKUGI','VESTACE','Fureylenx','BalaBelle','LISHUIHAOMI']}},
      {{id:'tLxCat3', kw:['LIEBLICH','ESSIE','Annamate','CHICLOVE','Billie Bijoux','Van Chloe','ANNIS MUNN','ANNIS','AmorAime','BlingGem','NinaMaid','WISHMISS']}},
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
}}
</script>
</body>
</html>'''
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[{now}] index.html generated")


def main():
    app_id = os.environ["LINGXING_APP_ID"]
    app_secret = os.environ["LINGXING_APP_SECRET"]

    # Step 1: Fetch
    print("[Step 1/3] 拉取领星数据...")
    raw = fetch_from_lingxing(app_id, app_secret)

    # Step 2: Process
    print("[Step 2/3] 处理数据...")
    data = process(raw)
    with open("lingxing_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  {data['total_orders']} orders, {data['shops_count']} stores, {data['stock_summary']['available']} FBA available")

    # Step 3: Build HTML
    print("[Step 3/3] 生成 HTML...")
    build_html(data)
    print("Done.")


if __name__ == "__main__":
    main()
