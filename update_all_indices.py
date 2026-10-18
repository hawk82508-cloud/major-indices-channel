import os
import re
import sys
import json
import datetime
import requests
import pandas as pd
import numpy as np

INDEX_CONFIGS = {
    'TAIEX': {
        'yahoo_symbol': '%5ETWII',
        'stooq_symbol': '^twi',
        'cnbc_symbol': None,
        'is_twse': True,
        'tz_offset_hours': 8,
        'weekly_friday_label': False
    },
    'DJI': {
        'yahoo_symbol': '%5EDJI',
        'stooq_symbol': '^dji',
        'cnbc_symbol': '.DJI',
        'is_twse': False,
        'tz_offset_hours': -4,
        'weekly_friday_label': True
    },
    'NASDAQ': {
        'yahoo_symbol': '%5EIXIC',
        'stooq_symbol': '^ndq',
        'cnbc_symbol': '.IXIC',
        'is_twse': False,
        'tz_offset_hours': -4,
        'weekly_friday_label': True
    },
    'SOX': {
        'yahoo_symbol': '%5ESOX',
        'stooq_symbol': '^sox',
        'cnbc_symbol': '.SOX',
        'is_twse': False,
        'tz_offset_hours': -4,
        'weekly_friday_label': True
    }
}

HTML_FILES = [
    'index.html',
    '各大指數高低控統整_多週期與跨週期前瞻雙軌通道分析系統.html'
]

def fetch_recent_bars(sym, cfg):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    bars = []

    # Engine 1: Yahoo Finance Global CDN (query1 & query2 fallback)
    for host in ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']:
        try:
            y_url = f"https://{host}/v8/finance/chart/{cfg['yahoo_symbol']}?interval=1d&range=3mo"
            r = requests.get(y_url, headers=headers, timeout=12)
            if r.status_code == 200:
                res = r.json()
                result = res['chart']['result'][0]
                timestamps = result.get('timestamp', [])
                quote = result['indicators']['quote'][0]
                gmtoffset = result.get('meta', {}).get('gmtoffset', cfg['tz_offset_hours'] * 3600)
                tz_info = datetime.timezone(datetime.timedelta(seconds=gmtoffset))

                for i in range(len(timestamps)):
                    c = quote['close'][i]
                    o = quote['open'][i]
                    h = quote['high'][i]
                    l = quote['low'][i]
                    v = quote.get('volume', [0])[i] if quote.get('volume') else 0
                    if c is not None and o is not None and h is not None and l is not None and not np.isnan(c):
                        d_dt = datetime.datetime.fromtimestamp(timestamps[i], tz=tz_info).date()
                        d_str = d_dt.strftime('%Y-%m-%d')
                        vol_val = round(float(v) / 100000000.0, 2) if v else 0.0
                        bars.append({
                            '時間': d_str,
                            '開盤價': round(float(o), 2),
                            '最高價': round(float(h), 2),
                            '最低價': round(float(l), 2),
                            '收盤價': round(float(c), 2),
                            '成交量': vol_val
                        })
                if bars:
                    print(f"[{sym}] Yahoo Finance ({host}): retrieved {len(bars)} recent bars, latest={bars[-1]['時間']} Close={bars[-1]['收盤價']}")
                    return bars
        except Exception as e:
            print(f"[{sym}] Yahoo Finance ({host}) Notice: {e}")

    # Engine 2: Stooq International Financial Data Feed
    try:
        s_url = f"https://stooq.com/q/d/l/?s={cfg['stooq_symbol']}&i=d"
        r = requests.get(s_url, headers=headers, timeout=12)
        if r.status_code == 200 and 'Date' in r.text:
            lines = [line.strip() for line in r.text.strip().split('\n') if line.strip()]
            for line in lines[1:][-60:]:
                parts = line.split(',')
                if len(parts) >= 5:
                    d_str = parts[0]
                    o, h, l, c = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                    v = float(parts[5]) if len(parts) > 5 and parts[5] != '' else 0.0
                    bars.append({
                        '時間': d_str,
                        '開盤價': round(o, 2),
                        '最高價': round(h, 2),
                        '最低價': round(l, 2),
                        '收盤價': round(c, 2),
                        '成交量': round(v / 100000000.0, 2) if v > 0 else 0.0
                    })
            if bars:
                print(f"[{sym}] Stooq: retrieved {len(bars)} recent bars, latest={bars[-1]['時間']} Close={bars[-1]['收盤價']}")
                return bars
    except Exception as e:
        print(f"[{sym}] Stooq Notice: {e}")

    # Engine 3: TWSE or CNBC Fallback
    if cfg.get('is_twse'):
        try:
            tz_taipei = datetime.timezone(datetime.timedelta(hours=8))
            today_dt = datetime.datetime.now(tz=tz_taipei).date()
            today_str = today_dt.strftime('%Y%m%d')
            twse_url = f"https://www.twse.com.tw/exchangeReport/FMTQIK?response=json&date={today_str}"
            r = requests.get(twse_url, headers=headers, timeout=12)
            if r.status_code == 200:
                data = r.json()
                if 'data' in data and len(data['data']) > 0:
                    last_row = data['data'][-1]
                    close_p = float(str(last_row[4]).replace(',', ''))
                    amt_val = float(str(last_row[2]).replace(',', '')) / 100000000.0
                    bars.append({
                        '時間': today_dt.strftime('%Y-%m-%d'),
                        '開盤價': close_p,
                        '最高價': close_p,
                        '最低價': close_p,
                        '收盤價': close_p,
                        '成交量': round(amt_val, 2)
                    })
                    return bars
        except Exception as e:
            print(f"[{sym}] TWSE Notice: {e}")
    elif cfg.get('cnbc_symbol'):
        try:
            cnbc_url = f"https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols={cfg['cnbc_symbol']}&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1"
            r = requests.get(cnbc_url, headers=headers, timeout=12)
            if r.status_code == 200:
                q = r.json()['FormattedQuoteResult']['FormattedQuote'][0]
                c = float(str(q['last']).replace(',', ''))
                o = float(str(q.get('open', c)).replace(',', ''))
                h = float(str(q.get('high', c)).replace(',', ''))
                l = float(str(q.get('low', c)).replace(',', ''))
                tz_ny = datetime.timezone(datetime.timedelta(hours=-4))
                d_str = datetime.datetime.now(tz=tz_ny).date().strftime('%Y-%m-%d')
                bars.append({
                    '時間': d_str,
                    '開盤價': round(o, 2),
                    '最高價': round(h, 2),
                    '最低價': round(l, 2),
                    '收盤價': round(c, 2),
                    '成交量': 0.0
                })
                return bars
        except Exception as e:
            print(f"[{sym}] CNBC Notice: {e}")

    return bars

