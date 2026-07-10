# 🚀 SecureDrop Lab

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-Backend-black)
![Architecture](https://img.shields.io/badge/Architecture-MVC-green)

SecureDrop Lab adalah aplikasi backend berbasis Python dan Flask untuk _secure file sharing_ di lingkungan laboratorium kampus. Proyek ini dirancang sebagai solusi internal yang lebih aman dibandingkan berbagi file melalui akun chat pribadi di perangkat publik.

## 🧩 Latar Belakang Masalah

Di banyak lab kampus, dosen atau asisten sering membagikan maupun mengumpulkan file tugas melalui WhatsApp. Praktik ini terlihat sederhana, tetapi menimbulkan risiko serius ketika mahasiswa harus masuk ke **WA Web** pada PC lab atau komputer publik.

Masalah utamanya adalah banyak pengguna lupa melakukan _logout_. Akibatnya, percakapan pribadi, file, dan informasi akun dapat diintip atau disalahgunakan oleh pengguna berikutnya yang memakai PC yang sama. Kondisi ini berbahaya dari sisi privasi dan keamanan data.

SecureDrop Lab hadir sebagai solusi **internal drop-off box** untuk berbagi file secara terkontrol. Sistem ini memisahkan file publik dan privat, mendukung pembagian file ke user tertentu, dan menggunakan autentikasi berbasis token yang disimpan aman di cookie HttpOnly.

## 🏗️ Arsitektur

Proyek ini mengikuti pola **MVC (Model-View-Controller)**:

- **Model**: `models/` berisi representasi data seperti `User`, `FileItem`, dan `FileShare`.
- **View**: `templates/` menyimpan halaman HTML untuk antarmuka pengguna.
- **Controller**: `routes/` menangani logika request, autentikasi, unggah file, dan alur akses data.

Struktur ini membuat kode lebih terpisah, mudah dirawat, dan lebih jelas pembagian tanggung jawabnya.

## 🛠️ Tech Stack

### Backend

- Python
- Flask
- Flask-SQLAlchemy
- Werkzeug
- python-dotenv

### Security / Auth

- Flask-JWT-Extended
- Flask-CORS
- Flask-Mail
- itsdangerous

### Frontend / UI

- HTML
- Tailwind CSS via CDN
- Vanilla JavaScript dengan Fetch API

## ✨ Fitur Utama

- **Secure Authentication**: JWT disimpan di **HttpOnly Cookie** untuk mengurangi risiko pencurian token melalui XSS pada PC publik.
- **Register, Login, Logout, dan Profile Lookup**: User dapat membuat akun, masuk, keluar, dan mengambil data profil aktif melalui `/api/auth/me`.
- **Forgot Password & Reset Password**: User dapat meminta link reset password via email, memverifikasi token reset, lalu mengganti password melalui halaman reset.
- **File Management**: Mendukung unggah file dengan `UUID` untuk nama file penyimpanan, serta metadata seperti `title` dan `description`.
- **Public & Private Visibility**: File dapat diatur sebagai publik agar muncul di _Public Explorer_, atau privat agar hanya dapat diakses pihak tertentu.
- **Targeted M2M Sharing**: File privat dapat dibagikan ke satu atau beberapa user tertentu melalui relasi **many-to-many**.
- **File Detail, Edit, dan Preview**: Owner dapat melihat detail file, memperbarui metadata, mengganti file fisik, dan melakukan preview untuk file gambar.
- **Protected Download**: Akses file privat dibatasi berdasarkan kepemilikan atau status berbagi.

## 🔐 Security Notes

- Token autentikasi tidak disimpan di `localStorage` atau `sessionStorage`.
- Cookie JWT menggunakan konfigurasi `HttpOnly` untuk mengurangi paparan token ke JavaScript.
- Sistem validasi upload membatasi tipe file yang diizinkan.
- Ukuran file maksimum dikendalikan oleh konfigurasi server.
- Reset password menggunakan token bertanda tangan dengan masa berlaku terbatas.

## 🖥️ Halaman UI

Proyek ini menyediakan halaman web berikut:

- `/login`
- `/register`
- `/forgot-password`
- `/reset-password`
- `/dashboard`
- `/explorer`
- `/shared-with-me`

## 🔁 API Flow & Endpoints

Semua endpoint berada di bawah prefix berikut:

- Auth: `/api/auth`
- Files: `/api/files`

### Auth API

| Method | Endpoint | Deskripsi | Keterangan |
|---|---|---|---|
| POST | `/api/auth/register` | Registrasi user baru | Membuat akun dengan `username`, `email`, `password`, dan opsional `full_name` |
| POST | `/api/auth/login` | Login user | Menghasilkan JWT lalu menyimpannya ke cookie HttpOnly (`Set-Cookie`) |
| POST | `/api/auth/logout` | Logout user | Menghapus cookie autentikasi (`Clear Cookie`) |
| GET | `/api/auth/me` | Ambil data user aktif | Mengembalikan profil user dari token yang sedang aktif |
| POST | `/api/auth/forgot-password` | Minta link reset password | Mengirim email reset ke alamat terdaftar |
| POST | `/api/auth/verify-reset-token` | Validasi token reset | Mengecek apakah token reset masih valid sebelum form ditampilkan |
| POST | `/api/auth/reset-password` | Simpan password baru | Memperbarui password user menggunakan token reset |

### Files API

| Method | Endpoint | Deskripsi | Keterangan |
|---|---|---|---|
| POST | `/api/files/upload` | Upload file baru | Menerima file, `title`, `description`, status publik/privat, dan target share |
| GET | `/api/files/public` | Ambil file publik | Menampilkan daftar file yang bisa diakses semua user yang login |
| GET | `/api/files/shared-with-me` | Ambil file yang dibagikan ke user aktif | Mengembalikan daftar file privat yang diterima melalui relasi M2M |
| GET | `/api/files/my-files` | Ambil file milik user aktif | Menampilkan file yang diunggah oleh user login |
| GET | `/api/files/users` | Ambil daftar user untuk sharing | Dipakai frontend untuk memilih target share |
| GET | `/api/files/{file_id}` | Ambil detail file | Owner mendapat detail tambahan seperti daftar user yang di-share |
| PUT/PATCH | `/api/files/{file_id}` | Update file | Memperbarui metadata file dan opsi share, serta opsional mengganti file fisik |
| GET | `/api/files/{file_id}/download` | Unduh file | Mengunduh file sesuai otorisasi akses |
| GET | `/api/files/{file_id}/preview` | Preview file gambar | Menampilkan file gambar secara inline |
| DELETE | `/api/files/{file_id}` | Hapus file | Hanya owner yang dapat menghapus file |

### Alur Singkat

1. User melakukan registrasi atau login.
2. Server mengirim JWT dan menyimpannya di cookie HttpOnly.
3. User dapat mengunggah file sebagai publik atau privat.
4. File publik muncul di _Public Explorer_.
5. File privat hanya muncul untuk owner atau user yang menerima share.
6. Jika user lupa password, ia dapat meminta link reset melalui email.

## 📦 How to Run

### 1. Clone repository

```bash
git clone <URL_REPOSITORY>
cd UAS_BACKEND-main
```

### 2. Buat virtual environment

```bash
python -m venv venv
```

### 3. Aktifkan virtual environment di Windows

```bash
.\venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Buat file `.env`

Buat file `.env` di root project, lalu isi minimal seperti berikut:

```env
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
```

Jika ingin menggunakan fitur reset password via email, tambahkan juga konfigurasi email berikut sesuai provider yang dipakai:

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=465
MAIL_USE_SSL=True
MAIL_USE_TLS=False
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password-or-app-password
MAIL_DEFAULT_SENDER=your-email@example.com
FRONTEND_URL=http://localhost:5000
```

### 6. Jalankan aplikasi

```bash
python app.py
```

Secara default, aplikasi akan berjalan di:

```bash
http://127.0.0.1:5000
```

## 📁 Struktur Proyek

```text
app.py
config.py
readme.md
requirements.txt
models/
routes/
static/
templates/
uploads/
```

## 📌 Catatan Implementasi

- UUID digunakan sebagai identitas utama untuk user dan file.
- File fisik disimpan di folder `uploads/`, sementara metadata disimpan di database.
- Relasi many-to-many untuk berbagi file dikelola melalui tabel asosiasi `FileShare`.
- Endpoint API membutuhkan autentikasi JWT untuk akses data yang sensitif.
- Halaman reset password menggunakan token yang dikirim melalui email dan diverifikasi sebelum user dapat mengganti password.

## ✅ Tujuan Proyek

SecureDrop Lab dibuat untuk menyediakan jalur distribusi file yang lebih aman, lebih terstruktur, dan lebih cocok untuk penggunaan di lingkungan kampus dibandingkan berbagi file melalui akun chat pribadi di perangkat publik.
