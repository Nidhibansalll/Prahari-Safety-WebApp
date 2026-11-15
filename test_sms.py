"""Quick SMS check:  python test_sms.py 9876543210"""
import sys, re
from app import app
from sms import send_sms

if len(sys.argv) < 2 or not re.fullmatch(r"\d{10}", sys.argv[1]):
    sys.exit("Usage: python test_sms.py <10-digit-number>")

res = send_sms(app.config, [sys.argv[1]], "Prahari test SMS - SMS alerts are working.")
print(res)
