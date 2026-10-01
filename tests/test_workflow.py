"""Guide accept/decline workflow, schedule, participants, messaging, notifications and Stripe payments."""
import json
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from messaging.models import Message
from notifications.models import Notification
from payments import gateway
from tours.models import Booking, GuideUnavailability, Participant

from .test_app import BaseTestCase

R = Booking.GuideResponse


class WorkflowBase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.booking = Booking.objects.create(
            tour=self.tour, user=self.customer, full_name="Sara Ali", email="sara@example.com", phone="1",
            travel_date=self.future(), travelers=2,
        )


class GuideResponseTests(WorkflowBase):
    def test_booking_inherits_tour_guide(self):
        self.assertEqual(self.booking.guide, self.guide)
        self.assertEqual(self.booking.guide_status, R.PENDING)

    def test_website_booking_notifies_admin_guide_and_customer(self):
        self.client.force_login(self.customer)
        self.client.post(reverse("tours:detail", args=[self.tour.slug]), {
            "book": "1", "full_name": "Sara", "email": "s@x.co", "phone": "1",
            "travel_date": self.future(20).isoformat(), "travelers": 1,
        })
        for user in (self.admin, self.guide, self.customer):
            self.assertTrue(Notification.objects.filter(recipient=user, kind__in=["booking", "guide"]).exists(), user)

    def test_accept_confirms_and_notifies_customer(self):
        self.client.force_login(self.guide)
        self.client.post(reverse("guide:respond", args=[self.booking.pk]), {"action": "accept"})
        self.booking.refresh_from_db()
        self.assertEqual((self.booking.guide_status, self.booking.status), (R.ACCEPTED, "confirmed"))
        note = Notification.objects.get(recipient=self.customer, kind="guide")
        self.assertEqual(note.url, reverse("accounts:booking_detail", args=[self.booking.reference]))

    def test_decline_flags_for_reassignment(self):
        self.client.force_login(self.guide)
        self.client.post(reverse("guide:respond", args=[self.booking.pk]), {"action": "decline", "reason": "Sick"})
        self.booking.refresh_from_db()
        self.assertEqual((self.booking.guide_status, self.booking.guide_decline_reason), (R.DECLINED, "Sick"))
        self.assertTrue(self.booking.needs_guide)
        self.assertTrue(Notification.objects.filter(recipient=self.admin, title__contains="declined").exists())
        # admin sees it under "needs guide"
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("dashboard:bookings"), {"guide": "needs"}), self.booking.reference)

    def test_other_guide_cannot_respond(self):
        self.client.force_login(self.other_guide)
        response = self.client.post(reverse("guide:respond", args=[self.booking.pk]), {"action": "accept"})
        self.assertEqual(response.status_code, 404)

    def test_admin_reassigns_and_new_guide_gets_access(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("dashboard:booking_action", args=[self.booking.pk]), {"action": "assign", "guide": self.other_guide.pk})
        self.booking.refresh_from_db()
        self.assertEqual((self.booking.guide, self.booking.guide_status), (self.other_guide, R.PENDING))
        self.assertTrue(Notification.objects.filter(recipient=self.other_guide).exists())
        self.client.force_login(self.guide)
        self.assertEqual(self.client.get(reverse("guide:booking_detail", args=[self.booking.pk])).status_code, 404)
        self.client.force_login(self.other_guide)
        self.assertEqual(self.client.get(reverse("guide:booking_detail", args=[self.booking.pk])).status_code, 200)

    def test_requests_tab_and_pages(self):
        self.client.force_login(self.guide)
        self.assertContains(self.client.get(reverse("guide:bookings")), self.booking.full_name)
        self.assertContains(self.client.get(reverse("guide:home")), "New trip requests")
        for name in ("calendar", "inbox"):
            self.assertEqual(self.client.get(reverse(f"guide:{name}")).status_code, 200)

    def test_customer_cancel_notifies_guide(self):
        self.client.force_login(self.customer)
        self.client.post(reverse("accounts:cancel_booking", args=[self.booking.reference]))
        self.assertTrue(Notification.objects.filter(recipient=self.guide, title__contains="cancelled").exists())


