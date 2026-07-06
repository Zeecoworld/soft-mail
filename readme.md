# Bulk Sender (Brevo + Netlify)

A tiny tool: paste a list of `email, first name` pairs, write your message once with a
`{{firstname}}` placeholder, and send a personalized batch through Brevo's transactional API.

## 1. Brevo setup (one-time)

1. Log in to your Brevo account.
2. Go to **Senders & IP** → verify the email address you'll send *from* (click the
   verification link Brevo emails you). You can't send until this is done.
3. Go to **SMTP & API** → **API Keys** → create a new key. Copy it — you won't see it again.

## 2. Deploy to Netlify

1. Push this folder to a GitHub repo (or drag-and-drop deploy it directly in the Netlify UI).
2. In Netlify: **Add new site** → connect the repo (build command: none needed, publish
   directory: `.`).
3. Go to **Site configuration** → **Environment variables** → add:
   - `BREVO_API_KEY` = the key you copied above
4. Deploy. Netlify will pick up `netlify/functions/send-batch.js` automatically.

## 3. Using it

1. Open your deployed site.
2. Fill in:
   - **From**: your verified sender name + email
   - **Recipients**: one per line, `email, first name` — e.g. `jane@example.com, Jane`
   - **Subject** and **Message**: use `{{firstname}}` anywhere you want it personalized
3. Hit **Send batch**.

## Daily limit reminder

Brevo's free plan caps at 300 emails/day (resets at midnight, doesn't roll over). For 500
emails, split into two batches — e.g. paste the first 250 in the morning, the remaining 250
in the afternoon. The tool itself doesn't enforce this split; it's on you to paste the right
chunk each time. (If you want, I can add a feature that auto-splits a pasted list of 500 into
two saved batches you trigger separately — just ask.)

## How it works technically

- The frontend posts your list + message to a Netlify serverless function
  (`send-batch.js`).
- That function calls Brevo's `POST /v3/smtp/email` endpoint using `messageVersions` — one
  version per recipient, each with their own rendered subject/body — so it's a single API
  call instead of 500 separate ones, and each person only ever sees their own address in "to".
- Personalization (`{{firstname}}`) is substituted server-side before sending, so it works
  regardless of what Brevo's own template engine supports.