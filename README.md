# Dheera Littles

Online store for baby dresses (0 months to 4 years). React + FastAPI + PostgreSQL, run with Docker Compose.
Customers pick a dress and age size, pay by UPI, and track their order. The admin manages products and orders and downloads an Excel sheet.

## Folder structure

```
dheera-littles/
├── docker-compose.yml
├── .env.example          # copy to .env
├── db/init/01-init.sql   # postgres init SQL (runs on first start)
├── frontend/             # React (Vite) + nginx.conf + Dockerfile
├── backend/              # FastAPI + Dockerfile
└── data/uploads, exports # product photos and generated files (mounted volumes)
```

## 1. Prerequisites (Windows 11)

1. Install **Docker Desktop** and start it (WSL 2 backend). Wait until it says "Engine running".
2. Install **Git for Windows**.
3. Check in PowerShell:
   ```powershell
   docker --version
   docker compose version
   git --version
   ```

## 2. First-time setup

Open PowerShell in the project folder:

```powershell
cd path\to\dheera-littles
copy .env.example .env
notepad .env
```

Change at least `POSTGRES_PASSWORD`, `JWT_SECRET` and `ADMIN_PASSWORD`.

## 3. Build the images and start

```powershell
docker compose build
docker compose up -d
docker compose ps
```

Open **http://localhost** in your browser.

| URL | What |
|---|---|
| http://localhost | Shop |
| http://localhost/account | Sign up / log in |
| http://localhost/admin | Admin (log in as `ADMIN_EMAIL` first) |
| http://localhost/api/docs | API docs |

To build and start in one step: `docker compose up -d --build`

## 4. Add your products

1. Log in with the admin email and password from `.env`.
2. Click **Admin**, then **Products**.
3. Enter name, price, description, upload photos, and enter stock for each age size. Click **Add product**.

## 5. Test mode (no keys needed)

- **OTP:** while `SMTP_HOST` is empty, OTPs are printed in the backend log:
  ```powershell
  docker compose logs -f backend
  ```
- **Payment:** while Razorpay keys are empty, clicking "Pay with UPI" simulates a successful payment so you can test the full flow.

## 6. Going live with real UPI and email

1. Create a Razorpay account, complete KYC, and put `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env`.
2. In Razorpay Dashboard, Webhooks: add `https://YOUR_DOMAIN/api/payments/webhook`, select `payment.captured` and `order.paid`, and put the secret in `RAZORPAY_WEBHOOK_SECRET`.
3. Put SMTP details (Gmail app password or AWS SES) in `.env` for email OTPs.
4. Set `COOKIE_SECURE=true` after enabling HTTPS.
5. Apply changes: `docker compose up -d --build`

## 7. Useful Docker commands

```powershell
docker compose logs -f backend      # backend logs
docker compose logs -f frontend     # nginx logs
docker compose restart backend
docker compose down                 # stop (data is kept)
docker compose down -v              # stop AND delete the database (careful)
docker exec -it dheera-db psql -U dheera -d dheera     # open the database
```

Back up the database:
```powershell
docker exec dheera-db pg_dump -U dheera dheera > backup.sql
```

## 8. Git commands

First time (create an empty repository on GitHub first):

```powershell
git init
git add .
git commit -m "Initial commit: Dheera Littles"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/dheera-littles.git
git push -u origin main
```

Daily work:

```powershell
git status
git add .
git commit -m "Describe your change"
git push
```

`.env` and uploaded photos are in `.gitignore`, so secrets are not pushed.

## 9. Deploy on AWS EC2 (next step)

On an Ubuntu EC2 instance: install Docker, `git clone` the repo, create `.env`, run `docker compose up -d --build`.
Open ports 80 and 443 (and 22 from your IP only). Never open 5432. Add a domain and HTTPS (Let's Encrypt) before using real payments. We will do this together once local testing is done.

## Notes

- Orders are stored in PostgreSQL (safe for many orders at once). Admin > Orders > **Download Excel** gives you an `.xlsx` of all paid orders.
- Shipping charge: flat Rs. 60, free above Rs. 999. Change `SHIPPING_FLAT` and `FREE_SHIPPING_ABOVE` in `.env`.
- Tables are created automatically on first backend start.
