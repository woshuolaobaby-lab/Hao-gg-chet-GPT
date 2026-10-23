"""股债相对强弱研究模块。仅使用真实获取/上传数据，不使用示意序列。"""
import re, json
import numpy as np
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

@st.cache_data(ttl=21600, show_spinner=False)
def fund_daily(code):
    url=f'https://fund.eastmoney.com/pingzhongdata/{code}.js'
    r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=22)
    r.raise_for_status()
    m=re.search(r'\bData_netWorthTrend\s*=\s*(\[.*?\])\s*;',r.text,re.S)
    if not m: raise ValueError(f'{code} 的公开净值接口未返回可识别数据')
    data=json.loads(m.group(1))
    f=pd.DataFrame(data)
    if not {'x','y'}.issubset(f.columns): raise ValueError('缺少净值字段')
    f['date']=pd.to_datetime(f['x'],unit='ms',utc=True).dt.tz_convert('Asia/Shanghai').dt.normalize().dt.tz_localize(None)
    f['nav']=pd.to_numeric(f['y'],errors='coerce')
    # 日增长率是复权收益近似，已计入分红再投资的影响；无增长率的日期不直接假设零收益
    f['growth']=pd.to_numeric(f.get('equityReturn',pd.Series(index=f.index,dtype=float)),errors='coerce')
    f=f[['date','nav','growth']].dropna(subset=['date','nav']).drop_duplicates('date').sort_values('date')
    return f

def read_csv(upload, name):
    f=pd.read_csv(upload)
    mapping={ '日期':'date','净值日期':'date','date':'date','收盘':'value','收盘价':'value','累计净值':'value','单位净值':'value','净值':'value','value':'value','日增长率':'growth','涨跌幅':'growth','growth':'growth'}
    f=f.rename(columns={k:v for k,v in mapping.items() if k in f.columns})
    if 'date' not in f or ('value' not in f and 'growth' not in f): raise ValueError(f'{name}：CSV须含日期+净值/收盘，或日期+日增长率')
    f['date']=pd.to_datetime(f['date'],errors='coerce')
    if 'value' in f: f['nav']=pd.to_numeric(f['value'],errors='coerce')
    else: f['nav']=np.nan
    if 'growth' in f: f['growth']=pd.to_numeric(f['growth'],errors='coerce')
    else: f['growth']=np.nan
    return f[['date','nav','growth']].dropna(subset=['date']).sort_values('date').drop_duplicates('date')

def wealth(f):
    f=f.copy().set_index('date')
    if f['growth'].notna().sum()>len(f)*.7:
        returns=f['growth']/100
        returns=returns.where(returns.between(-.5,.5))
        if returns.isna().any():
            raise ValueError('日增长率存在缺失，不能将缺失日期当作0收益复利；请上传完整CSV')
        w=(1+returns).cumprod()
        # 保持真实日收益复利；第一日设为1
        w=w/w.iloc[0]
    elif f['nav'].notna().sum()>len(f)*.9:
        w=f['nav']/f['nav'].iloc[0]
    else: raise ValueError('净值与增长率数据均不完整')
    return w.replace([np.inf,-np.inf],np.nan).dropna()

def analyse(a,b,window=756, min_obs=252,low=.15,high=.85):
    x=pd.concat([wealth(a).rename('equity'),wealth(b).rename('bond')],axis=1,join='inner').dropna()
    if len(x)<min_obs+30: raise ValueError('有效重叠交易日不足，至少需要约282天')
    x=x.loc[x.index>=pd.Timestamp('2012-01-01')].copy()
    x[['equity','bond']]=x[['equity','bond']]/x[['equity','bond']].iloc[0]
    x['ratio']=x.equity/x.bond
    # 严格历史窗口：每一天的阈值只由该日及之前的历史确定
    x['q_low']=x.ratio.shift(1).rolling(window,min_periods=min_obs).quantile(low)
    x['q_high']=x.ratio.shift(1).rolling(window,min_periods=min_obs).quantile(high)
    # 将当前比值与此前窗口比较，避免错误地计算窗口末日自身的历史分位。
    history=x.ratio.shift(1).rolling(window,min_periods=min_obs)
    x['past_percentile']=[float((x.ratio.iloc[max(0,i-window):i] <= x.ratio.iloc[i]).mean()) if i>=min_obs else np.nan for i in range(len(x))]
    x['cheap']=x.ratio<=x.q_low
    x['expensive']=x.ratio>=x.q_high
    x['entry']=x.cheap & ~x.cheap.shift(1,fill_value=False)
    x['exit']=x.expensive & ~x.expensive.shift(1,fill_value=False)
    return x

