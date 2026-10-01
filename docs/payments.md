# Payments (Stripe)

Online payment uses **Stripe Checkout** (Stripe's hosted, PCI-compliant payment page), so card
details never touch this server.

## Setup
1. Create a Stripe account and copy the **test** keys from https://dashboard.stripe.com/test/apikeys.
2. In `.env`:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   STRIPE_CURRENCY=usd          # match the currency symbol in Customization
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```
3. Webhook - locally with the Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:8000/payments/webhook/
   ```
   (it prints the `whsec_...` secret). In production add an endpoint in the Stripe dashboard pointing
   to `https://your-domain/payments/webhook/` with the events `checkout.session.completed`,
   `checkout.session.async_payment_succeeded` and `charge.refunded`.
4. Test card: `4242 4242 4242 4242`, any future expiry, any CVC.

Without `STRIPE_SECRET_KEY` online payment is simply hidden; admins mark cash/bank payments as paid
from the booking page.

## Flow
1. The traveler books (no payment needed to request a trip) and sees **Pay securely** on the
   confirmation page, in *My bookings* and on their booking page.
2. `POST /payments/checkout/<reference>/` creates a Checkout Session (one line item: tour × travelers
   at the booked unit price, booking reference in the metadata) and redirects to Stripe.
3. Stripe redirects back to `/payments/success/<reference>/?session_id=...`; the server retrieves the
   session from Stripe and, if paid, marks the booking paid.
4. The webhook does the same independently (covers closed tabs and async payment methods).
   `services.mark_paid` is idempotent, so both paths are safe.
5. Admin, guide and traveler get notifications; the admin booking page shows amount, date and a link
   to the payment in the Stripe dashboard.

## Refunds
On a paid booking, **Refund via Stripe** (admin booking page) refunds the full amount and marks the
booking refunded; refunds made directly in the Stripe dashboard are synced through the
`charge.refunded` webhook.

## Security notes
- Only the booking owner (or the guest who just made it, by session) can start a payment.
- The amount is always computed server-side from the booking, never from the browser.
- Webhooks are rejected unless the `Stripe-Signature` header verifies against `STRIPE_WEBHOOK_SECRET`.
- All Stripe calls live in `payments/gateway.py` (easy to mock, easy to swap).