class ScheduleTests(WorkflowBase):
    def test_time_off_blocks_new_bookings(self):
        self.client.force_login(self.guide)
        start = self.future(30)
        self.client.post(reverse("guide:calendar"), {"start_date": start, "end_date": start + timedelta(days=2), "reason": "Holiday"})
        self.assertTrue(GuideUnavailability.objects.filter(guide=self.guide).exists())
        response = self.client.post(reverse("tours:detail", args=[self.tour.slug]), {
            "book": "1", "full_name": "X", "email": "x@x.co", "phone": "1", "travel_date": start + timedelta(days=1), "travelers": 1,
        })
        self.assertContains(response, "isn&#x27;t available")
        events = self.client.get(reverse("guide:calendar_events")).json()
        self.assertTrue(any(e.get("display") == "background" for e in events))

    def test_time_off_in_past_rejected(self):
        self.client.force_login(self.guide)
        past = timezone.localdate() - timedelta(days=3)
        self.client.post(reverse("guide:calendar"), {"start_date": past, "end_date": past})
        self.assertFalse(GuideUnavailability.objects.exists())


class ParticipantTests(WorkflowBase):
    def post(self, rows):
        data = {"p-TOTAL_FORMS": len(rows), "p-INITIAL_FORMS": 0, "p-MIN_NUM_FORMS": 0, "p-MAX_NUM_FORMS": 1000}
        for i, name in enumerate(rows):
            data[f"p-{i}-full_name"] = name
        return self.client.post(reverse("accounts:booking_detail", args=[self.booking.reference]), data)

    def test_customer_adds_participants_visible_in_manifest(self):
        self.client.force_login(self.customer)
        self.post(["Sara Ali", "Omar Ali"])
        self.assertEqual(Participant.objects.filter(booking=self.booking).count(), 2)
        self.client.force_login(self.guide)
        manifest = reverse("guide:manifest", args=[self.tour.slug, self.booking.travel_date.isoformat()])
        self.assertContains(self.client.get(manifest), "Omar Ali")

    def test_cannot_exceed_travelers(self):
        self.client.force_login(self.customer)
        self.post(["A", "B", "C"])
        self.assertEqual(Participant.objects.count(), 0)

    def test_other_customer_cannot_open_booking(self):
        from django.contrib.auth.models import User
        other = User.objects.create_user("eve", "eve@example.com", "pass12345!")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("accounts:booking_detail", args=[self.booking.reference])).status_code, 404)