def update_single_index_csvs(sym, cfg):
    data_dir = os.path.join('data', sym)
    daily_csv = os.path.join(data_dir, 'raw_daily.csv')
    weekly_csv = os.path.join(data_dir, 'raw_weekly.csv')
    monthly_csv = os.path.join(data_dir, 'raw_monthly.csv')

    if not os.path.exists(daily_csv):
        return

    recent_bars = fetch_recent_bars(sym, cfg)
    if not recent_bars:
        print(f"[{sym}] Notice: No live network data retrieved; calculating with existing CSV.")
        return

    daily_df = pd.read_csv(daily_csv)
    weekly_df = pd.read_csv(weekly_csv) if os.path.exists(weekly_csv) else None
    monthly_df = pd.read_csv(monthly_csv) if os.path.exists(monthly_csv) else None

    last_existing_date = str(daily_df.iloc[-1]['時間'])
    new_or_curr_bars = [b for b in recent_bars if str(b['時間']) >= last_existing_date]

    for bar in new_or_curr_bars:
        target_date = str(bar['時間'])
        if target_date not in daily_df['時間'].astype(str).values:
            prev_close = float(daily_df.iloc[-1]['收盤價'])
            chg = round(bar['收盤價'] - prev_close, 2)
            pct = round((chg / prev_close) * 100.0, 2) if prev_close else 0.0
            row_to_add = dict(bar)
            if '漲跌' in daily_df.columns:
                row_to_add['漲跌'] = chg
                row_to_add['漲跌幅'] = pct
            daily_df = pd.concat([daily_df, pd.DataFrame([row_to_add])], ignore_index=True)
            print(f"[{sym}] Appended new daily bar: {target_date} Close={bar['收盤價']} ({chg:+.2f}, {pct:+.2f}%)")
        else:
            idx = daily_df[daily_df['時間'].astype(str) == target_date].index[0]
            prev_close = float(daily_df.iloc[idx - 1]['收盤價']) if idx > 0 else float(bar['開盤價'])
            daily_df.at[idx, '開盤價'] = bar['開盤價']
            daily_df.at[idx, '最高價'] = max(float(daily_df.at[idx, '最高價']), float(bar['最高價']))
            daily_df.at[idx, '最低價'] = min(float(daily_df.at[idx, '最低價']), float(bar['最低價']))
            daily_df.at[idx, '收盤價'] = bar['收盤價']
            if '漲跌' in daily_df.columns:
                chg = round(float(bar['收盤價']) - prev_close, 2)
                pct = round((chg / prev_close) * 100.0, 2) if prev_close else 0.0
                daily_df.at[idx, '漲跌'] = chg
                daily_df.at[idx, '漲跌幅'] = pct
            if bar.get('成交量', 0) > 0 and '成交量' in daily_df.columns:
                daily_df.at[idx, '成交量'] = bar['成交量']

        # Update Weekly CSV
        if weekly_df is not None:
            target_dt = datetime.datetime.strptime(target_date, '%Y-%m-%d').date()
            mon_dt = target_dt - datetime.timedelta(days=target_dt.weekday())
            fri_dt = mon_dt + datetime.timedelta(days=4)
            w_label_str = fri_dt.strftime('%Y-%m-%d') if cfg['weekly_friday_label'] else mon_dt.strftime('%Y-%m-%d')

            matched_w_idx = None
            for w_idx, r in weekly_df.iterrows():
                r_dt = datetime.datetime.strptime(str(r['時間']), '%Y-%m-%d').date()
                r_mon = r_dt - datetime.timedelta(days=r_dt.weekday())
                if r_mon == mon_dt:
                    matched_w_idx = w_idx
                    break

            if matched_w_idx is None:
                prev_w_close = float(weekly_df.iloc[-1]['收盤價'])
                chg = round(bar['收盤價'] - prev_w_close, 2)
                pct = round((chg / prev_w_close) * 100.0, 2) if prev_w_close else 0.0
                w_row = {
                    '時間': w_label_str,
                    '開盤價': bar['開盤價'],
                    '最高價': bar['最高價'],
                    '最低價': bar['最低價'],
                    '收盤價': bar['收盤價'],
                    '成交量': bar.get('成交量', 0.0)
                }
                if '漲跌' in weekly_df.columns:
                    w_row['漲跌'] = chg
                    w_row['漲跌幅'] = pct
                weekly_df = pd.concat([weekly_df, pd.DataFrame([w_row])], ignore_index=True)
            else:
                prev_w_close = float(weekly_df.iloc[matched_w_idx - 1]['收盤價']) if matched_w_idx > 0 else float(weekly_df.at[matched_w_idx, '開盤價'])
                weekly_df.at[matched_w_idx, '最高價'] = max(float(weekly_df.at[matched_w_idx, '最高價']), float(bar['最高價']))
                weekly_df.at[matched_w_idx, '最低價'] = min(float(weekly_df.at[matched_w_idx, '最低價']), float(bar['最低價']))
                weekly_df.at[matched_w_idx, '收盤價'] = bar['收盤價']
                if '漲跌' in weekly_df.columns:
                    chg = round(float(bar['收盤價']) - prev_w_close, 2)
                    pct = round((chg / prev_w_close) * 100.0, 2) if prev_w_close else 0.0
                    weekly_df.at[matched_w_idx, '漲跌'] = chg
                    weekly_df.at[matched_w_idx, '漲跌幅'] = pct

        # Update Monthly CSV
        if monthly_df is not None:
            ym_str = target_date[:7]
            m_matches = monthly_df[monthly_df['時間'].astype(str).str.startswith(ym_str)].index
            if len(m_matches) > 0:
                m_idx = m_matches[0]
                prev_m_close = float(monthly_df.iloc[m_idx - 1]['收盤價']) if m_idx > 0 else float(monthly_df.at[m_idx, '開盤價'])
                monthly_df.at[m_idx, '最高價'] = max(float(monthly_df.at[m_idx, '最高價']), float(bar['最高價']))
                monthly_df.at[m_idx, '最低價'] = min(float(monthly_df.at[m_idx, '最低價']), float(bar['最低價']))
                monthly_df.at[m_idx, '收盤價'] = bar['收盤價']
                if '漲跌' in monthly_df.columns:
                    chg = round(float(bar['收盤價']) - prev_m_close, 2)
                    pct = round((chg / prev_m_close) * 100.0, 2) if prev_m_close else 0.0
                    monthly_df.at[m_idx, '漲跌'] = chg
                    monthly_df.at[m_idx, '漲跌幅'] = pct
            else:
                prev_m_close = float(monthly_df.iloc[-1]['收盤價'])
                chg = round(bar['收盤價'] - prev_m_close, 2)
                pct = round((chg / prev_m_close) * 100.0, 2) if prev_m_close else 0.0
                m_row = {
                    '時間': f"{ym_str}-01",
                    '開盤價': bar['開盤價'],
                    '最高價': bar['最高價'],
                    '最低價': bar['最低價'],
                    '收盤價': bar['收盤價'],
                    '成交量': bar.get('成交量', 0.0)
                }
                if '漲跌' in monthly_df.columns:
                    m_row['漲跌'] = chg
                    m_row['漲跌幅'] = pct
                monthly_df = pd.concat([monthly_df, pd.DataFrame([m_row])], ignore_index=True)

    daily_df.to_csv(daily_csv, index=False)
    if weekly_df is not None:
        weekly_df.to_csv(weekly_csv, index=False)
    if monthly_df is not None:
        monthly_df.to_csv(monthly_csv, index=False)

