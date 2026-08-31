# Launch Checklist

> **What "launch" means here.** Not launching the whole ladder. Launching the **free
> tier and the Kit** — which is all the validation plan permits until the gates pass.
> Do not let a launch date pull the course and coaching forward past their gates.

---

## Blocking — cannot go live without these

### Legal and compliance
- [ ] **Privacy policy live** — ⚠️ required *before* collecting a single email address
- [ ] **Terms of service / purchase terms** — refund terms are contractual commitments
- [ ] **Business registration** appropriate to your jurisdiction
- [ ] **Sales tax / VAT / GST on digital products** — jurisdiction-dependent, and a
      real liability. **Ask an accountant.** Not modelled anywhere in this project
- [ ] **Cookie / consent position confirmed** (cookieless analytics makes this simpler,
      not automatically exempt)
- [ ] **Email compliance** — double opt-in, one-click unsubscribe, physical address in
      footer, accurate sender identity
- [ ] **Outreach compliance** for your jurisdiction (GDPR/PECR, CAN-SPAM, CASL)
- [ ] **Professional indemnity insurance** — before any coaching is delivered

### Brand and identity
- [ ] Name decided — **domain and trademark checked.** ⚠️ *Nothing has been checked*
- [ ] Social handles secured
- [ ] Decision recorded: faceless **marketing** vs. fully anonymous
- [ ] If coaching is offered: the named human is real, qualified, and named on the site

### Claims review — do this line by line
- [ ] No testimonials that are not real and permissioned
- [ ] No client logos for non-clients
- [ ] No results, percentages or savings figures that were not measured
- [ ] No "join N+ owners" unless N is true today
- [ ] No fake urgency, scarcity or struck-through prices never charged
- [ ] Illustrative examples labelled **as illustrative**, in the artifact itself
- [ ] The site's "no results yet" section is intact and honest
- [ ] Refund promises match what you will actually honour

> This section is the one most likely to be quietly skipped as launch approaches.
> It is also the one that decides whether this brand is trusted. **Read every page.**

### Technical
- [ ] `example.com` replaced everywhere (canonical, OG, JSON-LD, env)
- [ ] Favicon and OG image added
- [ ] `/privacy.html`, `/terms.html`, `/contact.html` exist — footer links currently 404
- [ ] Form connected to the ESP, **with no key in client-side code**
- [ ] Full opt-in path tested end to end with a real address
- [ ] Domain email authentication: SPF, DKIM, DMARC
- [ ] Checkout live and tested with a real card, then refunded
- [ ] Delivery after purchase tested
- [ ] Purchase → sequence exit tested (buyers must stop being sold the Kit)
- [ ] Reply → sequence pause tested
- [ ] Mobile tested at 320 / 390 / 768 — ✅ *verified during build*
- [ ] Dark mode checked both ways — ✅ *implemented*
- [ ] Keyboard navigation checked — ✅ *skip link, focus states in place*
- [ ] Analytics installed **after** the privacy policy
- [ ] Backups: product files and site in version control ✅, plus an off-repo copy

### Product readiness
- [ ] All nine Kit files complete in three states (blank / filled / how-to)
- [ ] Every filled example labelled as illustrative
- [ ] Files open correctly for someone outside your Google account — **test with a
      second account**; broken "make a copy" links are the most common launch failure
      for this product type
- [ ] Waste Walk PDF and web version both live
- [ ] Someone outside the business has run the Waste Walk and told you where it confused
      them

---

## Framework checklist — status

| Item | Status |
|---|---|
| Idea defined | ✅ `business-plan.md` |
| Customer identified | ✅ `research/ideal-customer-profile.md` |
| Market researched | ✅ `research/market-research.md` |
| Competitors reviewed | ✅ Grouped by what they sell |
| **Demand validated** | ❌ **NOT DONE — this is the gate.** `research/validation-plan.md` |
| Offer created | ✅ `offer/offer.md` |
| Pricing reviewed | ⚠️ Proposed, **unvalidated**; Rung 3 unanchored |
| Product/service built | ⚠️ Specified; Kit files not yet produced |
| Website tested | ✅ Built and verified responsive |
| Mobile tested | ✅ 320 / 390 / 768 |
| Forms tested | ⚠️ Validation works; **not connected** |
| Payments tested | ❌ Not set up |
| Emails tested | ⚠️ Written; not connected |
| Analytics installed | ⚠️ Placeholder only, by design |
| Automations tested | ❌ Designed, not built |
| Privacy / legal reviewed | ❌ **BLOCKING** |
| Claims reviewed | ✅ Written to the honesty rules; re-check before publish |
| Customer support process | ⚠️ "A human answers replies" — define response time |
| Backups | ✅ Version control; add an off-repo copy |
| Launch plan ready | ✅ Below |

---

## Launch sequence

**Week 1 — legal and technical foundations.** Privacy, terms, tax position, domain,
email authentication. Nothing public.

**Week 2 — the free tier.** Site live, Waste Walk delivering, sequence running. Test
the whole path yourself twice.

**Weeks 2–6 — publish and listen.** Weekly content. Start outreach. **Run Test 4's
fifteen conversations.** This is the real work of launch, and it is not glamorous.

**Week 6 — Gate check.** Opt-in rate against 25%. Conversations against the Gate 2
threshold. Write down the decision either way.

**Week 7+ — sell the Kit** (Gate 3), then a single pilot engagement (Gate 4).

**Later — build the course.** Only after Gate 4. It is the largest build in the
project and the most likely to be wasted if the earlier bets are wrong.

---

## Before you launch: the human review

The framework is explicit, and it is right: **a human — you, a co-founder, or an
advisor — must review the research, strategy, pricing, code and legal requirements
before this goes live.** Everything in this project was drafted by an AI working from
one paragraph of intent and a set of public sources.

Specifically, it cannot and did not:
- verify that a single number in the pricing is achievable
- check a domain, a trademark, or a business name
- give you legal, tax or insurance advice
- talk to one real customer
- know whether *you* want to run this business

The register of every decision waiting on a person is in `human-review.md`.
