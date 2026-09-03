# Setup Guide — what you do, in order

Written for someone who has not done this before. Every step says what to click, what
to type, and how to know it worked.

**Read this first:** you do not need to do all of it. Session 0 is free, takes an hour,
and is the most important thing in this document. Everything after it only matters if
Session 0 goes well.

---

## Decisions only you can make

I cannot answer these. They block different parts of the project.

| # | Decision | Why it matters | Blocks |
|---|---|---|---|
| 1 | **Is there a real, qualified person to run the coaching?** Do you hold a lean/CI credential, or have real operational experience you'd stand behind? | The site says "you'll know exactly who you're working with before you pay." That is only honest if it's true | The $2,400 tier. If no, we cut it and this becomes products-only — still a business, just a different one |
| 2 | **Brand name.** "The Lean Desk" is my suggestion. Nothing has been checked | Domain and trademark are unchecked. You could build on a name you cannot keep | Everything public |
| 3 | **Which industry to aim at first.** My read is US trades and home services — plumbing, HVAC, electrical, landscaping | Content gets sharper when it's specific. "Small business" is too broad to be recognizable | Content after day 30 |
| 4 | **Are you willing to hold the line and not build the $349 course** until 15 real conversations say people want it? | This is where most people skip ahead and waste 100 hours | The mid tier |

**You can start Session 0 without answering any of these.**

---

## Session 0 — The only test that matters

**Time: 1 hour · Cost: $0 · Needs: nothing**

Do not set up a single account until you have done this.

The whole business rests on one belief: that small business owners have a costly,
recurring process problem they can see once it is pointed at. This tests that in an
hour, for free.

1. **Pick a business.** Yours, a friend's, a family member's. It needs 5–50 staff and
   work that repeats — a trades company, a clinic, a workshop, a repair shop.
2. **Open the Waste Walk.** It's at `marketing/lead-magnet/waste-walk.md` in this
   project. Read the three rules at the top. They matter more than the worksheet.
3. **Ask the owner for one hour.** Say you're testing a process audit and you'll share
   what you find. That is true.
4. **Run it exactly as written.** Do not skip Step 3 (the letter marking) — that is
   where the surprise usually is.
5. **Finish Step 5.** They should end with one ranked problem and a number.

**How to tell it worked:** the owner says some version of *"I knew that was a problem
but I didn't realize it was costing that much."* If two or three owners say that, you
have a business. If nobody does, stop and tell me — we rethink before you spend money.

**Then tell me what happened.** That single result changes what we build next more
than anything else in this project.

---

## Session 1 — Create the two accounts

**Time: 30 minutes · Cost: $0**

Only do this once Session 0 went well.

### TikTok

1. Go to **tiktok.com** and click **Sign up**. Use an email you control, not a personal
   one you share.
2. Pick a username. Try **theleandesk**. If taken: `leandesk`, `theleandeskco`,
   `leandeskhq`. **Write down which one you got — I need it.**
3. Go to **Profile → ☰ menu (top right) → Settings and privacy → Account**.
4. Tap **Switch to Business Account**. Choose category **Education** or **Business
   Services**. *This is required — Buffer cannot post to a personal account.*
5. Set the bio to exactly:
   > Lean, translated for small business. Fix one process at a time. Free audit ↓