def backtest(x,horizon=60):
    # 前瞻收益仅用于历史评价，绝不作为当日信号输入；去重事件防止相邻日重复计数
    y=x.copy()
    y['forward']=y.equity.shift(-horizon)/y.equity-1
    cutoff=y.index.max()-pd.Timedelta(days=int(horizon*1.65))
    out=[]
    for typ,col in [('低位预警','entry'),('高位预警','exit')]:
        ev=y.loc[y[col]&y.forward.notna()&(y.index<=cutoff),['forward']].copy()
        ev=ev.loc[ev.index.to_series().diff().dt.days.fillna(999)>horizon*1.4]
        out.append({'信号':typ,'独立事件数':len(ev),'后续收益中位数':f'{ev.forward.median():+.1%}' if len(ev) else '样本不足','后续上涨占比':f'{(ev.forward>0).mean():.0%}' if len(ev) else '样本不足'})
    return pd.DataFrame(out)

@st.cache_data(ttl=21600, show_spinner=False)
def public_index_daily(kind):
    """Public AKShare adapters. Failure is explicit, never silently relabel proxy as official."""
    import akshare as ak
    if kind == 'bond':
        f = ak.bond_new_composite_index_cbond(indicator='财富', period='总值')
        source = '中债-新综合指数财富（AKShare公开转接）'
        f = f.rename(columns={'value':'nav'})
    elif kind == 'equity':
        # csi H00300 is the CSI 300 total return index; public Eastmoney availability is not guaranteed
        f = ak.stock_zh_index_daily_em(symbol='csiH00300', start_date='20120101', end_date='20500101')
        source = '沪深300全收益 H00300（东方财富公开行情转接）'
        f = f.rename(columns={'close':'nav'})
    else:
        raise ValueError('不支持的数据类型')
    if f is None or not isinstance(f,pd.DataFrame) or f.empty:
        raise ValueError(f'{source}：公开接口返回空值（可能不支持该指数代码、限流或上游接口改变）')
    if not {'date','nav'}.issubset(f.columns):
        raise ValueError('公开接口返回列缺失')
    f=f[['date','nav']].copy()
    f['date']=pd.to_datetime(f['date'],errors='coerce').dt.normalize()
    f['nav']=pd.to_numeric(f['nav'],errors='coerce')
    f=f.dropna().drop_duplicates('date').sort_values('date')
    f=f[(f.nav>0)&(f.date>=pd.Timestamp('2012-01-01'))]
    if len(f)<252 or f.date.max()<pd.Timestamp.now().normalize()-pd.Timedelta(days=21):
        raise ValueError(f'{source}：历史数据不足或最后更新日期超过21天（最后日期：{f.date.max() if len(f) else "无"}）')
    return f,source

