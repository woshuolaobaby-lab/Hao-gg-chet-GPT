# -*- coding: utf-8 -*-
"""基金智能监控雷达 PRO MAX V9.2 · 153只基金 · 多通道加速稳定版"""
import re,time,json,math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime
import numpy as np,pandas as pd,requests,streamlit as st

ROOT=Path(__file__).resolve().parent
HEAD={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36","Referer":"https://fund.eastmoney.com/","Accept":"*/*","Connection":"keep-alive"}
st.set_page_config(page_title="FundRadar V12 · A股专业资金终端",page_icon="📡",layout="wide")

# 原V7的115只基金：内置，防止升级后丢失
BUILTIN_FUNDS=[
    ('001549', '天弘上证50ETF'),
    ('530000', '天弘上证50场内'),
    ('006021', '广发沪深300'),
    ('510300', '沪深300ETF'),
    ('011609', '易方达科创50'),
    ('588080', '科创50场内'),
    ('019817', '广发创业板ETF'),
    ('159952', '创业板场内'),
    ('588000', '科创50ETF华夏'),
    ('013305', '科创创业50'),
    ('023918', '自由现金流'),
    ('159201', '自由现金流场内'),
    ('017512', '北证50'),
    ('020465', '招商半导体'),
    ('561980', '半导体设备ETF'),
    ('020482', '机器人'),
    ('560770', '机器人ETF'),
    ('020900', '通信设备'),
    ('515880', '通信ETF'),
    ('024195', '卫星'),
    ('159206', '卫星ETF'),
    ('012734', '人工智能'),
    ('006503', '集成电路'),
    ('001072', '智能装备'),
    ('022364', '永赢科技'),
    ('019830', '数字产业'),
    ('016664', '高端制造'),
    ('008989', '科技创新'),
    ('009049', '易方达高端'),
    ('159852', '软件服务ETF'),
    ('012621', '软件服务场内'),
    ('002170', '东吴移动'),
    ('515250', '智能汽车场内'),
    ('013292', '富国智能汽车'),
    ('008586', '华夏人工智能'),
    ('019062', '易方达软件'),
    ('562930', '软件易方达场内'),
    ('020686', '科创新材料'),
    ('588160', '科创新材料场内'),
    ('019170', '云计算'),
    ('023885', '金融科技'),
    ('516100', '金融科技场内'),
    ('001630', '计算机'),
    ('159998', '计算机场内'),
    ('017877', '新能源'),
    ('018926', '电池'),
    ('019875', '稀有金属'),
    ('001410', '信澳新能源'),
    ('161028', '新能源汽车'),
    ('501226', '全球新能源'),
    ('019058', '绿色电力'),
    ('260112', '基建能源'),
    ('013817', '光伏'),
    ('516290', '光伏场内'),
    ('159755', '电池ETF'),
    ('159608', '稀有金属ETF'),
    ('159611', '电力ETF'),
    ('016185', '电力公用'),
    ('013476', '智能电动车'),
    ('016900', '碳中和'),
    ('562990', '碳中和场内'),
    ('025857', '电网设备'),
    ('159326', '电网设备场内'),
    ('006113', '创新药'),
    ('501009', '生物科技'),
    ('159892', '恒生医药ETF'),
    ('012738', '创新药广发'),
    ('515120', '创新药场内'),
    ('007883', '医药易方达'),
    ('512010', '医药ETF场内'),
    ('015945', '国防军工'),
    ('512560', '军工ETF'),
    ('025732', '航天航空'),
    ('028091', '航天航空行业'),
    ('161725', '白酒'),
    ('000083', '消费行业'),
    ('012857', '主要消费'),
    ('159928', '消费场内'),
    ('560880', '家电场内'),
    ('015040', '食品饮料'),
    ('159736', '食品饮料场内'),
    ('512690', '酒ETF'),
    ('005064', '家用电器'),
    ('159732', '消费电子ETF'),
    ('001469', '金融地产'),
    ('159940', '金融地产场内'),
    ('012874', '证券指数'),
    ('005663', '金融精选'),
    ('161029', '银行指数'),
    ('006697', '华宝银行'),
    ('512800', '银行场内'),
    ('512880', '证券ETF'),
    ('018099', '保险'),
    ('010365', '香港银行'),
    ('015896', '化工指数'),
    ('159870', '化工ETF'),
    ('005224', '基建工程'),
    ('516970', '基建场内'),
    ('014415', '畜牧养殖'),
    ('516670', '畜牧场内'),
    ('010770', '天弘农业'),
    ('512620', '农业场内'),
    ('008190', '钢铁'),
    ('515210', '钢铁场内'),
    ('008280', '煤炭'),
    ('515220', '煤炭场内'),
    ('008987', '上海金'),
    ('518600', '金场内'),
    ('165520', '800有色'),
    ('018853', '标普石油'),
    ('100039', '通胀通缩'),
    ('007786', '一带一路'),
    ('515150', '一带一路场内'),
    ('011036', '稀土产业'),
    ('159698', '粮食场内'),
    ('021087', '粮食产业'),
    ('020904', '工程机械'),
    ('560280', '工程机械场内'),
    ('161715', '大宗商品'),
    ('270023', '全球精选'),
    ('017731', '全球产业升级'),
    ('005698', '全球科技先锋'),
    ('018230', '全球优质企业'),
    ('100055', '全球科技互联网'),
    ('016702', '海外量化'),
    ('000043', '美国成长'),
    ('040046', '纳斯达克'),
    ('006479', '广发纳斯达克'),
    ('018147', '新兴市场'),
    ('008254', '华宝致远'),
    ('006328', '中概互联网'),
    ('513050', '中概互联网ETF'),
    ('000979', '港股深'),
    ('005555', '恒生国企ETF'),
    ('159954', '恒生国企场内'),
    ('013402', '恒生科技'),
    ('014674', '港股通互联网'),
    ('159792', '港股通互联网场内'),
    ('020969', '全球商品QDII'),
    ('012769', '动漫游戏'),
    ('159869', '动漫游戏场内'),
    ('004753', '传媒'),
    ('512980', '传媒场内'),
    ('000390', '华商优势'),
    ('166301', '华商新趋势'),
    ('720001', '财通价值动量'),
    ('001170', '宏利复兴'),
    ('001412', '德邦鑫星'),
    ('001438', '瑞享灵活'),
    ('001048', '新兴产业'),
    ('025942', '广发新动力'),
    ('002163', '东方惠新'),
    ('001194', '稳健回报'),
]
ETF_CODES=set(['159201', '159206', '159326', '159608', '159611', '159698', '159732', '159736', '159755', '159792', '159852', '159869', '159870', '159892', '159928', '159940', '159952', '159954', '159998', '510300', '512010', '512560', '512620', '512690', '512800', '512880', '512980', '513050', '515120', '515150', '515210', '515220', '515250', '515880', '516100', '516290', '516670', '516970', '518600', '560280', '560770', '560880', '561980', '562930', '562990', '588000', '588080', '588160'])
MACRO={"上证50":"510050","沪深300":"510300","科创50":"588000","创业板":"159915","QQQ":"QQQ","VOO":"VOO"}

SESSION=requests.Session(); SESSION.headers.update(HEAD)

@st.cache_data(ttl=900,show_spinner=False)
def http_get(url,params=None,timeout=15,referer=None):
    """统一网络通道：短超时 + 3次重试，失败尽快切换下一数据源。"""
    last=None
    headers=dict(HEAD)
    if referer:
        headers["Referer"]=referer
    for attempt in range(3):
        try:
            r=SESSION.get(url,params=params,headers=headers,timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            last=e
            if attempt<2:
                time.sleep(0.35*(2**attempt))
    raise RuntimeError(f"通道请求失败（已重试3次）: {last}")

@st.cache_data(ttl=86400,show_spinner=False)
def fund_hist(code):
    """开放式基金历史净值：主通道 pingzhongdata，备用 F10 JSON，再备用 F10 HTML。"""
    code=str(code).zfill(6); errors=[]
    # 通道1：pingzhongdata JS
    try:
        r=http_get(f"https://fund.eastmoney.com/pingzhongdata/{code}.js",{"v":int(time.time()*1000)},timeout=12)
        m=re.search(r"Data_netWorthTrend\s*=\s*(\[[\s\S]*?\]);",r.text)
        if m:
            rows=[]
            for z in json.loads(m.group(1)):
                try: rows.append((pd.to_datetime(int(z["x"]),unit="ms"),float(z["y"])))
                except: pass
            if len(rows)>=40:
                return pd.DataFrame(rows,columns=["date","close"]).set_index("date").sort_index().assign(volume=np.nan)
        errors.append("pingzhongdata无有效历史")
    except Exception as e: errors.append(f"pingzhongdata:{e}")
    # 通道2：F10 JSON 历史净值
    try:
        p={"fundCode":code,"pageIndex":1,"pageSize":500,"startDate":"","endDate":"","_":int(time.time()*1000)}
        r=http_get("https://api.fund.eastmoney.com/f10/lsjz",p,timeout=12,referer="https://fundf10.eastmoney.com/")
        z=r.json(); rows=[]
        for item in ((z.get("Data") or {}).get("LSJZList") or []):
            try: rows.append((pd.to_datetime(item["FSRQ"]),float(item["DWJZ"])))
            except: pass
        if len(rows)>=40:
            return pd.DataFrame(rows,columns=["date","close"]).set_index("date").sort_index().assign(volume=np.nan)
        errors.append(f"F10 JSON仅{len(rows)}条")
    except Exception as e: errors.append(f"F10 JSON:{e}")
    # 通道3：F10DataApi HTML 表格
    try:
        p={"type":"lsjz","code":code,"page":1,"per":200}
        r=http_get("https://fund.eastmoney.com/f10/F10DataApi.aspx",p,timeout=12,referer="https://fundf10.eastmoney.com/")
        dates=re.findall(r'<td>(\d{4}-\d{2}-\d{2})</td>\s*<td class="tor bold">([0-9.]+)</td>',r.text)
        rows=[(pd.to_datetime(d),float(v)) for d,v in dates]
        if len(rows)>=40:
            return pd.DataFrame(rows,columns=["date","close"]).set_index("date").sort_index().assign(volume=np.nan)
        errors.append(f"F10 HTML仅{len(rows)}条")
    except Exception as e: errors.append(f"F10 HTML:{e}")
    raise RuntimeError("基金历史数据3通道全部失败："+" | ".join(errors[-3:]))

@st.cache_data(ttl=86400,show_spinner=False)
def etf_hist(code):
    """ETF历史K线多通道：东财双节点 → 腾讯 → 新浪 → 基金净值 → Yahoo。"""
    code=str(code).zfill(6); errors=[]
    secid=("1."+code) if code.startswith(("5","6","68")) else ("0."+code)
    p={"secid":secid,"fields1":"f1,f2,f3,f4,f5,f6","fields2":"f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61","klt":"101","fqt":"1","beg":"0","end":"20500101","lmt":"500"}
    for endpoint in ["https://push2his.eastmoney.com/api/qt/stock/kline/get","https://push2.eastmoney.com/api/qt/stock/kline/get"]:
        try:
            j=http_get(endpoint,p,timeout=10).json(); ks=((j.get("data") or {}).get("klines") or [])
            rows=[]
            for item in ks:
                z=item.split(",")
                try: rows.append({"date":z[0],"open":float(z[1]),"close":float(z[2]),"high":float(z[3]),"low":float(z[4]),"volume":float(z[5])})
                except: pass
            if len(rows)>=40: return pd.DataFrame(rows)
            errors.append(f"{endpoint.split('//')[1].split('/')[0]}仅{len(rows)}条")
        except Exception as e: errors.append(f"东财:{e}")
    # 腾讯日K
    try:
        tq=("sh" if code.startswith(("5","6","68")) else "sz")+code
        url="https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        r=http_get(url,{"_var":"kline_dayqfq","param":f"{tq},day,,,{500},qfq"},timeout=10,referer="https://finance.qq.com/")
        raw=r.text; raw=raw[raw.find("=")+1:] if "=" in raw else raw
        z=json.loads(raw); d=((z.get("data") or {}).get(tq) or {}); arr=d.get("qfqday") or d.get("day") or []
        rows=[]
        for a in arr:
            try: rows.append({"date":a[0],"open":float(a[1]),"close":float(a[2]),"high":float(a[3]),"low":float(a[4]),"volume":float(a[5])})
            except: pass
        if len(rows)>=40: return pd.DataFrame(rows)
        errors.append(f"腾讯K线仅{len(rows)}条")
    except Exception as e: errors.append(f"腾讯K线:{e}")
    # 新浪日K
    try:
        sg=("sh" if code.startswith(("5","6","68")) else "sz")+code
        r=http_get("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData",{"symbol":sg,"scale":240,"ma":"no","datalen":1023},timeout=10,referer="https://finance.sina.com.cn/")
        arr=r.json(); rows=[]
        for a in arr:
            try: rows.append({"date":a["day"],"open":float(a["open"]),"close":float(a["close"]),"high":float(a["high"]),"low":float(a["low"]),"volume":float(a["volume"])})
            except: pass
        if len(rows)>=40: return pd.DataFrame(rows)
        errors.append(f"新浪K线仅{len(rows)}条")
    except Exception as e: errors.append(f"新浪K线:{e}")
    try:
        d=fund_hist(code)
        if len(d)>=40: return d
    except Exception as e: errors.append(f"基金净值:{e}")
    suffix=".SS" if code.startswith(("5","6","68")) else ".SZ"
    try:
        d=yahoo_hist(code+suffix)
        if len(d)>=40: return d
    except Exception as e: errors.append(f"Yahoo:{e}")
    raise RuntimeError("ETF历史数据5通道全部失败："+" | ".join(errors[-5:]))

@st.cache_data(ttl=300,show_spinner=False)
def fund_rt(code):
    code=str(code).zfill(6); errors=[]
    # 天天基金估值
    try:
        r=http_get(f"https://fundgz.1234567.com.cn/js/{code}.js",{"rt":int(time.time()*1000)},timeout=8)
        m=re.search(r"jsonpgz\((.*)\)",r.text)
        if m:
            z=json.loads(m.group(1)); price=float(z["gsz"]) if z.get("gsz") not in (None,"") else np.nan; pct=float(z["gszzl"]) if z.get("gszzl") not in (None,"") else np.nan
            return {"price":price,"pct":pct,"time":z.get("gztime","")}
        errors.append("天天基金无返回")
    except Exception as e: errors.append(f"天天基金:{e}")
    # 腾讯基金基础净值兜底：用于最新值/涨跌，字段随基金类型可能缺失，所以只在可解析时使用
    try:
        r=http_get(f"https://qt.gtimg.cn/q=jj{code}",timeout=8,referer="https://fund.qq.com/")
        txt=r.content.decode("gbk",errors="ignore"); m=re.search(r'="(.*?)"',txt)
        if m:
            a=m.group(1).split("~"); nums=[]
            for v in a:
                try: nums.append(float(v))
                except: nums.append(np.nan)
            vals=[v for v in nums if pd.notna(v) and v>0]
            if vals:
                price=vals[-1]
                return {"price":price,"pct":np.nan,"time":"腾讯基金兜底"}
        errors.append("腾讯基金无可用净值")
    except Exception as e: errors.append(f"腾讯基金:{e}")
    raise RuntimeError("基金实时估值2通道失败："+" | ".join(errors))

@st.cache_data(ttl=180,show_spinner=False)
def tencent_quote(code):
    code=str(code).zfill(6); sym=("sh" if code.startswith(("5","6","68")) else "sz")+code
    r=http_get("https://qt.gtimg.cn/q="+sym,timeout=8,referer="https://finance.qq.com/")
    txt=r.content.decode("gbk",errors="ignore"); m=re.search(r'="(.*?)"',txt)
    if not m: raise RuntimeError("腾讯行情无返回")
    a=m.group(1).split("~")
    if len(a)<33: raise RuntimeError("腾讯行情字段不足")
    price=float(a[3]); pct=float(a[32])
    return {"price":price,"pct":pct}

@st.cache_data(ttl=180,show_spinner=False)
def sina_quote(code):
    code=str(code).zfill(6); sym=("sh" if code.startswith(("5","6","68")) else "sz")+code
    r=http_get("https://hq.sinajs.cn/list="+sym,timeout=8,referer="https://finance.sina.com.cn/")
    txt=r.content.decode("gbk",errors="ignore"); m=re.search(r'="(.*?)"',txt)
    if not m: raise RuntimeError("新浪行情无返回")
    a=m.group(1).split(",")
    if len(a)<4: raise RuntimeError("新浪行情字段不足")
    return {"price":float(a[3]),"pct":(float(a[3])-float(a[2]))/float(a[2])*100 if float(a[2]) else np.nan}

@st.cache_data(ttl=180,show_spinner=False)
def etf_rt(code):
    code=str(code).zfill(6); errors=[]; secid=("1."+code) if code.startswith(("5","6","68")) else ("0."+code)
    try:
        z=(http_get("https://push2.eastmoney.com/api/qt/stock/get",{"secid":secid,"fields":"f43,f58,f169,f170"},timeout=8).json().get("data") or {})
        if z: return {"price":float(z["f43"]),"pct":float(z["f170"])/100,"channel":"东方财富"}
        errors.append("东财无返回")
    except Exception as e: errors.append(f"东财:{e}")
    try:
        z=tencent_quote(code); z["channel"]="腾讯"; return z
    except Exception as e: errors.append(f"腾讯:{e}")
    try:
        z=sina_quote(code); z["channel"]="新浪"; return z
    except Exception as e: errors.append(f"新浪:{e}")
    raise RuntimeError("ETF实时3通道失败："+" | ".join(errors))

@st.cache_data(ttl=21600,show_spinner=False)
def yahoo_hist(sym):
    end=int(time.time()); start=end-370*86400
    r=http_get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",{"period1":start,"period2":end,"interval":"1d","events":"history"})
    z=(r.json().get("chart") or {}).get("result") or []
    if not z: raise RuntimeError("Yahoo无数据")
    z=z[0]; q=z["indicators"]["quote"][0]; d=pd.to_datetime(z["timestamp"],unit="s")
    out=pd.DataFrame({"close":q["close"],"volume":q.get("volume")},index=d).dropna(subset=["close"])
    if len(out)<40: raise RuntimeError("Yahoo历史数据不足40条")
    return out

def indicators(d):
    x=d.copy(); c=pd.to_numeric(x["close"],errors="coerce").astype(float)
    x["MA5"]=c.rolling(5).mean(); x["MA20"]=c.rolling(20).mean(); x["MA60"]=c.rolling(60).mean(); x["MA120"]=c.rolling(120).mean()
    de=c.diff(); g=de.clip(lower=0).rolling(14).mean(); l=(-de.clip(upper=0)).rolling(14).mean(); x["RSI"]=100-100/(1+g/l.replace(0,np.nan))
    e12=c.ewm(span=12,adjust=False).mean(); e26=c.ewm(span=26,adjust=False).mean(); x["MACD"]=e12-e26; x["SIGNAL"]=x.MACD.ewm(span=9,adjust=False).mean(); x["HIST"]=x.MACD-x.SIGNAL
    x["RET20"]=c.pct_change(20)*100; x["RET60"]=c.pct_change(60)*100; x["DD"]=(c/c.cummax()-1)*100
    mid=c.rolling(20).mean(); sd=c.rolling(20).std(); x["BB_POS"]=(c-(mid-2*sd))/(4*sd)*100; x["VOL"]=c.pct_change().rolling(20).std()*math.sqrt(252)*100
    x["MA20_SLOPE"]=x.MA20.pct_change(5)*100; x["MA60_SLOPE"]=x.MA60.pct_change(10)*100
    x["MA_GOLDEN"]=(x.MA5>x.MA20)&(x.MA5.shift(1)<=x.MA20.shift(1)); x["MA_DEAD"]=(x.MA5<x.MA20)&(x.MA5.shift(1)>=x.MA20.shift(1))
    x["MACD_GOLDEN"]=(x.MACD>x.SIGNAL)&(x.MACD.shift(1)<=x.SIGNAL.shift(1)); x["MACD_DEAD"]=(x.MACD<x.SIGNAL)&(x.MACD.shift(1)>=x.SIGNAL.shift(1))
    x["MA_GOLDEN_10D"]=x.MA_GOLDEN.rolling(10).max().fillna(False).astype(bool)
    x["MACD_GOLDEN_10D"]=x.MACD_GOLDEN.rolling(10).max().fillna(False).astype(bool)
    return x

def score(x):
    """严格版多指标评分：100分制，且买入信号有硬性门槛，避免仅靠金叉/短期动量就误判。"""
    r=x.iloc[-1]; s=0; why=[]; risk=[]
    def add(cond, pts, good):
        nonlocal s
        if pd.notna(cond) and bool(cond): s += pts; why.append(good)

    # 1) 趋势 35 分：必须尽量站在中长期趋势之上
    add(r.close>r.MA20,6,"价格站上MA20")
    add(r.MA20>r.MA60,7,"MA20>MA60")
    add(r.close>r.MA60,5,"价格站上MA60")
    add(r.MA60>r.MA120,4,"MA60>MA120")
    add(r.close>r.MA120,3,"价格站上MA120")
    add(r.MA20_SLOPE>0,5,"MA20向上")
    add(r.MA60_SLOPE>0,5,"MA60向上")

    # 2) 动量 20 分：短中期都要有确认
    add(r.RET20>0,5,"20日动量为正")
    add(r.RET20>3,3,"20日动量>3%")
    add(r.RET60>0,5,"60日动量为正")
    add(r.RET60>5,3,"60日动量>5%")

    # 3) MACD 20 分：不仅看多头，还看零轴与柱体改善
    add(r.MACD>r.SIGNAL,6,"MACD多头")
    add(r.MACD>0,4,"MACD在零轴上方")
    hist_rising = len(x)>=2 and pd.notna(x.HIST.iloc[-1]) and pd.notna(x.HIST.iloc[-2]) and x.HIST.iloc[-1]>x.HIST.iloc[-2]
    if hist_rising: s+=5; why.append("MACD柱体改善")
    if bool(r.MACD_GOLDEN_10D): s+=5; why.append("10日内MACD金叉")

    # 4) RSI 15 分：健康区间优先，极端高位严禁追涨
    if pd.notna(r.RSI):
        if 52<=r.RSI<=68: s+=15; why.append("RSI健康52-68")
        elif 48<=r.RSI<52: s+=10; why.append("RSI接近健康区")
        elif 68<r.RSI<=72: s+=7; why.append("RSI偏强但可控")
        elif r.RSI>72: risk.append("RSI过热")
        elif r.RSI<35: s+=3; why.append("RSI超跌，需等待确认")

    # 5) 风险/位置 10 分：避免追高与异常波动
    if pd.notna(r.DD):
        if -12<=r.DD<=-3: s+=5; why.append("回撤区间较适合分批")
        elif r.DD>-3: risk.append("距离高点过近，追高风险")
        elif r.DD<-20: risk.append("回撤过大")
        else: s+=2; why.append("回撤可接受")
    if pd.notna(r.VOL):
        if r.VOL<30: s+=5; why.append("波动率较低")
        elif r.VOL>45: risk.append("波动率偏高")
        else: s+=2

    # 硬性否决/扣分
    if bool(r.MA_DEAD): s-=10; risk.append("MA死叉")
    if bool(r.MACD_DEAD): s-=10; risk.append("MACD死叉")
    if pd.notna(r.RSI) and r.RSI>72: s-=10
    if pd.notna(r.RET60) and r.RET60<-8: s-=8; risk.append("60日趋势明显偏弱")
    if pd.notna(r.RET20) and r.RET20<-8: s-=6; risk.append("20日动量明显偏弱")

    s=max(0,min(100,round(s)))
    return s,"、".join(why),risk

def classify(x,s):
    r=x.iloc[-1]
    ma_trend=bool(pd.notna(r.close) and pd.notna(r.MA20) and pd.notna(r.MA60) and r.close>r.MA20>r.MA60)
    macd_ok=bool(pd.notna(r.MACD) and pd.notna(r.SIGNAL) and r.MACD>r.SIGNAL)
    rsi_ok=bool(pd.notna(r.RSI) and 48<=r.RSI<=68)
    mom_ok=bool(pd.notna(r.RET20) and r.RET20>0 and pd.notna(r.RET60) and r.RET60>0)
    no_dead=not bool(r.MA_DEAD or r.MACD_DEAD)
    not_overheat=not (pd.notna(r.RSI) and r.RSI>72)
    strong=ma_trend and macd_ok and rsi_ok and mom_ok and no_dead and not_overheat and s>=82
    add=ma_trend and macd_ok and pd.notna(r.RSI) and 45<=r.RSI<=65 and pd.notna(r.RET60) and r.RET60>0 and no_dead and s>=75
    if strong: return "🟢 强买入", "趋势+MACD+RSI+20/60日动量同时确认"
    if add: return "🟡 回调加仓", "中期趋势未坏，适合等待回调分批"
    if s>=70: return "🔵 观察", "技术面偏强，但尚未达到严格买入门槛"
    if s>=55: return "⚪ 持有/等待", "趋势一般，等待更多确认"
    if s>=45: return "🟠 减仓/观望", "技术面偏弱或风险上升"
    return "🔴 高风险/回避", "多项指标未通过"

def load_items():
    p=ROOT/"fund_codes.csv"
    if not p.exists(): return BUILTIN_FUNDS.copy()
    try:
        d=pd.read_csv(p,dtype=str); cc=next((c for c in d.columns if c.lower() in ("code","代码")),None); nc=next((c for c in d.columns if c.lower() in ("name","名称")),None)
        if not cc: return BUILTIN_FUNDS.copy()
        out=[]
        for _,row in d.iterrows():
            c=str(row[cc]).strip()
            if c and c.lower()!="nan": out.append((c,str(row[nc]).strip() if nc else c))
        return out or BUILTIN_FUNDS.copy()
    except: return BUILTIN_FUNDS.copy()

def get_data(code):
    code=str(code).strip()
    if re.fullmatch(r"\d{6}",code):
        return (etf_hist(code),"东方财富ETF K线") if code in ETF_CODES else (fund_hist(code),"东方财富历史净值")
    return yahoo_hist(code),"Yahoo Finance"

@st.cache_data(ttl=300, show_spinner=False)
def process_one(code,name):
    out={"代码":code,"名称":name,"状态":"失败","错误":""}
    try:
        d,source=get_data(code)
        if len(d)<30: raise RuntimeError("历史数据不足30条")
        x=indicators(d); r=x.iloc[-1]; s,why,risk=score(x); latest=float(r.close); pct=float((r.close/x.close.iloc[-2]-1)*100)
        try:
            rt=etf_rt(code) if code in ETF_CODES else fund_rt(code) if re.fullmatch(r"\d{6}",code) else None
        except: rt=None
        if rt and pd.notna(rt.get("price")):
            latest=float(rt["price"]); pct=float(rt["pct"]) if pd.notna(rt.get("pct")) else pct
        level,level_reason=classify(x,s)
        out.update({"状态":"正常","数据源":source,"实时通道":rt.get("channel", "天天基金") if rt else "历史数据", "最新值":round(latest,4),"涨跌%":round(pct,2),"评分":s,"买入等级":level,"等级说明":level_reason,"RSI":round(float(r.RSI),2) if pd.notna(r.RSI) else np.nan,"MA5/20":"金叉" if bool(r.MA_GOLDEN) else ("多头" if r.MA5>r.MA20 else "空头"),"MACD":"金叉" if bool(r.MACD_GOLDEN) else ("多头" if r.MACD>r.SIGNAL else "空头"),"MA20趋势":"向上" if pd.notna(r.MA20_SLOPE) and r.MA20_SLOPE>0 else "向下","20日动量%":round(float(r.RET20),2) if pd.notna(r.RET20) else np.nan,"60日动量%":round(float(r.RET60),2) if pd.notna(r.RET60) else np.nan,"回撤%":round(float(r.DD),2) if pd.notna(r.DD) else np.nan,"布林位置%":round(float(r.BB_POS),2) if pd.notna(r.BB_POS) else np.nan,"年化波动%":round(float(r.VOL),2) if pd.notna(r.VOL) else np.nan,"建议":level,"共振理由":why,"风险提示":"、".join(risk) if risk else "暂无明显风险"})
    except Exception as e: out["错误"]=str(e)
    return out

@st.cache_data(ttl=21600,show_spinner=False)
def macro_one(n,c):
    try:
        d=yahoo_hist(c) if c in ("QQQ","VOO") else (etf_hist(c) if c in ETF_CODES else fund_hist(c)); x=indicators(d); s,_,_=score(x)
        return {"名称":n,"评分":s,"建议":"多头" if s>=70 else ("中性" if s>=50 else "偏弱")}
    except Exception as e:
        return {"名称":n,"评分":np.nan,"建议":"数据失败","错误":str(e)}

@st.cache_data(ttl=21600,show_spinner=False)
def macro_snapshot():
    with ThreadPoolExecutor(max_workers=6) as ex:
        return pd.DataFrame(list(ex.map(lambda kv: macro_one(*kv), MACRO.items())))

def channel_probe():
    """从当前部署服务器实测主要数据通道；用于排查云端网络/接口波动。"""
    tests=[
        ("东方财富 ETF K线", "https://push2his.eastmoney.com/api/qt/stock/kline/get", {"secid":"1.510300","fields1":"f1,f2,f3,f4,f5,f6","fields2":"f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61","klt":"101","fqt":"1","beg":"0","end":"20500101","lmt":"60"}),
        ("东方财富 ETF实时", "https://push2.eastmoney.com/api/qt/stock/get", {"secid":"1.510300","fields":"f43,f58,f169,f170"}),
        ("天天基金估值", "https://fundgz.1234567.com.cn/js/001549.js", {"rt":int(time.time()*1000)}),
        ("东方财富基金历史", "https://fund.eastmoney.com/pingzhongdata/001549.js", {"v":int(time.time()*1000)}),
        ("腾讯 ETF实时", "https://qt.gtimg.cn/q=sh510300", None),
        ("新浪 ETF实时", "https://hq.sinajs.cn/list=sh510300", None),
        ("Yahoo ETF历史", "https://query1.finance.yahoo.com/v8/finance/chart/510300.SS", {"period1":int(time.time())-90*86400,"period2":int(time.time()),"interval":"1d"}),
    ]
    out=[]
    for name,url,params in tests:
        t=time.time()
        try:
            r=http_get(url,params,timeout=6)
            ok=len(r.content)>20
            out.append({"通道":name,"状态":"🟢 通畅" if ok else "🟠 有响应但内容异常","耗时(秒)":round(time.time()-t,2),"HTTP":r.status_code,"返回字节":len(r.content),"错误":""})
        except Exception as e:
            out.append({"通道":name,"状态":"🔴 失败","耗时(秒)":round(time.time()-t,2),"HTTP":"-","返回字节":0,"错误":str(e)[:160]})
    return pd.DataFrame(out)

with st.sidebar:
    st.header("📡 V9.2 · 153只基金 · 多通道加速版")
    if st.button("🔄 立即刷新全部数据",use_container_width=True): st.cache_data.clear(); st.rerun()
    if st.button("🧪 测试数据通道是否通畅",use_container_width=True):
        st.session_state["channel_probe"]=channel_probe()
    search=st.text_input("搜索代码/名称")
    threshold=st.slider("最低技术评分",0,100,60,5)
    signal=st.selectbox("信号筛选",["全部","🟢 强买入","🟡 回调加仓","🔵 观察","⚪ 持有/等待","🟠 减仓/观望","🔴 高风险/回避","金叉","多头"])
    st.caption("自动刷新：15分钟。历史数据采用多通道：东方财富→F10→腾讯→新浪→Yahoo；实时数据采用东方财富→腾讯→新浪备用。并发8路，历史缓存24小时。")
    if "channel_probe" in st.session_state:
        st.success("通道测试完成：下面主页面会显示详细结果。")
try:
    from streamlit_autorefresh import st_autorefresh; st_autorefresh(interval=900000,key="v91_auto15")
except: pass

items=load_items()
if len(items)<153: items=BUILTIN_FUNDS.copy()
if len({c for c,_ in items}) < 153: items=BUILTIN_FUNDS.copy()
st.title("📡 FundRadar V12 · A股专业资金终端")
if "channel_probe" in st.session_state:
    with st.expander("🧪 最近一次数据通道实测结果",expanded=True):
        st.dataframe(st.session_state["channel_probe"],use_container_width=True,hide_index=True)
st.caption("153只基金 · 多通道加速稳定版：东方财富 / F10 / 腾讯 / 新浪 / Yahoo 多源备用 · 严格多指标共振：趋势 + MACD + RSI + 20/60日动量 + 回撤 + 波动率 · 买入信号采用硬性门槛")


# ===================== V11 专业行情终端 =====================
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.markdown("""<style>
.stApp {background-color:#080d13;color:#e2e8f0}
[data-testid="stMetric"] {background:#101b27;border:1px solid #22354a;border-radius:8px;padding:12px}
[data-testid="stMetricLabel"] {color:#9ab1c8}
h1,h2,h3 {color:#e4edf9!important}
[data-testid="stSidebar"] {background:#0d1722}
</style>""",unsafe_allow_html=True)

INDEXES={"上证指数":"1.000001","深证成指":"0.399001","创业板指":"0.399006","沪深300":"1.000300","科创50":"1.000688","中证2000":"1.932000"}

def _num(x,scale=1):
    try:
        v=float(x)
        return v/scale if math.isfinite(v) else np.nan
    except: return np.nan

@st.cache_data(ttl=180,show_spinner=False)
def terminal_indices():
    result=[]
    for name,secid in INDEXES.items():
        try:
            r=http_get('https://push2.eastmoney.com/api/qt/stock/get',{'secid':secid,'fields':'f43,f57,f58,f169,f170,f47,f48','ut':'fa5fd1943c7b386f172d6893dbfba10b'},timeout=5).json().get('data') or {}
            if not r or r.get('f43') in (None,'-'): continue
            result.append({'指数':name,'点位':_num(r.get('f43'),100),'涨跌%':_num(r.get('f170'),100),'成交额(亿)':_num(r.get('f48'),1e8),'来源':'东方财富实时接口'})
        except Exception: pass
    return pd.DataFrame(result)

@st.cache_data(ttl=300,show_spinner=False)
def terminal_market():
    """逐页拉取A股个股快照。仅成功取得完整页集合时才展示全市场指标。"""
    data=[]; total=None; page=1; size=500
    while page<=20:
        params={'pn':page,'pz':size,'po':1,'np':1,'fltt':2,'invt':2,'fid':'f3','fs':'m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048', 'fields':'f12,f14,f2,f3,f6','ut':'bd1d9ddb04089700cf9c27f6f7426281','_':int(time.time()*1000)}
        try:
            obj=http_get('https://push2.eastmoney.com/api/qt/clist/get',params,timeout=12).json().get('data')
            if not obj or not isinstance(obj.get('diff'),(list,dict)): return pd.DataFrame(), '行情接口未返回有效数据'
            total=int(obj.get('total',0)); batch=obj['diff']; batch=list(batch.values()) if isinstance(batch,dict) else batch
            if not batch: break
            data.extend(batch)
            if len(data)>=total: break
            page+=1
        except Exception as exc: return pd.DataFrame(),f'请求失败：{str(exc)[:90]}'
    if not total or len(data)<total: return pd.DataFrame(),f'仅取得 {len(data)}/{total} 只股票，暂停计算全市场比例，避免误判'
    df=pd.DataFrame(data)
    for c in ('f3','f6'): df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.dropna(subset=['f3','f6']).drop_duplicates(subset=['f12'])
    if len(df)<1000:return pd.DataFrame(),'有效股票数量不足'
    return df,''

@st.cache_data(ttl=600,show_spinner=False)
def terminal_sectors():
    try:
        obj=http_get('https://push2.eastmoney.com/api/qt/clist/get',{'pn':1,'pz':30,'po':1,'np':1,'fltt':2,'invt':2,'fid':'f3','fs':'m:90+t:2','fields':'f12,f14,f3,f6'},timeout=8).json().get('data') or {}
        items=obj.get('diff') or []
        if isinstance(items,dict):items=list(items.values())
        return pd.DataFrame([{'板块':x.get('f14'),'涨跌%':_num(x.get('f3')),'成交额(亿)':_num(x.get('f6'),1e8)} for x in items])
    except Exception:return pd.DataFrame()

st.subheader('🖥️ 专业行情全景终端')
st.caption('黑底终端 · 指数多屏 · 市场宽广度 · TRIN成交额代理指标 · 板块轮动。行情接口可能延迟或受云端限制；未获取到的数据明确显示缺失。')
ix=terminal_indices()
if not ix.empty:
    cs=st.columns(3)
    for i,(_,r) in enumerate(ix.iterrows()):
        cs[i%3].metric(r['指数'],f"{r['点位']:,.2f}",f"{r['涨跌%']:+.2f}%" if pd.notna(r['涨跌%']) else None)
else:st.warning('指数实时接口当前不可用，未使用模拟价格。')

with st.expander('📊 查看指数行情表',expanded=False):
    if not ix.empty:st.dataframe(ix,use_container_width=True,hide_index=True)

st.markdown('#### 市场宽广度 × 资金成交结构')
fetch_breadth=st.toggle('获取全市场股票快照（约需数秒；缓存5分钟）',value=False,key='v11_market_toggle')
if fetch_breadth:
    with st.spinner('逐页获取市场股票数据，检查是否完整……'):
        mk,err=terminal_market()
    if err:st.warning(err)
    elif not mk.empty:
        up=mk[mk.f3>0];dn=mk[mk.f3<0];flat=mk[mk.f3==0]
        nup,ndn,nflat=len(up),len(dn),len(flat)
        tv_up,tv_dn=up.f6.sum(),dn.f6.sum()
        breadth=nup/len(mk)*100
        ad=nup/ndn if ndn else np.nan
        turnover_ratio=tv_up/tv_dn if tv_dn>0 else np.nan
        trin=ad/turnover_ratio if pd.notna(ad) and pd.notna(turnover_ratio) and turnover_ratio>0 else np.nan
        st.session_state['v11_latest']={'时间':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'上涨家数':nup,'下跌家数':ndn,'平盘家数':nflat,'上涨占比%':round(breadth,2),'涨跌家数比':round(ad,3),'上涨成交额(亿)':round(tv_up/1e8,2),'下跌成交额(亿)':round(tv_dn/1e8,2),'成交额比':round(turnover_ratio,3),'TRIN_成交额代理':round(trin,3)}
        metrics=st.columns(5)
        metrics[0].metric('上涨家数',f'{nup:,}')
        metrics[1].metric('下跌家数',f'{ndn:,}')
        metrics[2].metric('上涨占比',f'{breadth:.1f}%')
        metrics[3].metric('上涨/下跌家数',f'{ad:.2f}×')
        metrics[4].metric('TRIN成交额代理',f'{trin:.2f}' if pd.notna(trin) else '—')
        a,b=st.columns(2)
        with a:
            fig=go.Figure(go.Bar(x=['上涨股票','下跌股票'],y=[tv_up/1e8,tv_dn/1e8],marker_color=['#e65b5b','#20b78a'],text=[f'{tv_up/1e8:.0f}亿',f'{tv_dn/1e8:.0f}亿'],textposition='auto'))
            fig.update_layout(title='涨跌股票成交额（亿元）',template='plotly_dark',paper_bgcolor='#080d13',plot_bgcolor='#0e1722',height=310)
            st.plotly_chart(fig,use_container_width=True)
        with b:
            fig=go.Figure(go.Pie(labels=['上涨','下跌','平盘'],values=[nup,ndn,nflat],hole=.62,marker_colors=['#e65b5b','#20b78a','#64748b']))
            fig.update_layout(title='上涨/下跌/平盘家数占比',template='plotly_dark',paper_bgcolor='#080d13',height=310)
            st.plotly_chart(fig,use_container_width=True)
        if pd.notna(trin):
            if breadth>=65 and trin>1.2:st.warning('⚠️ 广度较强但TRIN成交额代理偏高：上涨家数优势未获得同比例的成交额支持，留意量价背离。')
            elif breadth>=60 and trin<=1:st.success('上涨家数较多，且成交额分布与广度大体匹配；仍需观察后续持续性。')
            elif breadth<40:st.warning('上涨家数占比不足40%，市场宽广度偏弱。')
            else:st.info('市场处于混合状态；结合指数走势和连续交易日变化判断。')
        st.caption('TRIN成交额代理 = (上涨家数/下跌家数) ÷ (上涨股票成交额/下跌股票成交额)。传统TRIN常采用成交量；这里明确使用成交额，不能与成交量口径直接混用。成交额不等于资金净流入，不能单凭它断言主力出货。')
        st.caption('统计范围为接口筛选出的沪深京A股；剔除无法获得有效涨跌幅或成交额的证券。停牌、新股及不同数据平台的分类规则可能造成差异。')

st.markdown('#### 📈 历史TRIN与宽广度曲线')
st.caption('上传自行保存的日度数据CSV后可绘制真实历史曲线；不自动补造缺失的涨跌方向成交额。')
with st.expander('上传历史数据CSV / 查看绘图要求',expanded=False):
    st.code('日期,上涨家数,下跌家数,平盘家数,上涨成交额,下跌成交额\n2026-09-21,4536,936,81,14952,5531',language='text')
    st.caption('示例中的成交额数字仅用于说明CSV格式，不代表2026-09-21已核验的数据。两种成交额必须使用同一单位。')
    hist_file=st.file_uploader('上传CSV（UTF-8）',type=['csv'],key='v11_hist_csv')
    if hist_file:
        try:
            h=pd.read_csv(hist_file)
            req=['日期','上涨家数','下跌家数','平盘家数','上涨成交额','下跌成交额']
            if any(c not in h.columns for c in req):raise ValueError('缺少必要列：'+','.join(c for c in req if c not in h.columns))
            for c in req[1:]:h[c]=pd.to_numeric(h[c],errors='coerce')
            h['日期']=pd.to_datetime(h['日期'],errors='coerce')
            h=h.dropna(subset=req).sort_values('日期')
            h=h[(h['上涨家数']>0)&(h['下跌家数']>0)&(h['上涨成交额']>0)&(h['下跌成交额']>0)]
            if h.empty:raise ValueError('没有有效的历史数据行')
            h['上涨占比%']=h['上涨家数']/(h['上涨家数']+h['下跌家数']+h['平盘家数'])*100
            h['TRIN']= (h['上涨家数']/h['下跌家数'])/(h['上涨成交额']/h['下跌成交额'])
            fig=make_subplots(specs=[[{'secondary_y':True}]])
            fig.add_trace(go.Scatter(x=h['日期'],y=h['上涨占比%'],name='上涨占比%',line_color='#f59e0b'),secondary_y=False)
            fig.add_trace(go.Scatter(x=h['日期'],y=h['TRIN'],name='TRIN成交额代理',line_color='#60a5fa'),secondary_y=True)
            fig.add_hline(y=1,line_dash='dash',line_color='#94a3b8',secondary_y=True)
            fig.update_layout(template='plotly_dark',paper_bgcolor='#080d13',plot_bgcolor='#0e1722',height=400)
            fig.update_yaxes(title_text='上涨占比%',secondary_y=False)
            fig.update_yaxes(title_text='TRIN',secondary_y=True)
            st.plotly_chart(fig,use_container_width=True)
            st.dataframe(h[['日期','上涨占比%','TRIN']],hide_index=True,use_container_width=True)
        except Exception as e:st.error(f'历史CSV解析失败：{e}')

if 'v11_latest' in st.session_state:
    record=pd.DataFrame([st.session_state['v11_latest']])
    st.download_button('⬇️ 导出本次市场快照CSV',record.to_csv(index=False).encode('utf-8-sig'),file_name='A股市场宽广度快照.csv',mime='text/csv')

st.markdown('#### 🔥 行业板块轮动')
sectors=terminal_sectors()
if not sectors.empty:
    st.dataframe(sectors,hide_index=True,use_container_width=True)
    st.caption('板块涨跌幅与成交额仅用于观察强弱，不等同于板块资金净流入。')
else:st.info('板块行情接口暂不可用。')
st.divider()
# ===================== V11 终端结束 =====================

st.subheader("🌍 大环境 / QQQ / VOO")
mc=st.columns(6)
try:
    md=macro_snapshot()
    for col,(_,row) in zip(mc,md.iterrows()): col.metric(row["名称"],"—" if pd.isna(row["评分"]) else int(row["评分"]),row["建议"])
except: pass

# ===================== 市场宽广度 / Arms(TRIN) / 量价资金系统 =====================
st.subheader("🧭 全市场宽广度 · Arms(TRIN) · 量价资金背离")
st.caption("说明：以下 2026-09-21/22 的关键数字来自你提供的视频/文字，作为案例输入展示；未提供的字段不会自动编造。实时全市场统计接口需要在云端验证后才能作为自动数据使用。")
with st.expander("📐 指标公式与案例演算（展开查看）", expanded=True):
    st.markdown("""
**1）市场宽广度（上涨比例）** = 上涨家数 ÷（上涨 + 下跌 + 平盘家数）× 100%

**2）涨跌家数比（A/D）** = 上涨家数 ÷ 下跌家数

**3）上涨/下跌成交额比（U/D Volume）** = 上涨股票成交额 ÷ 下跌股票成交额

**4）阿姆斯指标 Arms / TRIN** =（上涨家数 ÷ 下跌家数）÷（上涨股票成交额 ÷ 下跌股票成交额）。**TRIN 大于 1** 表示下跌股票相对成交额偏重；小于 1 表示上涨股票相对成交额更有量能支持。单日值容易波动，必须结合宽广度趋势、指数位置和连续多日数据判断。
""")

st.markdown("**案例 A｜2026-09-21（按你提供的数据计算）**")
c1,c2,c3,c4=st.columns(4)
adv_pct=c1.number_input("上涨股票占比 %",min_value=0.0,max_value=100.0,value=80.0,step=0.1,key="br_adv_pct")
dec_pct=c2.number_input("下跌股票占比 %",min_value=0.0,max_value=100.0,value=17.6,step=0.1,key="br_dec_pct")
down_turn=c3.number_input("下跌股票成交额占比 %",min_value=0.0,max_value=100.0,value=27.0,step=0.1,key="br_down_turn")
flat_pct=max(0.0,100.0-adv_pct-dec_pct)
up_turn=100.0-down_turn
if adv_pct>0 and dec_pct>0 and down_turn>0 and down_turn<100:
    ad_ratio=adv_pct/dec_pct
    vol_ratio=up_turn/down_turn
    trin=ad_ratio/vol_ratio
    cc1,cc2,cc3,cc4=st.columns(4)
    cc1.metric("上涨占比",f"{adv_pct:.1f}%")
    cc2.metric("涨跌家数比 A/D",f"{ad_ratio:.2f}:1")
    cc3.metric("涨跌成交额比 U/D",f"{vol_ratio:.2f}:1")
    cc4.metric("计算 Arms / TRIN",f"{trin:.2f}","量能相对偏弱" if trin>1 else "量能相对支持")
    st.info(f"平盘占比约 {flat_pct:.1f}%；上涨成交额占比按剩余值估算为 {up_turn:.1f}%。按这些输入计算，TRIN={ad_ratio:.2f}÷{vol_ratio:.2f}={trin:.2f}，与您提到的 1.69 基本一致（差异来自输入值四舍五入）。")

st.markdown("**案例 B｜2026-09-22（按你提供的数据）**")
b1,b2,b3=st.columns(3)
adv_next=b1.number_input("次日上涨股票占比 %",min_value=0.0,max_value=100.0,value=43.7,step=0.1,key="br_next_adv")
dec_next=b2.number_input("次日下跌股票占比 %（未提供时请填入）",min_value=0.0,max_value=100.0,value=0.0,step=0.1,key="br_next_dec")
trin_next=b3.number_input("次日 Arms/TRIN（未提供时填 0）",min_value=0.0,max_value=10.0,value=0.0,step=0.01,key="br_next_trin")
if dec_next>0:
    st.metric("次日涨跌家数比 A/D",f"{adv_next/dec_next:.2f}:1")
else:
    st.caption("次日下跌占比未提供，因此不计算次日 A/D 或 TRIN，避免把未知数当成事实。")

# Visuals: keep separate scales to avoid misleading overlays.
chart_df=pd.DataFrame({"日期":["09-21","09-22"],"上涨股票占比(%)":[adv_pct,adv_next]}).set_index("日期")
st.markdown("**图 1｜市场宽广度：上涨股票占比**")
st.line_chart(chart_df, y="上涨股票占比(%)", use_container_width=True)
vol_df=pd.DataFrame({"类别":["上涨股票成交额占比","下跌股票成交额占比"],"占比(%)":[up_turn,down_turn]}).set_index("类别")
st.markdown("**图 2｜09-21 成交额分布（由你提供的 27% 下跌成交额推算）**")
st.bar_chart(vol_df, y="占比(%)", use_container_width=True)
trin_df=pd.DataFrame({"日期":["09-21","09-22"],"Arms/TRIN":[round(trin,2) if adv_pct>0 and dec_pct>0 and 0<down_turn<100 else None, trin_next if trin_next>0 else None]}).set_index("日期")
st.markdown("**图 3｜Arms/TRIN（空白表示没有足够数据，不代表 0）**")
st.line_chart(trin_df, y="Arms/TRIN", use_container_width=True)

st.markdown("**量价/资金解读（案例假设，不是对真实历史行情的独立核验）**")
st.markdown(f"""
- 09-21：上涨占比 {adv_pct:.1f}%，下跌占比 {dec_pct:.1f}%，下跌股票成交额占比 {down_turn:.1f}%。按比例推算，上涨/下跌家数比为 **{(adv_pct/dec_pct if dec_pct else 0):.2f}**，上涨/下跌成交额比为 **{(up_turn/down_turn if down_turn else 0):.2f}**，TRIN 约 **{(trin if adv_pct>0 and dec_pct>0 and 0<down_turn<100 else float('nan')):.2f}**。
- 这意味着上涨股票数量明显占优，但下跌股票以较少家数承载了相对较高的成交额；若同时出现指数上涨乏力、权重股放量走弱，属于**广度强、成交额结构不均衡的风险提示**，可以称为潜在量价/资金背离，不能单凭 TRIN 就断言“权重正在出货”。
- 09-22：你提供的上涨占比从 80% 降至 43.7%，下降 **{adv_pct-adv_next:.1f} 个百分点**。这是广度急剧恶化的信号；但要验证“权重松手导致市场转弱”，还需要当天指数涨跌、上涨/下跌成交额、主要权重股成交额和涨跌家数完整数据。
- **操作规则建议**：TRIN > 1 且宽广度连续回落、指数跌破短期趋势时提高风险等级；TRIN < 1 且上涨占比扩张、指数/成交额同步走强时，量价确认较好。用 3–5 日滚动均值过滤单日噪声，不能把单一阈值当成买卖指令。
""")

# ===================== 公开来源历史行情核验 =====================
st.subheader("🗂️ A股近期历史行情：公开数据核验与量价论证")
st.caption("以下为公开网页报道的历史快照，不是实时行情。不同网站的统计范围（是否含北交所、ST、停牌股）可能不同；同一组前后比较优先采用同一来源。公开报道未给出涨跌股票分方向成交额时，不计算 TRIN。")
market_records = [
    {"日期":"2026-09-21", "上涨家数":4536, "下跌家数":936, "平盘家数":81, "成交额(亿元)":20483, "上证涨跌幅(%)":0.97, "来源":"东方财富号复盘", "url":"https://caifuhao.eastmoney.com/news/20260921154815097111860"},
    {"日期":"2026-10-20", "上涨家数":3778, "下跌家数":1666, "平盘家数":None, "成交额(亿元)":14561.1, "上证涨跌幅(%)":0.12, "来源":"连板网日度归档", "url":"https://lianbanwang.com/days/2026-10-20.html"},
    {"日期":"2026-10-21", "上涨家数":1981, "下跌家数":3364, "平盘家数":None, "成交额(亿元)":14293.5, "上证涨跌幅(%)":-0.60, "来源":"连板网日度归档", "url":"https://lianbanwang.com/days/2026-10-21.html"},
]
market_df = pd.DataFrame(market_records)
market_df["上涨占比(%)"] = (market_df["上涨家数"]/(market_df["上涨家数"]+market_df["下跌家数"]+market_df["平盘家数"].fillna(0))*100).round(2)
market_df["涨跌家数比"] = (market_df["上涨家数"]/market_df["下跌家数"]).round(2)
show_df = market_df[["日期","上涨家数","下跌家数","平盘家数","上涨占比(%)","涨跌家数比","成交额(亿元)","上证涨跌幅(%)","来源"]]
st.dataframe(show_df, use_container_width=True, hide_index=True)
st.markdown("**公开来源：** [2026-09-21复盘（东方财富号）](https://caifuhao.eastmoney.com/news/20260921154815097111860) · [2026-10-20行情归档](https://lianbanwang.com/days/2026-10-20.html) · [2026-10-21行情归档](https://lianbanwang.com/days/2026-10-21.html) · [TRIN公式说明（Fidelity）](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/trin)")
trend = market_df[market_df["日期"].isin(["2026-10-20","2026-10-21"])].copy().set_index("日期")
if not trend.empty:
    st.markdown("**图 4｜近期上涨/下跌家数：普涨修复后是否快速转弱**")
    st.line_chart(trend[["上涨家数","下跌家数"]], use_container_width=True)
    st.markdown("**图 5｜市场成交额与上证指数涨跌幅（不同单位分开显示）**")
    cvol, cidx = st.columns(2)
    cvol.bar_chart(trend[["成交额(亿元)"]], use_container_width=True)
    cidx.bar_chart(trend[["上证涨跌幅(%)"]], use_container_width=True)
    if len(trend) == 2:
        first, last = trend.iloc[0], trend.iloc[1]
        adv_change = int(last["上涨家数"] - first["上涨家数"])
        dec_change = int(last["下跌家数"] - first["下跌家数"])
        breadth_first = float(first["上涨占比(%)"])
        breadth_last = float(last["上涨占比(%)"])
        turnover_change = float(last["成交额(亿元)"] - first["成交额(亿元)"])
        st.markdown(f"""**自动论证｜2026-10-20 → 2026-10-21**
- 上涨家数变化：**{adv_change:+,}**；下跌家数变化：**{dec_change:+,}**。
- 上涨占比从 **{breadth_first:.1f}%** 降到 **{breadth_last:.1f}%**，变化 **{breadth_last-breadth_first:+.1f} 个百分点**。
- 两市成交额变化约 **{turnover_change:+,.1f} 亿元**，而上证指数从 **{first['上证涨跌幅(%)']:+.2f}%** 转为 **{last['上证涨跌幅(%)']:+.2f}%**。

**解读：** 这组数据支持“10月20日普涨修复、10月21日广度明显恶化”的判断；成交额只是小幅下降，说明广度转弱并非单纯由成交额骤降造成。它本身不能证明权重股出货。若要确认阿姆斯/TRIN，必须取得同一统计范围下上涨股票成交额总和与下跌股票成交额总和；当前公开摘要没有这两项拆分，所以本模块不伪造 TRIN。""")
st.caption("统计口径提示：2026-09-21来源报告上涨4536、下跌936、平盘81；另一公开归档对沪深剔除北交所采用不同家数。为避免混用口径，本表将来源差异保留为来源注记。2026-10-20/21用于相邻交易日比较。")

from relative_value import render as render_relative_value
render_relative_value()

st.subheader("🔥 今日决策中心")
bar=st.progress(0,f"正在获取{len(items)}只基金数据……"); rows=[]
with ThreadPoolExecutor(max_workers=8) as ex:
    fs=[ex.submit(process_one,c,n) for c,n in items]
    for i,f in enumerate(as_completed(fs),1):
        try: rows.append(f.result())
        except Exception as e: rows.append({"代码":"?","名称":"未知","状态":"失败","错误":str(e)})
        bar.progress(i/max(1,len(fs)),f"正在获取 {i} / {len(fs)}")
bar.empty()
df=pd.DataFrame(rows)
if df.empty: st.error("没有读取到任何基金数据。")
else:
    ok=df[df["状态"]=="正常"].copy(); view=ok.copy()
    if search:
        q=search.lower().strip(); view=view[view.apply(lambda r:q in str(r["代码"]).lower() or q in str(r["名称"]).lower(),axis=1)]
    if signal!="全部":
        if signal=="金叉": view=view[(view["MA5/20"]=="金叉")|(view["MACD"]=="金叉")]
        elif signal=="多头": view=view[(view["MA5/20"].isin(["金叉","多头"]))&(view["MACD"].isin(["金叉","多头"]))]
        else: view=view[view["买入等级"]==signal]
    view=view.sort_values(["评分","20日动量%"],ascending=False)
    strong=ok[ok["买入等级"]=="🟢 强买入"]
    add=ok[ok["买入等级"]=="🟡 回调加仓"]
    watch=ok[ok["买入等级"]=="🔵 观察"]
    a,b,c,d,e,f=st.columns(6)
    a.metric("监控品种",len(items)); b.metric("数据正常",len(ok)); c.metric("🟢 强买入",len(strong)); d.metric("🟡 回调加仓",len(add)); e.metric("🔵 观察",len(watch)); f.metric("数据失败",len(df)-len(ok))

    # 顶部两个快捷入口：点击后只看真正严格信号
    q1,q2,q3=st.columns(3)
    with q1:
        if st.button(f"🟢 强买入（{len(strong)}）",use_container_width=True):
            st.session_state["quick_filter"]="🟢 强买入"
    with q2:
        if st.button(f"🟡 回调加仓（{len(add)}）",use_container_width=True):
            st.session_state["quick_filter"]="🟡 回调加仓"
    with q3:
        if st.button(f"🔵 观察（{len(watch)}）",use_container_width=True):
            st.session_state["quick_filter"]="🔵 观察"
    qf=st.session_state.get("quick_filter")
    if qf:
        st.info(f"当前快捷查看：{qf} · 下面只显示这一类基金")
        view=ok[ok["买入等级"]==qf].sort_values(["评分","20日动量%"],ascending=False)

    cols=["代码","名称","最新值","涨跌%","评分","买入等级","RSI","MA5/20","MACD","MA20趋势","20日动量%","60日动量%","回撤%","年化波动%","等级说明","风险提示"]
    st.dataframe(view[view["评分"]>=threshold][[c for c in cols if c in view.columns]],use_container_width=True,hide_index=True,column_config={"评分":st.column_config.ProgressColumn("技术评分",min_value=0,max_value=100,format="%d")})

with st.expander("📡 数据通道说明 / 本轮实际使用通道"):
    st.markdown("**历史：** 东方财富 pingzhongdata / F10 JSON / F10 HTML；ETF额外启用东方财富K线双节点、腾讯K线、新浪K线、Yahoo。\n\n**实时：** 开放式基金优先天天基金，失败后腾讯基金兜底；ETF优先东方财富，失败后腾讯、再新浪。\n\n**加速：** 153只基金并发提升到8路；历史数据缓存24小时，实时数据缓存3–5分钟。")
    if not df.empty and "实时通道" in df.columns:
        st.dataframe(df["实时通道"].value_counts().rename_axis("通道").reset_index(name="数量"),use_container_width=True,hide_index=True)

with st.expander(f"⚠️ 数据源诊断（失败 {len(df[df['状态']!='正常']) if not df.empty else 0} 个）"):
    bad=df[df["状态"]!="正常"] if not df.empty else pd.DataFrame()
    if not bad.empty: st.dataframe(bad[["代码","名称","错误"]],use_container_width=True,hide_index=True)
    else: st.success("本轮153只基金全部成功获取。")
st.caption(f"V11 专业终端 · 内置153只基金 · 历史缓存24小时 / 实时缓存3-5分钟 · 最后刷新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · 信号仅作辅助，不构成投资建议")

