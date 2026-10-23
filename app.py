import streamlit as st
import pandas as pd
import numpy as np
import requests, re, json, time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.graph_objects as go

st.set_page_config(page_title='FundRadar V15.1 · 大盘监测',page_icon='📡',layout='wide')
st.markdown('''<style>.stApp{background:#fff;color:#172033} [data-testid="stSidebar"]{background:#f2f6fc} [data-testid="stMetric"]{background:#f2f6fc;border:1px solid #dde5f0;border-radius:12px;padding:14px} h1,h2,h3{color:#142c50}</style>''',unsafe_allow_html=True)
TZ=timezone(timedelta(hours=8))
HEAD={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0 Safari/537.36','Referer':'https://finance.sina.com.cn/','Accept':'*/*'}
INDEXES={'上证指数':('sh000001','1.000001'),'深证成指':('sz399001','0.399001'),'沪深300':('sh000300','1.000300'),'创业板指':('sz399006','0.399006'),'科创50':('sh000688','1.000688'),'上证50':('sh000016','1.000016')}

def fetch(url,params=None,timeout=7):
    r=requests.get(url,params=params,headers=HEAD,timeout=timeout);r.raise_for_status();return r.text

def num(x):
    try:
        v=float(x)
        return v if np.isfinite(v) else None
    except (TypeError,ValueError):return None

def tencent_quotes():
    symbols=','.join(v[0] for v in INDEXES.values())
    raw=fetch('https://qt.gtimg.cn/q='+symbols)
    out={}
    for chunk in raw.split(';'):
        m=re.search(r'v_([a-z]{2}\d+)="([^"]+)"',chunk)
        if not m:continue
        a=m.group(2).split('~'); symbol=m.group(1)
        if len(a)<33:continue
        price=num(a[3]); prev=num(a[4]); change=num(a[32])
        if price and price>0 and prev and prev>0:
            out[symbol]={'price':price,'pct':(price/prev-1)*100,'stamp':a[30] if len(a)>30 else '', 'source':'腾讯'}
    return out

def sina_quotes():
    raw=fetch('https://hq.sinajs.cn/list='+','.join(v[0] for v in INDEXES.values()))
    out={}
    for chunk in raw.split(';'):
        m=re.search(r'hq_str_([a-z]{2}\d+)="([^"]+)"',chunk)
        if not m:continue
        a=m.group(2).split(','); sym=m.group(1)
        if len(a)<5:continue
        # index quote: name,current,change,change%,volume,amount
        price=num(a[1]);pct=num(a[3]);
        if price and price>0 and pct is not None:out[sym]={'price':price,'pct':pct,'stamp':'','source':'新浪'}
    return out

def eastmoney_quotes():
    out={}
    for name,(sym,secid) in INDEXES.items():
        try:
            raw=fetch('https://push2.eastmoney.com/api/qt/stock/get',{'secid':secid,'fields':'f43,f60,f57,f58,f124','ut':'fa5fd1943c7b386f172d6893dbfba10b'},5)
            d=json.loads(raw).get('data') or {};p=num(d.get('f43'));prev=num(d.get('f60'))
            if p and prev and p>0 and prev>0:out[sym]={'price':p/100,'pct':(p/prev-1)*100,'stamp':str(d.get('f124','')),'source':'东方财富'}
        except Exception:pass
    return out

@st.cache_data(ttl=300,show_spinner=False)
def quotes():
    diagnostics=[]; merged={}
    for label,fn in [('腾讯',tencent_quotes),('新浪',sina_quotes),('东方财富',eastmoney_quotes)]:
        if len(merged)==len(INDEXES):break
        try:
            data=fn()
            for k,v in data.items():merged.setdefault(k,v)
            diagnostics.append((label,'成功' if data else '无有效数据',len(data),'',datetime.now(TZ).strftime('%H:%M:%S')))
        except Exception as e:diagnostics.append((label,'失败',0,str(e)[:160],datetime.now(TZ).strftime('%H:%M:%S')))
    return merged,diagnostics,datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')

def parse_stock_rows(rows, expected, source):
    if not expected or expected < 2500 or len(rows) < expected:
        raise RuntimeError(f'{source}：分页覆盖不足 {len(rows)}/{expected}，拒绝计算TRIN')
    df=pd.DataFrame(rows).drop_duplicates(subset=['code'])
    df['pct']=pd.to_numeric(df['pct'],errors='coerce')
    df['turnover']=pd.to_numeric(df['turnover'],errors='coerce')
    df=df[df.pct.notna() & df.turnover.notna() & (df.turnover>=0)]
    if len(df)<max(2500,int(expected*.95)):
        raise RuntimeError(f'{source}：有效股票只有{len(df)}/{expected}')
    up=df[df.pct>0];down=df[df.pct<0];flat=df[df.pct==0]
    ua=float(up.turnover.sum());da=float(down.turnover.sum());a=len(up);d=len(down)
    return {'up':a,'down':d,'flat':len(flat),'total':len(df),'up_amount':ua,'down_amount':da,'breadth':100*a/len(df),'ad':a/d if d else None,'ud':ua/da if da else None,'trin':(a/d)/(ua/da) if d and da and ua else None,'rows':df[['code','name','pct','turnover']].rename(columns={'code':'代码','name':'名称','pct':'涨跌幅%','turnover':'成交额(元)'}),'source':source}

def breadth_eastmoney(domain):
    url=f'https://{domain}/api/qt/clist/get'
    common={'pn':1,'pz':1000,'po':1,'np':1,'ut':'bd1d9ddb04089700cf9c27f6f7426281','fltt':2,'invt':2,'fid':'f3','fs':'m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23','fields':'f2,f3,f6,f12,f13,f14'}
    rows=[];total=0
    for page in range(1,12):
        payload=json.loads(fetch(url,{**common,'pn':page},timeout=9));data=payload.get('data') or {}
        if page==1:total=int(data.get('total') or 0)
        diff=data.get('diff') or []
        if isinstance(diff,dict):diff=list(diff.values())
        if not diff:break
        for x in diff:
            rows.append({'code':str(x.get('f12','')),'name':x.get('f14',''),'pct':x.get('f3'),'turnover':x.get('f6')})
        if total and len(rows)>=total:break
    return parse_stock_rows(rows,total,'东方财富 '+domain)

def breadth_sina():
    # 新浪沪深A股分市场列表；每个市场必须完整分页，否则拒绝生成全市场结论
    rows=[];expected=0
    for node in ('sh_a','sz_a'):
        node_rows=[];node_total=None
        for page in range(1,90):
            url='https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
            raw=fetch(url,{'page':page,'num':80,'sort':'symbol','asc':1,'node':node,'symbol':'','_s_r_a':'page'},timeout=9)
            data=json.loads(raw)
            if not isinstance(data,list):raise RuntimeError(f'新浪 {node} 返回格式异常')
            if not data:break
            for x in data:
                code=str(x.get('code') or x.get('symbol') or '')
                if not code:continue
                node_rows.append({'code':code,'name':x.get('name',''),'pct':x.get('changepercent'),'turnover':x.get('turnover')})
            if len(data)<80:break
        if not node_rows:raise RuntimeError(f'新浪 {node} 无股票数据')
        rows.extend(node_rows)
    # 新浪该列表不提供可靠 total；仅允许足够覆盖、无重复的快照，标为部分市场样本，不冒充全A股
    raise RuntimeError(f'新浪列表取得{len(rows)}条，但无法验证全A股覆盖和成交额单位；不用于全市场TRIN')

@st.cache_data(ttl=600,show_spinner=False)
def breadth():
    errors=[]
    for domain in ('82.push2.eastmoney.com','push2.eastmoney.com','push2ex.eastmoney.com'):
        try:
            return breadth_eastmoney(domain),datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:errors.append(f'{domain}: {str(e)[:100]}')
    try:return breadth_sina(),datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:errors.append('新浪: '+str(e)[:100])
    raise RuntimeError('；'.join(errors))

def clean_history(df,source):
    df=df.copy();df['日期']=pd.to_datetime(df['日期'],errors='coerce')
    for c in ['开盘','收盘','最高','最低','成交量']:
        df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.dropna(subset=['日期','收盘']).sort_values('日期').drop_duplicates('日期')
    df=df[df['收盘']>0]
    if len(df)<65:raise RuntimeError(f'{source}有效日线不足65根（{len(df)}）')
    df.attrs['source']=source
    return df

def history_eastmoney(secid,days):
    raw=fetch('https://push2his.eastmoney.com/api/qt/stock/kline/get',{'secid':secid,'klt':101,'fqt':0,'lmt':days,'end':'20500101','fields1':'f1,f2,f3,f4,f5,f6','fields2':'f51,f52,f53,f54,f55,f56'},timeout=9)
    lines=(json.loads(raw).get('data') or {}).get('klines') or []
    df=pd.DataFrame([s.split(',')[:6] for s in lines],columns=['日期','开盘','收盘','最高','最低','成交量'])
    return clean_history(df,'东方财富')

def history_tencent(symbol,days):
    # 腾讯指数日K：kline / day，字段 [日期,开,收,高,低,量]
    raw=fetch('https://web.ifzq.gtimg.cn/appstock/app/fqkline/get',{'param':f'{symbol},day,,,{days},qfq'},timeout=10)
    obj=json.loads(raw);data=(obj.get('data') or {}).get(symbol) or {}
    lines=data.get('day') or data.get('qfqday') or []
    if not lines:raise RuntimeError('腾讯K线返回空数组')
    df=pd.DataFrame([{'日期':x[0],'开盘':x[1],'收盘':x[2],'最高':x[3],'最低':x[4],'成交量':x[5] if len(x)>5 else np.nan} for x in lines if len(x)>=5])
    if '成交量' not in df:df['成交量']=np.nan
    return clean_history(df,'腾讯')

def history_sina(symbol,days):
    raw=fetch('https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_data=/CN_MarketDataService.getKLineData',{'symbol':symbol,'scale':240,'ma':'no','datalen':days},timeout=10)
    match=re.search(r'(\[\s*\{.*\}\s*\])',raw,re.S)
    if not match:raise RuntimeError('新浪K线格式不符')
    data=json.loads(match.group(1))
    df=pd.DataFrame([{'日期':x.get('day'),'开盘':x.get('open'),'收盘':x.get('close'),'最高':x.get('high'),'最低':x.get('low'),'成交量':x.get('volume')} for x in data])
    return clean_history(df,'新浪')

@st.cache_data(ttl=3600,show_spinner=False)
def history(symbol,secid,days=400):
    errors=[]
    for label,fn in [('腾讯',lambda:history_tencent(symbol,days)),('新浪',lambda:history_sina(symbol,days)),('东方财富',lambda:history_eastmoney(secid,days))]:
        try:return fn()
        except Exception as e:errors.append(f'{label}: {str(e)[:110]}')
    raise RuntimeError('；'.join(errors))


st.sidebar.title('📡 FundRadar V15.1')
st.sidebar.caption('大盘优先 · 白色版 · 真实数据校验')
if st.sidebar.button('🔄 立即重新请求全部接口',use_container_width=True):
    quotes.clear();breadth.clear();history.clear();st.rerun()
show_breadth=st.sidebar.toggle('获取全市场股票涨跌快照',value=True,help='约6页请求，可能受云端访问限制；默认关闭避免拖慢页面')
selected=st.sidebar.selectbox('历史趋势指数',list(INDEXES),index=2)
st.sidebar.caption('报价缓存5分钟；宽度缓存10分钟；历史日线缓存1小时。页面不展示模拟行情。')
st.sidebar.warning('云端历史记录不会自动永久保存。请每日下载CSV留档。')
stock_csv=st.sidebar.file_uploader('可选：导入当日完整股票快照CSV',type=['csv'],help='列名需包含 代码、名称、涨跌幅%、成交额(元)；须是同一交易日的完整A股数据')
history_csv=st.sidebar.file_uploader('可选：导入指数历史日线CSV',type=['csv'],help='列名需包含 日期、开盘、收盘、最高、最低、成交量')
st.title('📡 FundRadar V15.1 · A股大盘监测终端')
st.info('🏃 加载状态：页面运行期间会显示加载动画；下方各模块分别标注成功/失败。所有模块结束后，页面底部显示【本轮加载已结束】。')
st.caption('优先指数与市场宽度；多源切换、覆盖校验、真实成交额TRIN、接口诊断。行情可能延迟，仅作研究辅助。')
q,diagnostics,updated=quotes()
st.subheader('🌏 核心指数行情')
cols=st.columns(3)
for i,(name,(symbol,secid)) in enumerate(INDEXES.items()):
    x=q.get(symbol)
    with cols[i%3]:
        if x:st.metric(name,f'{x["price"]:,.2f}',f'{x["pct"]:+.2f}%',help='来源：'+x['source'])
        else:st.metric(name,'数据缺失',help='所有尝试的公开通道均未返回有效报价')
st.caption(f'服务器请求时间（北京时间）：{updated}。指数涨跌幅为最近返回的行情，可能非实时；请核对交易日。')
if not q:st.error('全部指数报价通道失败。不是指数跌到0；请展开接口诊断检查云端连接。')

st.subheader('🧭 大盘强弱判读')
valid=[x['pct'] for x in q.values()]
if len(valid)>=4:
    positive=sum(v>0 for v in valid);negative=sum(v<0 for v in valid)
    st.metric('六大指数上涨数',f'{positive}/{len(valid)}')
    if positive>=5:st.success('指数共振偏强：多数主要指数上涨；仍需结合市场宽度和成交结构确认。')
    elif negative>=5:st.warning('指数共振偏弱：多数主要指数下跌；注意仓位和风险。')
    else:st.info('指数分化：不宜仅凭单一指数判断全市场强弱。')
else:st.info('指数有效覆盖不足4只，不生成大盘强弱结论。')

st.subheader('📊 全市场宽度 · Arms/TRIN')
st.caption('只有完整股票快照才计算；不把指数涨跌或成交额总量冒充上涨/下跌股票成交额。')
if show_breadth:
    try:
        if stock_csv is not None:
            upload=pd.read_csv(stock_csv,dtype={'代码':str})
            needed={'代码','名称','涨跌幅%','成交额(元)'}
            if not needed.issubset(upload.columns):raise ValueError('上传股票CSV缺少列：'+','.join(sorted(needed-set(upload.columns))))
            raw=[{'code':x['代码'],'name':x['名称'],'pct':x['涨跌幅%'],'turnover':x['成交额(元)']} for _,x in upload.iterrows()]
            b=parse_stock_rows(raw,len(raw),'用户导入CSV（请核实同日完整覆盖）')
            bt=datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
        else:b,bt=breadth()
        c=st.columns(4)
        for col,label,val in zip(c,['上涨/下跌/平盘','上涨占比','涨跌家数比 A/D','成交额TRIN'],[f'{b["up"]}/{b["down"]}/{b["flat"]}',f'{b["breadth"]:.1f}%',f'{b["ad"]:.2f}' if b['ad'] else '缺失',f'{b["trin"]:.2f}' if b['trin'] else '缺失']):col.metric(label,val)
        st.caption(f'来源 {b["source"]}；完整覆盖 {b["total"]} 只；北京时间 {bt}；上涨成交额 {b["up_amount"]/1e8:.0f} 亿元 / 下跌成交额 {b["down_amount"]/1e8:.0f} 亿元。成交额版TRIN=(上涨家数/下跌家数)/(上涨成交额/下跌成交额)，与成交量版定义不同。')
        if b['trin'] and b['trin']>1.2:st.warning('上涨股票相对成交额偏弱（TRIN>1.2）；属于结构警示，不等于机构出货已被证实。')
        elif b['trin'] and b['trin']<0.8:st.success('上涨股票相对成交额较强（TRIN<0.8）；仍须结合趋势和历史分位。')
        st.dataframe(b['rows'].sort_values('涨跌幅%',ascending=False),hide_index=True,use_container_width=True,height=250)
        st.download_button('下载本次股票快照 CSV',b['rows'].to_csv(index=False).encode('utf-8-sig'),'A股股票快照.csv','text/csv')
    except Exception as e:st.warning(f'全市场快照不可用：{str(e)[:230]}。不显示伪造的上涨家数或TRIN。可改用下面的指数趋势判读。')
else:st.info('默认不请求全市场股票接口。需要涨跌家数和TRIN时，请打开左侧「获取全市场股票涨跌快照」。')

st.subheader('📈 历史趋势 · MA20/MA60 · MACD · RSI')
try:
    if history_csv is not None:
        df=clean_history(pd.read_csv(history_csv),'用户导入CSV')
    else:df=history(INDEXES[selected][0],INDEXES[selected][1])
    close=df['收盘'];df['MA20']=close.rolling(20).mean();df['MA60']=close.rolling(60).mean()
    e12=close.ewm(span=12,adjust=False).mean();e26=close.ewm(span=26,adjust=False).mean();df['DIF']=e12-e26;df['DEA']=df.DIF.ewm(span=9,adjust=False).mean()
    delta=close.diff();gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean();loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean();df['RSI14']=100-100/(1+gain/loss.replace(0,np.nan))
    last=df.iloc[-1];lastdate=last['日期'].strftime('%Y-%m-%d')
    a,b,c,d=st.columns(4)
    a.metric('历史数据截至',lastdate);b.metric('MA20趋势','偏强' if last['收盘']>last.MA20 else '偏弱');c.metric('MA60趋势','偏强' if last['收盘']>last.MA60 else '偏弱');d.metric('RSI14',f'{last.RSI14:.1f}' if pd.notna(last.RSI14) else '缺失')
    fig=go.Figure();fig.add_trace(go.Scatter(x=df['日期'],y=df['收盘'],name='收盘',line=dict(color='#2563eb')))
    fig.add_trace(go.Scatter(x=df['日期'],y=df.MA20,name='MA20',line=dict(color='#e9a23b')))
    fig.add_trace(go.Scatter(x=df['日期'],y=df.MA60,name='MA60',line=dict(color='#16a085')))
    fig.update_layout(height=390,margin=dict(l=10,r=10,t=20,b=10),legend=dict(orientation='h'),plot_bgcolor='white',paper_bgcolor='white')
    st.plotly_chart(fig,use_container_width=True)
    st.caption('历史K线来源：'+df.attrs.get('source','未知')+'；日线日期：'+lastdate+'。均线与RSI基于真实日线计算。')
    st.download_button('📥 下载指数历史及指标 CSV',df.to_csv(index=False).encode('utf-8-sig'),f'{selected}_历史指标.csv','text/csv')
except Exception as e:st.warning(f'历史日线接口不可用：{str(e)[:220]}。当前不生成技术指标。')

st.subheader('🧪 数据通道诊断')
with st.expander('展开查看各通道是否成功、报错原因',expanded=not bool(q)):
    st.dataframe(pd.DataFrame(diagnostics,columns=['数据源','状态','有效指数数','错误摘要','请求时间']),hide_index=True,use_container_width=True)
    st.caption('注意：腾讯/新浪/东方财富均为公开网页数据入口，不承诺SLA。云端502、封禁、跨境网络或接口变更均可能导致失败。')
st.divider()
st.success('✅ 本轮页面加载已结束。请留意上方黄色错误提示：加载结束不等于全部数据成功。')
st.caption('FundRadar V15.1 | 不使用模拟价格，不把缺失值当作0，不把ETF代理称为官方沪深300全收益。市场指标仅辅助判断，不构成投资建议。')