def build_single_payload(sym):
    data_dir = os.path.join('data', sym)
    daily_df = pd.read_csv(os.path.join(data_dir, 'raw_daily.csv'))
    weekly_df = pd.read_csv(os.path.join(data_dir, 'raw_weekly.csv'))
    monthly_df = pd.read_csv(os.path.join(data_dir, 'raw_monthly.csv'))

    for df in [daily_df, weekly_df, monthly_df]:
        df['high_12'] = df['最高價'].rolling(12).max().round(2)
        df['low_12'] = df['最低價'].rolling(12).min().round(2)
        df['point1'] = ((df['high_12'] * 2 + df['low_12']) / 3.0).round(2)
        df['point2'] = ((df['high_12'] + df['low_12'] * 2) / 3.0).round(2)

    weekly_lookup = []
    for idx, r in weekly_df.iterrows():
        w_dt = datetime.datetime.strptime(str(r['時間']), '%Y-%m-%d').date()
        mon_dt = w_dt - datetime.timedelta(days=w_dt.weekday())
        weekly_lookup.append({
            'start_date': mon_dt.strftime('%Y-%m-%d'),
            'high_12': float(r['high_12']) if not pd.isna(r['high_12']) else None,
            'low_12': float(r['low_12']) if not pd.isna(r['low_12']) else None,
            'point1': float(r['point1']) if not pd.isna(r['point1']) else None,
            'point2': float(r['point2']) if not pd.isna(r['point2']) else None
        })

    monthly_lookup = []
    for idx, r in monthly_df.iterrows():
        monthly_lookup.append({
            'ym': str(r['時間'])[:7],
            'start_date': str(r['時間']),
            'high_12': float(r['high_12']) if not pd.isna(r['high_12']) else None,
            'low_12': float(r['low_12']) if not pd.isna(r['low_12']) else None,
            'point1': float(r['point1']) if not pd.isna(r['point1']) else None,
            'point2': float(r['point2']) if not pd.isna(r['point2']) else None
        })

    def get_weekly_point(date_str):
        matched = None
        for w in weekly_lookup:
            if date_str >= w['start_date']:
                matched = w
            else:
                break
        if matched:
            return matched['point1'], matched['point2']
        return None, None

    def get_monthly_point(date_str):
        d_ym = date_str[:7]
        matched = None
        for m in monthly_lookup:
            if m['ym'] == d_ym:
                matched = m
                break
            elif date_str >= m['start_date']:
                matched = m
        if matched:
            return matched['point1'], matched['point2']
        return None, None

    daily_list = []
    multi_list = []

    for idx, r in daily_df.iterrows():
        d_str = str(r['時間'])
        p1_d = float(r['point1']) if not pd.isna(r['point1']) else None
        p2_d = float(r['point2']) if not pd.isna(r['point2']) else None
        h12_d = float(r['high_12']) if not pd.isna(r['high_12']) else None
        l12_d = float(r['low_12']) if not pd.isna(r['low_12']) else None

        w_p1, w_p2 = get_weekly_point(d_str)
        m_p1, m_p2 = get_monthly_point(d_str)

        prev_c = float(daily_df.iloc[idx - 1]['收盤價']) if idx > 0 else float(r['開盤價'])
        chg_val = float(r['漲跌']) if '漲跌' in r and not pd.isna(r['漲跌']) else round(float(r['收盤價']) - prev_c, 2)
        chg_pct = float(r['漲跌幅']) if '漲跌幅' in r and not pd.isna(r['漲跌幅']) else (round((chg_val / prev_c) * 100.0, 2) if prev_c else 0.0)

        item_base = {
            'date': d_str,
            'open': float(r['開盤價']),
            'high': float(r['最高價']),
            'low': float(r['最低價']),
            'close': float(r['收盤價']),
            'change': chg_val,
            'change_pct': chg_pct,
            'volume': float(r['成交量']) if '成交量' in r and not pd.isna(r['成交量']) else 0.0,
            'high_12': h12_d,
            'low_12': l12_d,
            'point1': p1_d,
            'point2': p2_d,
            'is_future': False
        }
        daily_list.append(item_base)
        multi_list.append({
            **item_base,
            'w_point1': w_p1,
            'w_point2': w_p2,
            'm_point1': m_p1,
            'm_point2': m_p2
        })

    weekly_list = []
    for idx, r in weekly_df.iterrows():
        prev_c = float(weekly_df.iloc[idx - 1]['收盤價']) if idx > 0 else float(r['開盤價'])
        chg_val = float(r['漲跌']) if '漲跌' in r and not pd.isna(r['漲跌']) else round(float(r['收盤價']) - prev_c, 2)
        chg_pct = float(r['漲跌幅']) if '漲跌幅' in r and not pd.isna(r['漲跌幅']) else (round((chg_val / prev_c) * 100.0, 2) if prev_c else 0.0)
        weekly_list.append({
            'label': str(r['時間']),
            'date': str(r['時間']),
            'open': float(r['開盤價']),
            'high': float(r['最高價']),
            'low': float(r['最低價']),
            'close': float(r['收盤價']),
            'change': chg_val,
            'change_pct': chg_pct,
            'volume': float(r['成交量']) if '成交量' in r and not pd.isna(r['成交量']) else 0.0,
            'high_12': float(r['high_12']) if not pd.isna(r['high_12']) else None,
            'low_12': float(r['low_12']) if not pd.isna(r['low_12']) else None,
            'point1': float(r['point1']) if not pd.isna(r['point1']) else None,
            'point2': float(r['point2']) if not pd.isna(r['point2']) else None,
            'is_future': False
        })

    monthly_list = []
    for idx, r in monthly_df.iterrows():
        prev_c = float(monthly_df.iloc[idx - 1]['收盤價']) if idx > 0 else float(r['開盤價'])
        chg_val = float(r['漲跌']) if '漲跌' in r and not pd.isna(r['漲跌']) else round(float(r['收盤價']) - prev_c, 2)
        chg_pct = float(r['漲跌幅']) if '漲跌幅' in r and not pd.isna(r['漲跌幅']) else (round((chg_val / prev_c) * 100.0, 2) if prev_c else 0.0)
        monthly_list.append({
            'month': str(r['時間'])[:7],
            'date': str(r['時間'])[:7],
            'open': float(r['開盤價']),
            'high': float(r['最高價']),
            'low': float(r['最低價']),
            'close': float(r['收盤價']),
            'change': chg_val,
            'change_pct': chg_pct,
            'volume': float(r['成交量']) if '成交量' in r and not pd.isna(r['成交量']) else 0.0,
            'high_12': float(r['high_12']) if not pd.isna(r['high_12']) else None,
            'low_12': float(r['low_12']) if not pd.isna(r['low_12']) else None,
            'point1': float(r['point1']) if not pd.isna(r['point1']) else None,
            'point2': float(r['point2']) if not pd.isna(r['point2']) else None,
            'is_future': False
        })

    last_11_d = daily_df.tail(11)
    h11_d = round(float(last_11_d['最高價'].max()), 2)
    l11_d = round(float(last_11_d['最低價'].min()), 2)
    p1_d_future = round((h11_d * 2 + l11_d) / 3.0, 2)
    p2_d_future = round((h11_d + l11_d * 2) / 3.0, 2)

    last_date = datetime.datetime.strptime(str(daily_df.iloc[-1]['時間']), '%Y-%m-%d').date()
    next_day = last_date + datetime.timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += datetime.timedelta(days=1)
    next_day_label = f"{next_day.strftime('%Y-%m-%d')} (次日預測)"

    daily_future = {
        'label': next_day_label,
        'date': next_day_label,
        'open': None, 'high': None, 'low': None, 'close': None, 'volume': None,
        'high_12': h11_d,
        'low_12': l11_d,
        'point1': p1_d_future,
        'point2': p2_d_future,
        'is_future': True
    }

    last_11_w = weekly_df.tail(11)
    h11_w = round(float(last_11_w['最高價'].max()), 2)
    l11_w = round(float(last_11_w['最低價'].min()), 2)
    p1_w_future = round((h11_w * 2 + l11_w) / 3.0, 2)
    p2_w_future = round((h11_w + l11_w * 2) / 3.0, 2)

    weekly_future = {
        'label': '次週預測',
        'date': '次週預測',
        'open': None, 'high': None, 'low': None, 'close': None, 'volume': None,
        'high_12': h11_w,
        'low_12': l11_w,
        'point1': p1_w_future,
        'point2': p2_w_future,
        'is_future': True
    }

    last_11_m = monthly_df.tail(11)
    h11_m = round(float(last_11_m['最高價'].max()), 2)
    l11_m = round(float(last_11_m['最低價'].min()), 2)
    p1_m_future = round((h11_m * 2 + l11_m) / 3.0, 2)
    p2_m_future = round((h11_m + l11_m * 2) / 3.0, 2)

    monthly_future = {
        'label': '次月預測',
        'month': '次月預測',
        'date': '次月預測',
        'open': None, 'high': None, 'low': None, 'close': None, 'volume': None,
        'high_12': h11_m,
        'low_12': l11_m,
        'point1': p1_m_future,
        'point2': p2_m_future,
        'is_future': True
    }

    multi_future = {
        'label': f"{next_day.strftime('%Y-%m-%d')} (次期前瞻)",
        'date': f"{next_day.strftime('%Y-%m-%d')} (次期前瞻)",
        'open': None, 'high': None, 'low': None, 'close': None, 'volume': None,
        'high_12': h11_d,
        'low_12': l11_d,
        'point1': p1_d_future,
        'point2': p2_d_future,
        'w_point1': p1_w_future,
        'w_point2': p2_w_future,
        'm_point1': p1_m_future,
        'm_point2': p2_m_future,
        'is_future': True
    }

    return {
        'daily': daily_list,
        'daily_future': daily_future,
        'weekly': weekly_list,
        'weekly_future': weekly_future,
        'monthly': monthly_list,
        'monthly_future': monthly_future,
        'multi': multi_list,
        'multi_future': multi_future
    }

def main():
    all_payloads = {}
    for sym, cfg in INDEX_CONFIGS.items():
        update_single_index_csvs(sym, cfg)
        all_payloads[sym] = build_single_payload(sym)

    payloads_json = json.dumps(all_payloads, ensure_ascii=False)

    for hfile in HTML_FILES:
        if os.path.exists(hfile):
            with open(hfile, 'r', encoding='utf-8') as f:
                html = f.read()
            new_html = re.sub(
                r'const allIndicesPayloads = (\{.*?\});',
                lambda m: f'const allIndicesPayloads = {payloads_json};',
                html,
                flags=re.DOTALL
            )
            with open(hfile, 'w', encoding='utf-8') as f:
                f.write(new_html)
            print(f"Updated {hfile} successfully.")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error in update_all_indices.py: {e}")
        sys.exit(0)