6. Leave the link field empty for now (the website isn't live yet).

### Instagram

1. Go to **instagram.com**, sign up with the **same email**.
2. Use the **same username** you got on TikTok, so people can find you.
3. Go to **Profile → ☰ → Settings → Account type and tools → Switch to professional
   account**. Choose **Business**. Category: **Education**.
4. Instagram will ask to connect a **Facebook Page**. You must do this — it's a
   platform requirement for scheduled posting, not ours. If you have no Facebook Page,
   it will offer to create one. Let it.
5. Bio:
   > **The Lean Desk**
   > Lean, translated for small business.
   > Most of this was written for factories with 1,000 people. You have 11.
   > One process at a time ↓ free 60-min audit

**How to tell it worked:** both accounts say "Business" in settings, and Instagram is
linked to a Facebook Page.

**Send me:** the username you ended up with.

---

## Session 2 — Buffer, the thing that does the posting

**Time: 20 minutes · Cost: check current pricing — roughly $6–15 per channel per month**

Buffer is the tool that actually publishes. TikTok only lets approved partners post
automatically, and Buffer is one. This is why we're not using something free.

1. Go to **buffer.com** and create an account.
2. **Choose a paid plan that includes TikTok.** The free plan will not work for this.
   ⚠️ Check what it costs today — I have not verified current pricing.
3. Click **Channels → Connect a channel**. Connect **TikTok**. Log in and approve.
4. Connect **Instagram**. It will ask for the Facebook Page from Session 1.
5. **Set the timezone.** Go to **Settings → Preferences → Timezone** and choose
   **New York (Eastern Time)**.

   > **Not Jamaica.** Your audience is in the US. Setting it to New York means your
   > posts land at the same time in *their* morning all year, and Buffer handles US
   > daylight saving for you. If you set it to Jamaica, every post would drift an hour
   > later in their day from March to November.

6. **Do one test post by hand.** Post anything simple to each channel from Buffer —
   even a plain image. Watch it appear on TikTok and Instagram.

   > Do not skip this. Most failures in this whole system are a broken connection
   > between Buffer and the platform, and they are far easier to find now than when
   > automation is layered on top.

**Send me:** confirmation that the test posts appeared on both.

---

## Session 3 — Connect it to Claude

**Time: 15 minutes · Cost: $0**

### 3a. Authorize Buffer

1. Open this link: **https://mcp.zapier.com/api/v1/connect-auth/BufferCLIAPI?accountId=4745045**
2. Log in to Buffer if asked, and click **Allow**.

### 3b. Create the two Routines

These run the weekly loop. They must be created in the **claude.ai** website, not here —
Routines made from this session can't reach Notion or Gmail.

1. Go to **claude.ai** and open **Routines** in the sidebar.
2. Click **New Routine**.
3. Open `automations/weekly-routine-setup.md` in this project. It has both Routines
   written out with the exact name, schedule and prompt to paste.
4. Create **Routine 1 (Saturday digest)** — copy the name, schedule `0 14 * * 6`, and
   the whole prompt block. Attach connectors **Notion** and **Gmail**.
5. Create **Routine 2 (Sunday publish)** — schedule `0 1 * * 1`, attach **Notion** and
   **Zapier**. Before saving, fill in your two Buffer channel IDs where the prompt says
   `<FILL IN>`. Find them in Buffer: click a channel, and the ID is in the browser
   address bar.

   > The Sunday Routine's schedule says Monday (`* * 1`). That is correct, not a typo —
   > Sunday 8pm in Jamaica is Monday 1am in UTC, which is what the schedule uses.

**How to tell it worked:** Saturday morning you get an email listing next week's posts.

---

## Session 4 — Before you can collect an email or take a dollar

Do not skip these. They are legal requirements, not polish.

| What | Why | Who |
|---|---|---|
| **Privacy policy on the site** | Legally required *before* you collect one email address | A generator is fine to start; a lawyer is better |
| **Terms + refund policy** | The site promises refunds. That's a contract | You, then ideally a lawyer |
| **Payment processor** | ⚠️ **Stripe does not work in Jamaica.** Use a merchant of record — Lemon Squeezy, Paddle or Gumroad. They also handle US sales tax for you, which is worth the higher fee | You. **Check they pay out to Jamaica before committing** |
| **Email provider** | To send the Waste Walk. ConvertKit or MailerLite, free tier is fine | You |
| **Website hosting** | The site is built and ready. GitHub Pages is free | Ask me — I'll do it |

> **Never** set up a US company just to get a Stripe account. It breaks Stripe's terms,
> and the way it fails is they close the account and hold your money — after you have
> customers.

---

## What I do once you've done the above

Tell me when each session is done and I'll handle the rest:

- Point the site at your real domain, add the favicon and social image
- Connect the signup form to your email provider
- Put your real TikTok/Instagram handles into the site and the posts
- Publish the site
- Fix anything the first week of posting turns up

---

## The honest summary

**Ready now:** 30 posts written, 432 slide images rendered, the website built and
tested, the approval board live in Notion, the Waste Walk ready to use.

**Not ready:** nothing is connected to the outside world yet, and no real person has
been asked whether they'd pay for any of it.

**The single most valuable hour** in this whole document is Session 0, and it costs
nothing. Everything else is machinery for a business that Session 0 tells you whether
you have.
