import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
import logging
import ssl
import urllib3
from datetime import datetime
from requests.adapters import HTTPAdapter

# SSL warnings suppress
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ✅ Legacy SSL Fix — same as pehle wala
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

PAGE_URL = "https://castcertificatewb.gov.in/searchapplication/viewcertificatedetails"
API_URL  = "https://castcertificatewb.gov.in/searchcertificate"

USER_AGENTS = [
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def get_session():
    session = requests.Session()
    adapter = LegacySSLAdapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': '*/*',
        'Accept-Language': 'en-IN,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Connection': 'keep-alive',
    })
    return session

def get_csrf_token(session):
    """Page load karke XSRF token aur cookies lo"""
    try:
        resp = session.get(PAGE_URL, verify=False, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Laravel _token (hidden input field mein hota hai)
        csrf = None
        tag = soup.find('input', {'name': '_token'})
        if tag:
            csrf = tag.get('value')

        if not csrf:
            meta = soup.find('meta', {'name': 'csrf-token'})
            if meta:
                csrf = meta.get('content')

        if csrf:
            logger.info(f"✅ CSRF token fetched: {csrf[:20]}...")
        else:
            logger.warning("⚠️  CSRF token HTML mein nahi mila — cookie-based hoga")

        return csrf
    except Exception as e:
        logger.warning(f"CSRF fetch failed: {e}")
        return None

def search_single(session, cert_no, issue_date, csrf_token):
    """
    POST /searchcertificate
    Body: _token=...&hname=WB1502ST201503554&dateofissue=2015-06-02
    """
    try:
        payload = {
            '_token': csrf_token or '',
            'hname': cert_no,
            'dateofissue': issue_date,
        }

        headers = {
            'Referer': PAGE_URL,
            'Origin': 'https://castcertificatewb.gov.in',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'sec-ch-ua-platform': '"Android"',
            'sec-ch-ua-mobile': '?1',
        }

        resp = session.post(
            API_URL,
            data=payload,
            headers=headers,
            verify=False,
            timeout=20
        )

        if resp.status_code != 200:
            return error_result(cert_no, issue_date, f"HTTP_{resp.status_code}")

        # JSON parse
        try:
            data = resp.json()
        except Exception:
            return error_result(cert_no, issue_date, "INVALID_JSON")

        result = {
            'Certificate_No'  : cert_no,
            'Issue_Date_Input': issue_date,
            'Application_ID'  : 'N/A',
            'Applicant_Name'  : 'N/A',
            'Sex'             : 'N/A',
            'Father_Name'     : 'N/A',
            'Address'         : 'N/A',
            'Caste'           : 'N/A',
            'Sub_Caste'       : 'N/A',
            'Issue_Date'      : 'N/A',
            'Is_Valid'        : 'N/A',
            'Issued_By'       : 'N/A',
            'Status'          : 'N/A',
            'Search_Time'     : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        # NOT FOUND check
        if not data.get('status', False):
            result['Status'] = 'NOT_FOUND'
            result['Applicant_Name'] = 'NOT_FOUND'
            return result

        cert_list = data.get('certdetails', [])
        if not cert_list:
            result['Status'] = 'NOT_FOUND'
            result['Applicant_Name'] = 'NOT_FOUND'
            return result

        row = cert_list[0]

        result['Application_ID'] = row.get('applid', 'N/A')
        result['Applicant_Name'] = row.get('appl_name', 'N/A')
        result['Sex']            = row.get('sex', 'N/A')

        # Father/Mother name with co field
        co   = row.get('co', '')
        fname= row.get('father_name', 'N/A')
        result['Father_Name'] = f"{co} {fname}".strip() if co else fname

        result['Address']    = row.get('add', 'N/A')
        result['Caste']      = row.get('casteid', 'N/A')
        result['Sub_Caste']  = row.get('sub_caste_name', 'N/A')
        result['Issue_Date'] = row.get('issuedt', 'N/A')
        result['Is_Valid']   = 'Valid' if row.get('is_valid') == 'Y' else 'Invalid'
        result['Issued_By']  = data.get('issuedby', 'N/A')
        result['Status']     = 'Found'

        return result

    except requests.exceptions.SSLError as e:
        return error_result(cert_no, issue_date, f"SSL: {str(e)[:40]}")
    except requests.exceptions.Timeout:
        return error_result(cert_no, issue_date, "TIMEOUT")
    except Exception as e:
        logger.error(f"Error for {cert_no}: {e}")
        return error_result(cert_no, issue_date, str(e)[:50])

def error_result(cert_no, issue_date, reason):
    return {
        'Certificate_No'  : cert_no,
        'Issue_Date_Input': issue_date,
        'Application_ID'  : 'ERROR',
        'Applicant_Name'  : 'ERROR',
        'Sex'             : 'N/A',
        'Father_Name'     : 'N/A',
        'Address'         : 'N/A',
        'Caste'           : 'N/A',
        'Sub_Caste'       : 'N/A',
        'Issue_Date'      : 'N/A',
        'Is_Valid'        : 'N/A',
        'Issued_By'       : 'N/A',
        'Status'          : f'ERROR: {reason}',
        'Search_Time'     : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

def read_csv(csv_file):
    """
    CSV mein 2 columns hone chahiye:
    - Certificate_No  (ya certno, cert_no, hname)
    - Issue_Date      (ya issuedate, dateofissue, issue_date) — format: YYYY-MM-DD
    """
    try:
        df = pd.read_csv(csv_file)
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

        # Certificate No column dhundo
        cert_col = None
        for c in df.columns:
            if any(x in c for x in ['cert', 'hname', 'certno']):
                cert_col = c
                break
        if not cert_col:
            cert_col = df.columns[0]

        # Issue Date column dhundo
        date_col = None
        for c in df.columns:
            if any(x in c for x in ['date', 'issue', 'dt']):
                date_col = c
                break
        if not date_col:
            date_col = df.columns[1]

        records = []
        for _, row in df.iterrows():
            cert = str(row[cert_col]).strip()
            date = str(row[date_col]).strip()
            if cert and date and cert != 'nan':
                records.append((cert, date))

        logger.info(f"✅ {len(records)} records loaded from {csv_file}")
        logger.info(f"   Cert column: '{cert_col}' | Date column: '{date_col}'")
        return records

    except Exception as e:
        logger.error(f"CSV read error: {e}")
        return []

def search_batch(records, output_file='cert_results.csv'):
    session = get_session()
    csrf_token = get_csrf_token(session)

    results = []
    total = len(records)
    start_time = time.time()

    print("\n" + "="*70)
    print(f"🔍 CERTIFICATE SEARCH — {total} RECORDS")
    print(f"🌐 Endpoint: POST /searchcertificate")
    print("="*70)

    for idx, (cert_no, issue_date) in enumerate(records, 1):
        print(f"\n[{idx}/{total}] Certificate: {cert_no} | Date: {issue_date}")

        # Retry logic — 3 attempts
        result = None
        for attempt in range(1, 4):
            result = search_single(session, cert_no, issue_date, csrf_token)
            if 'ERROR' not in result.get('Status', ''):
                break
            if attempt < 3:
                wait = attempt * 3
                print(f"   ↩️  Retry {attempt}/3 — waiting {wait}s...")
                time.sleep(wait)
                # CSRF refresh karo on retry
                csrf_token = get_csrf_token(session) or csrf_token

        results.append(result)
        status = result.get('Status', '')
        name   = result.get('Applicant_Name', 'N/A')

        if status == 'Found':
            valid = result.get('Is_Valid', '')
            print(f"✅ {name[:35]} | {valid} | Issued by: {result.get('Issued_By','')[:30]}")
        elif 'NOT_FOUND' in status:
            print(f"❌ NOT FOUND")
        else:
            print(f"⚠️  {status[:50]}")

        elapsed   = time.time() - start_time
        avg       = elapsed / idx
        remaining = avg * (total - idx)
        print(f"📊 {idx/total*100:.1f}% | ⏱️  ~{remaining/60:.1f} min remaining")

        # Polite delay
        if idx < total:
            if idx % 40 == 0:
                pause = random.uniform(2, 4)
                print(f"   ☕ Short break ({pause:.1f}s) after {idx} requests...")
                time.sleep(pause)
            else:
                time.sleep(random.uniform(0.4, 1))

    # Save
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        excel_file = output_file.replace('.csv', '.xlsx')
        df.to_excel(excel_file, index=False)

        print("\n" + "="*70)
        print("📊 SUMMARY")
        print("="*70)
        print(f"Total    : {len(results)}")
        print(f"Found    : {len(df[df['Status']=='Found'])}")
        print(f"Not Found: {len(df[df['Status']=='NOT_FOUND'])}")
        print(f"Errors   : {len(df[df['Status'].str.startswith('ERROR', na=False)])}")
        print(f"\n💾 CSV  : {output_file}")
        print(f"💾 Excel: {excel_file}")

def main():
    print("="*70)
    print("🔍 CAST CERTIFICATE VERIFIER")
    print("   POST /searchcertificate | SSL Fixed | Retry Logic")
    print("="*70)
    print("\n📋 CSV format chahiye:")
    print("   Certificate_No    , Issue_Date")
    print("   WB1502ST201503554 , 2015-06-02")
    print("   WB2401ST2022008825, 2022-03-07\n")

    csv_file = input("📁 CSV file name: ").strip() or 'certificates.csv'
    records  = read_csv(csv_file)

    if not records:
        print("❌ No records found! CSV mein Certificate_No aur Issue_Date columns hone chahiye.")
        return

    print(f"\n📋 Records found: {len(records)}")
    for i, (c, d) in enumerate(records[:5], 1):
        print(f"   {i}. {c} | {d}")
    if len(records) > 5:
        print(f"   ... aur {len(records)-5} more")

    output_file = input(f"\n📄 Output file (default: cert_results.csv): ").strip() or 'cert_results.csv'
    confirm     = input("\n🚀 Start search? (y/n): ").strip().lower()

    if confirm == 'y':
        search_batch(records, output_file)
        print("\n🎉 Done!")
    else:
        print("Cancelled.")

if __name__ == "__main__":
    main()