class MessagingTests(WorkflowBase):
    def send(self, user, body):
        self.client.force_login(user)
        return self.client.post(reverse("messaging:send", args=[self.booking.reference]), json.dumps({"body": body}),
                                content_type="application/json")

    def test_customer_and_guide_chat(self):
        self.assertEqual(self.send(self.customer, "Hi, where do we meet?").status_code, 200)
        self.assertTrue(Notification.objects.filter(recipient=self.guide, kind="message").exists())
        self.send(self.guide, "Hotel lobby at 7am")
        data = self.client.get(reverse("messaging:poll", args=[self.booking.reference])).json()
        self.assertEqual([m["role"] for m in data["messages"]], ["Traveler", "Guide"])
        self.assertTrue(data["messages"][1]["mine"])
        after = data["messages"][0]["id"]
        newer = self.client.get(reverse("messaging:poll", args=[self.booking.reference]), {"after": after}).json()
        self.assertEqual(len(newer["messages"]), 1)

    def test_admin_can_read_and_reply(self):
        self.send(self.customer, "Question")
        self.assertEqual(self.send(self.admin, "Office here").json()["message"]["role"], "Office")
        self.assertContains(self.client.get(reverse("dashboard:conversations")), self.booking.reference)

    def test_outsiders_blocked(self):
        self.assertEqual(self.send(self.other_guide, "hi").status_code, 404)
        self.client.logout()
        response = self.client.get(reverse("messaging:poll", args=[self.booking.reference]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Message.objects.count(), 0)

    def test_unread_badge(self):
        self.send(self.customer, "Hello")
        self.client.force_login(self.guide)
        self.assertContains(self.client.get(reverse("guide:inbox")), 'class="badge bg-brand')


class NotificationTests(WorkflowBase):
    def test_open_marks_read_and_redirects(self):
        from notifications.services import notify
        note = notify([self.customer], "Hello", url="/tours/")[0]
        note = Notification.objects.get(recipient=self.customer)
        self.client.force_login(self.customer)
        response = self.client.get(reverse("notifications:open", args=[note.pk]))
        self.assertRedirects(response, "/tours/", fetch_redirect_response=False)
        note.refresh_from_db()
        self.assertTrue(note.is_read)

    def test_external_urls_not_followed(self):
        note = Notification.objects.create(recipient=self.customer, title="x", url="https://evil.example/")
        self.client.force_login(self.customer)
        response = self.client.get(reverse("notifications:open", args=[note.pk]))
        self.assertEqual(response.url, reverse("notifications:list"))

    def test_bell_and_list_render_for_each_role(self):
        for user in (self.admin, self.guide, self.customer):
            Notification.objects.create(recipient=user, title="Ping")
            self.client.force_login(user)
            self.assertContains(self.client.get(reverse("notifications:list")), "Ping")


@override_settings(STRIPE_SECRET_KEY="sk_test_123", STRIPE_WEBHOOK_SECRET="whsec_123", STRIPE_CURRENCY="usd")
class StripeTests(WorkflowBase):
    def test_checkout_redirects_to_stripe(self):
        self.client.force_login(self.customer)
        with mock.patch.object(gateway, "create_checkout_session", return_value=("cs_test_1", "https://checkout.stripe.com/c/pay/cs_test_1")) as create:
            response = self.client.post(reverse("payments:checkout", args=[self.booking.reference]))
        self.assertRedirects(response, "https://checkout.stripe.com/c/pay/cs_test_1", fetch_redirect_response=False)
        self.assertIn("{CHECKOUT_SESSION_ID}", create.call_args.args[1])
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.stripe_session_id, "cs_test_1")

    def test_line_item_amounts(self):
        self.assertEqual(gateway.to_minor_units(Decimal("80")), 8000)
        with override_settings(STRIPE_CURRENCY="jpy"):
            self.assertEqual(gateway.to_minor_units(Decimal("8000")), 8000)

    def test_only_owner_can_pay(self):
        self.client.force_login(self.other_guide)
        with mock.patch.object(gateway, "create_checkout_session") as create:
            self.client.post(reverse("payments:checkout", args=[self.booking.reference]))
        create.assert_not_called()

    def test_success_redirect_verifies_and_marks_paid(self):
        self.booking.stripe_session_id = "cs_test_1"
        self.booking.save()
        self.client.force_login(self.customer)
        session = {"id": "cs_test_1", "paid": True, "reference": self.booking.reference, "amount": Decimal("160"), "payment_intent": "pi_1"}
        with mock.patch.object(gateway, "retrieve_session", return_value=session):
            self.client.get(reverse("payments:success", args=[self.booking.reference]), {"session_id": "cs_test_1"})
        self.booking.refresh_from_db()
        self.assertEqual((self.booking.payment_status, self.booking.amount_paid, self.booking.stripe_payment_intent), ("paid", Decimal("160"), "pi_1"))
        self.assertTrue(Notification.objects.filter(recipient=self.guide, kind="payment").exists())

    def test_webhook_marks_paid_once(self):
        event = {"type": "checkout.session.completed", "data": {"object": {
            "client_reference_id": self.booking.reference, "payment_status": "paid", "amount_total": 16000, "payment_intent": "pi_2"}}}
        with mock.patch.object(gateway, "parse_webhook", return_value=event):
            for _ in range(2):
                self.assertEqual(self.client.post(reverse("payments:webhook"), b"{}", content_type="application/json").status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, "paid")
        self.assertEqual(Notification.objects.filter(recipient=self.customer, kind="payment").count(), 1)

    def test_webhook_rejects_bad_signature(self):
        response = self.client.post(reverse("payments:webhook"), b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="bad")
        self.assertEqual(response.status_code, 400)

    def test_admin_refund(self):
        self.booking.payment_status, self.booking.stripe_payment_intent = "paid", "pi_9"
        self.booking.save()
        self.client.force_login(self.admin)
        with mock.patch.object(gateway, "refund") as refund:
            self.client.post(reverse("dashboard:booking_action", args=[self.booking.pk]), {"action": "refund"})
        refund.assert_called_once_with("pi_9")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, "refunded")

    def test_pay_button_shown_to_customer(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("accounts:booking_detail", args=[self.booking.reference]))
        self.assertContains(response, reverse("payments:checkout", args=[self.booking.reference]))