def render():
    st.subheader('⚖️ V14.1 股债性价比 · 白色稳定版')
    st.info('优先尝试公开接口自动获取两端数据。公开接口并非官方授权SLA服务，若无法获得完整、近期且正确口径的全收益数据，将明确提示或切换标注的基金代理模式。')
    st.caption('数据口径：沪深300全收益 H00300.CSI（不是000300价格指数，也不是000984等权指数）；债券端建议中债综合财富指数。官方历史文件上传后可回测至文件最新日期。')
    with st.expander('数据口径、公式和局限（建议先阅读）',expanded=False):
        st.markdown('**股债比 = 股票资产累计收益净值 ÷ 债券资产累计收益净值**；两者在共同起始日归一为1。低比值表示股票相对债券较弱，**不等于绝对低估**。\n\n公开接口优先使用基金披露的日增长率复利，若增长率缺失则退回净值比值（可能遗漏分红影响）；如需严谨复制原图，请上传官方沪深300全收益及二级债基财富指数CSV。\n\n**阈值为滚动历史分位数，绝不使用未来数据。** 信号在收盘净值公布后才形成，最早次日执行。历史回测仅做事件后的统计，不扣费、不含冲击成本、非真实可交易收益。')
    c1,c2,c3=st.columns([1,1,1])
    with c1: window=st.selectbox('滚动观察窗口',[504,756,1260,2520],index=1,format_func=lambda n:f'{n}个交易日（约{n//252}年）')
    with c2: lo=st.slider('低位分位阈值',5,30,15,5)/100
    with c3: hi=st.slider('高位分位阈值',70,95,85,5)/100
    st.caption('首次访问和缓存到期后自动尝试更新；CSV可覆盖接口结果。数据缓存6小时，更新到数据提供方最新已公布交易日。')
    mode=st.radio('数据模式',['自动模式（官方优先，失败则明确标注基金代理）','严格模式（仅官方数据，不自动降级）','基金代理（备用）'],horizontal=True)
    strict=mode.startswith('严格')
    public=not mode.startswith('基金')
    u1,u2=st.columns(2)
    with u1: eqfile=st.file_uploader('官方沪深300全收益CSV（严格模式）',type='csv',key='v12_eq')
    with u2: bondfile=st.file_uploader('中债财富指数CSV（严格模式）',type='csv',key='v12_bond')
    try:
        with st.spinner('读取股债历史净值（首次可能较慢）...'):
            notes=[]
            if eqfile:
                eq=read_csv(eqfile,'官方沪深300全收益'); notes.append('股票：用户上传CSV（需自行核实指数身份）')
            elif public:
                try:
                    eq,src=public_index_daily('equity'); notes.append('股票：'+src)
                except Exception as err:
                    if strict:
                        st.error(f'沪深300全收益公开接口失败：{err}。严格模式不允许用代理数据替代。')
                        return
                    st.warning(f'沪深300全收益公开接口不可用：{err}。已切换为510300基金代理；该数据不能视为官方沪深300全收益。')
                    eq=fund_daily('510300'); notes.append('股票：510300 ETF代理（非官方全收益）')
            else:
                eq=fund_daily('510300'); notes.append('股票：510300 ETF代理，非官方全收益指数')
            if bondfile:
                bd=read_csv(bondfile,'中债财富指数'); notes.append('债券：用户上传CSV（需自行核实指数身份）')
            elif public:
                try:
                    bd,src=public_index_daily('bond'); notes.append('债券：'+src)
                except Exception as err:
                    if strict:
                        st.error(f'中债财富指数公开接口失败：{err}。严格模式不允许用代理数据替代。')
                        return
                    st.warning(f'中债财富指数公开接口不可用：{err}。已切换为110008基金代理；该数据不能视为官方债券财富指数。')
                    bd=fund_daily('110008'); notes.append('债券：110008二级债基代理（非官方债券指数）')
            else:
                bd=fund_daily('110008'); notes.append('债券：110008二级债基代理，非中债指数')
            st.caption(' | '.join(notes))
            x=analyse(eq,bd,window=window,low=lo,high=hi)
    except Exception as e:
        st.warning(f'真实历史数据未能取得，暂不生成指标或信号：{e}。可上传两份CSV继续使用。')
        return
    last_common=x.index[-1]
    age=(pd.Timestamp.now().normalize()-pd.Timestamp(last_common).normalize()).days
    if age>14:
        st.warning(f'共同数据截至 {last_common.date()}，已滞后 {age} 天。只显示历史研究结果，不应当作为当日买卖信号。')
    else:
        st.success('股债数据已完成读取和对齐。请检查下方来源与共同日期。')
    st.caption('数据来源：'+' | '.join(notes))
    st.caption('股票端最新日期：'+str(eq.date.max().date())+'；债券端最新日期：'+str(bd.date.max().date())+'；共同最新日期：'+str(x.index[-1].date()))
    now=x.iloc[-1]
    a,b,c,d=st.columns(4)
    a.metric('最新股债比',f'{now.ratio:.3f}')
    b.metric('历史滚动分位',f'{now.past_percentile:.0%}' if pd.notna(now.past_percentile) else '数据不足')
    c.metric('最新共同净值日',str(x.index[-1].date()))
    state='低位观察' if now.cheap else '高位风险' if now.expensive else '中性区间'
    d.metric('相对强弱信号',state)
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.09,row_heights=[.60,.40])
    fig.add_trace(go.Scatter(x=x.index,y=x.equity,name='股票端累计收益',line=dict(color='#ff6868',width=1.5)),row=1,col=1)
    fig.add_trace(go.Scatter(x=x.index,y=x.bond,name='债券端累计收益',line=dict(color='#49a7ff',width=1.5)),row=1,col=1)
    fig.add_trace(go.Scatter(x=x.index,y=x.ratio,name='股债比',line=dict(color='#ffc247',width=1.6)),row=2,col=1)
    fig.add_trace(go.Scatter(x=x.index,y=x.q_low,name=f'低位历史{lo:.0%}分位',line=dict(color='#36ce86',dash='dash')),row=2,col=1)
    fig.add_trace(go.Scatter(x=x.index,y=x.q_high,name=f'高位历史{hi:.0%}分位',line=dict(color='#ed6d78',dash='dash')),row=2,col=1)
    for col,color,name in [('entry','#3bd789','低位预警'),('exit','#fa6262','高位预警')]:
        z=x[x[col]]
        fig.add_trace(go.Scatter(x=z.index,y=z.ratio,mode='markers',name=name,marker=dict(size=8,color=color,symbol='circle'),hovertemplate='%{x|%Y-%m-%d}<br>股债比%{y:.3f}<extra></extra>'),row=2,col=1)
    fig.update_layout(template='plotly_white',height=650,margin=dict(l=15,r=15,t=35,b=10),legend=dict(orientation='h',y=1.07),hovermode='x unified')
    fig.update_yaxes(title_text='共同起点=1',row=1,col=1)
    fig.update_yaxes(title_text='股票/债券',row=2,col=1)
    st.plotly_chart(fig,use_container_width=True)
    st.markdown('**严格历史事件检验（仅已发生且已走完观察期的信号）**')
    horizon=st.selectbox('观察后续交易日',[20,60,120],index=1)
    st.dataframe(backtest(x,horizon),use_container_width=True,hide_index=True)
    st.caption('注意：信号是相对强弱分位触发，不是预言市场顶部或底部；样本量少时不能推断胜率。此处不声称截图中的“69%”已被复现。')
    check=pd.Timestamp('2024-09-24')
    if check in x.index:
        row=x.loc[check]
        st.info(f'2024-09-24 核验：股债比 {row.ratio:.3f}，滚动低位阈值 {row.q_low:.3f}，当日低位预警：{"是" if row.cheap else "否"}。此检验基于当前选定的数据模式，不等同于前一张截图的股债利差上轨突破。' if pd.notna(row.q_low) else '2024-09-24：当日滚动历史样本不足。')
    st.download_button('下载全部真实计算结果 CSV',x.reset_index().to_csv(index=False).encode('utf-8-sig'),file_name='FundRadar_V14_1_股债历史核验.csv',mime='text/csv')
