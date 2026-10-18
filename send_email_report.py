import os
import smtplib
import datetime
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header

def send_daily_email(html_path='index.html'):
    sender_email = os.environ.get('GMAIL_USER')
    sender_password = os.environ.get('GMAIL_APP_PASSWORD')

    if not sender_email or not sender_password:
        print("Notice: GMAIL_USER or GMAIL_APP_PASSWORD not set in GitHub Secrets. Skipping email delivery.")
        return

    recipients = ['hawk82508@gmail.com', 'skfg7381@skl.com.tw']
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    today_num = today_str.replace('-', '')

    summary_lines = []
    for sym, label in [
        ('TAIEX', '集中市場加權指數 (TAIEX)'),
        ('DJI', '道瓊工業平均指數 (DJI)'),
        ('NASDAQ', '那斯達克綜合指數 (NASDAQ)'),
        ('SOX', '費城半導體指數 (SOX)')
    ]:
        daily_csv = os.path.join('data', sym, 'raw_daily.csv')
        if os.path.exists(daily_csv):
            try:
                df = pd.read_csv(daily_csv)
                last_row = df.iloc[-1]
                d_str = str(last_row['時間'])
                close_p = float(last_row['收盤價'])
                last_11 = df.tail(11)
                h11 = float(last_11['最高價'].max())
                l11 = float(last_11['最低價'].min())
                p1 = (2 * h11 + l11) / 3.0
                p2 = (h11 + 2 * l11) / 3.0
                summary_lines.append(
                    f"* {label} ({d_str})：收盤 {close_p:,.2f} | 次日上軌(第1點) {p1:,.2f} | 次日下軌(第2點) {p2:,.2f}"
                )
            except Exception as e:
                print(f"Error reading {daily_csv}: {e}")

    summary_block = "\n".join(summary_lines)
    subject = f"【四大指數高低控統整日報】{today_str} TAIEX / DJI / NASDAQ / SOX 跨週期雙軌分析"

    body_text = f"""您好：

這是 {today_str} 各大指數高低控統整系統（TAIEX、DJI、NASDAQ、SOX）的每日盤後技術分析自動推播。

【四大指數最新盤後與次日 11 期前瞻重點】
{summary_block}

【附件檔案說明】
隨信附上整合版獨立離線網頁檔案：Major_Indices_{today_num}_Report.html
下載後直接點擊即可使用 Google Chrome 開啟（首頁展示四大指數跨週期融合走勢圖總覽，頂部可一鍵切換各指數獨立完整頁面）。

本郵件由 GitHub Actions 自動化系統排程發送。
"""

    msg = MIMEMultipart('mixed')
    msg['From'] = f"Major Indices Channel System <{sender_email}>"
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = Header(subject, 'utf-8').encode()
    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

    if os.path.exists(html_path):
        clean_filename = f"Major_Indices_{today_num}_Report.html"
        with open(html_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Type', 'application/octet-stream', name=clean_filename)
        part.add_header('Content-Disposition', 'attachment', filename=clean_filename)
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=20)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()
        print(f"Successfully sent daily email report to {recipients}")
    except Exception as e:
        print(f"Notice: Failed to send email report: {e}")

if __name__ == '__main__':
    send_daily_email()
