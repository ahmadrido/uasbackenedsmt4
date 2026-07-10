import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

email = os.getenv('MAIL_USERNAME')
password = os.getenv('MAIL_PASSWORD')

print("Mencoba menghubungi server Gmail...")
try:
    # Coba koneksi ke port 587
    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
    server.set_debuglevel(1) # Memunculkan log detail
    server.ehlo()
    server.starttls()
    server.login(email, password)
    print("Koneksi SUKSES! Masalah ada di konfigurasi Flask.")
    server.quit()
except Exception as e:
    print(f"Koneksi GAGAL: {e}")
    print("Kesimpulan: OS/Jaringan/Firewall memblokir python.exe ke port SMTP.")