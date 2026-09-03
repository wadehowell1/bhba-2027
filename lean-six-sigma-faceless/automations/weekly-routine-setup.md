# Weekly Routine Setup

The approve-once-a-week loop needs two scheduled Routines. **You have to create these
yourself, in the claude.ai Routines UI** — the reason is below, and it is not
optional.

Everything else is already built: the Notion board exists, all 30 posts are loaded as
`Draft`, and Buffer is enabled in Zapier.

---

## Why you have to create these, and not me

I created the Sunday Routine from this session and it came back with a warning:

> *this trigger stores no MCP connectors, so the sessions it fires will run without
> connector tools*

Attempting to attach them explicitly returned:

> *the connectors parameter is not available for this organization*

Meaning: a Routine created from inside this session fires a session with **no Notion,
no Gmail, no Zapier** — so it could read nothing and send nothing. It would have fired
every Sunday, failed, and notified you about the failure.

**I deleted it** rather than leave that running. Routines created from the claude.ai
Routines UI *can* have connectors attached, so that is where these belong.

---

## Before you create them

- [ ] **Authorize Buffer in Zapier** — the app is enabled but not connected:
      https://mcp.zapier.com/api/v1/connect-auth/BufferCLIAPI?accountId=4745045
- [ ] Connect your TikTok and Instagram channels **inside Buffer**
- [ ] Publish one manual test post from Buffer to each channel, and confirm it lands
- [ ] Note your Buffer channel IDs (the Zapier action needs them)
- [ ] Set your **Buffer account timezone to America/New_York** — NOT Jamaica. Buffer
      schedules in the account's timezone, and the slots should be fixed in the
      *audience's* clock, not yours. See "Two clocks" below

---

## Timezone and why the days are what they are

### Two clocks, and which governs what

You are in Jamaica. The audience is in the US. These are different clocks and they
govern different things — getting this backwards is the most likely scheduling
mistake here.

| | Clock | Why |
|---|---|---|
| **Post times** (in Buffer) | **US Eastern** — `America/New_York` | The slots must land at the same local moment for the *reader*, every week. Set Buffer to Eastern and it handles US daylight saving for you |
| **Routine times** (the crons) | **Jamaica** — `America/Jamaica` | These only need to run before the first post, with lead time. Anchoring them to Jamaica means they never shift, because Jamaica has no daylight saving |

**Why this matters:** Jamaica is UTC−5 all year. US Eastern is UTC−5 in winter but
**UTC−4 from March to November**. If you set Buffer to Jamaica, your 06:30 slot would
silently become 07:30 Eastern for eight months of the year. Setting Buffer to Eastern
fixes the slot in the reader's clock; your own local time for it just shifts by an
hour twice a year, which costs you nothing.

The Routine crons below are anchored to Jamaica and never need seasonal adjustment.
Both give ample lead time in either season.

**Cron is evaluated in UTC**, so the stored expressions are the local time plus five
hours. Note that the Sunday publish Routine crosses midnight in UTC and therefore
appears as **Monday** in its cron (`* * 1`). That is correct, not a typo.

| Routine | Jamaica | UTC | Cron |
|---|---|---|---|
| Approval digest | **Sat 09:00** | Sat 14:00 | `0 14 * * 6` |
| Publish | **Sun 20:00** | Mon 01:00 | `0 1 * * 1` |

### Why Saturday and Sunday, rather than Sunday and Monday

The first post of the week goes out **Monday 06:30**. A publish step running Monday
morning would be racing the post it is meant to schedule — Buffer needs the item in
its queue well before the slot.

So the week runs:

```
Sat 09:00  digest arrives          ─┐
                                    │  ~35 hours to review and approve
Sun 20:00  publish step runs       ─┘
                                    │  ~10.5 hours of queue lead time
Mon 06:30  first post goes live    ─┘
```

You get a relaxed weekend window to approve, and the queue is loaded the night before
the first post. If you approve late on Sunday, anything approved after 20:00 simply
waits for the following week's run rather than half-posting.

---

## Routine 1 — Saturday approval digest

| Setting | Value |
|---|---|
| Name | `Lean Desk — Saturday approval digest` |
| Schedule | `0 14 * * 6` — **Saturdays 09:00 Jamaica** (14:00 UTC) |
| Mode | New session each run |
| Connectors | **Notion, Gmail** |
| Notifications | Push on |

**Prompt — paste verbatim:**

```
Weekly content-approval step for "The Lean Desk" — a faceless social brand
(TikTok + Instagram) publishing slideshow posts about lean process improvement
for small businesses.

CONTEXT (fresh session — everything needed is here):
- Content calendar in Notion: "The Lean Desk — Content Calendar",
  data source id e3a99878-0bb3-47ad-b3a7-f638468a1405
- Row properties: Post, Day, Status, Pillar, Platform, Publish date, Hook,
  Slides, Caption, Hashtags, CTA, Assets, Notes
- Status values: Draft, Approved, Scheduled, Posted, Skipped
- NOTHING publishes unless a human sets Status to "Approved". Never set Status
  to Approved yourself, under any circumstances, however good the content looks
  or however far behind the calendar is.

TASK:
1. Query the Notion data source for rows with Publish date in the next 7 days.
2. For each: Day number, date, Post title, Status, Hook, Caption, CTA, and
   whether Assets is empty.
3. Send ONE email to wade.howell1@gmail.com via Gmail. Subject:
   "Lean Desk — approve next week's posts (N waiting)" where N = count still in Draft.
   Body: for each post, the day and date, the Hook, the caption, and a flag if
   Assets is empty.
   End with: open the Notion board, edit anything you want changed directly in
   the row, flip Status to Approved for the ones to publish. Anything left as
   Draft will not post.
   Include: https://app.notion.com/p/3cd19c12699d412ea4483bf19c8d3c95
4. Plain and scannable. No hype, no marketing language, no emoji. This is an
   internal working email.

RULES:
- Do not modify any row's Status.
- You may fix an obvious typo in Caption or Slides if confident — note any such
  edit in the email.
- If no posts fall in the next 7 days, email saying the calendar has run out and
  needs the next batch. Do not invent posts yourself.
- If Notion or Gmail is unavailable, say so clearly in the final report rather
  than silently doing nothing.
```

---

## Routine 2 — Sunday publish

| Setting | Value |
|---|---|
| Name | `Lean Desk — Sunday publish approved posts` |
| Schedule | `0 1 * * 1` — **Sundays 20:00 Jamaica** (01:00 UTC Monday) |
| Mode | New session each run |
| Connectors | **Notion, Zapier** |
| Notifications | Push on |

**Prompt — paste verbatim, after filling in the two channel IDs:**

```
Weekly publish step for "The Lean Desk" faceless social brand.

CONTEXT (fresh session — everything needed is here):
- Content calendar in Notion: "The Lean Desk — Content Calendar",
  data source id e3a99878-0bb3-47ad-b3a7-f638468a1405
- Row properties: Post, Day, Status, Pillar, Platform, Publish date, Hook,
  Slides, Caption, Hashtags, CTA, Assets, Notes
- Publishing goes through Buffer, via the Zapier connector. Use the Buffer
  "update" write action to add each post to the Buffer queue.
- Buffer channel IDs — TikTok: <FILL IN>   Instagram: <FILL IN>

TASK:
1. Query Notion for rows where Status = "Approved" AND Publish date is within
   the next 8 days.
2. For each such row, in Publish date order:
   a. Confirm the slide images for that Day actually resolve (fetch the first
      one). If they do not, SKIP the row and report it. Never schedule a post
      with no images.
   b. Build the image list for the row. Do NOT rely on the Assets field being
      filled in — derive the URLs from the Day number, which is always correct:

        https://raw.githubusercontent.com/wadehowell1/bhba-2027/<BRANCH>/lean-six-sigma-faceless/marketing/social/slides/day-<NN>/<PLATFORM>/<SS>.png

      where <BRANCH> is claude/lean-six-sigma-faceless-orhfzg (change to main once
      the pull request is merged), <NN> is the zero-padded Day, <PLATFORM> is
      tiktok or ig, and <SS> is the zero-padded slide number starting at 01.
      The slide count per day is in slides/manifest.json in the same repo.
   c. Create a Buffer update for each platform listed in the row's Platform
      property, using the Caption plus that platform's hashtags from the
      Hashtags field, the derived image list, and the row's Publish date.
      Scheduled times: TikTok 06:30, Instagram 07:00 — these are in the Buffer
      account's timezone, which must be set to America/New_York (US Eastern), so
      they stay fixed in the audience's clock through daylight saving.
   d. On success, set that row's Status to "Scheduled".
3. Report at the end: how many scheduled, how many skipped and why, and any
   failures with the error.

RULES:
- Only ever act on rows whose Status is exactly "Approved". Never publish a
  Draft, and never change a row's Status to Approved yourself for any reason.
- Set Status to "Scheduled" immediately after a successful Buffer call, so a
  re-run cannot double-post.
- If a Buffer call fails, leave the row as "Approved" and report it. Do not
  retry more than once.
- If the Buffer connection is broken or unauthorised, stop and report clearly.
  Do not attempt to post any other way.
- Also check: if no post has published in the last 8 days, flag that the
  Buffer-to-platform connection may have expired.
```

---

## The two rules that must survive any future edit

1. **Only `Approved` rows publish**, and only a human sets `Approved`. If you later
   ask Claude to "just approve the good ones" you have removed the only safety
   property in this design.
2. **A row whose slide images do not resolve never gets scheduled.** This is the guard
   against posting a caption with no pictures. Note it checks the *images*, not the
   Assets field — the URLs are derived from the Day number, so there is nothing to
   paste and nothing to mistype. The Assets field is a convenience link for you, not
   an input to the pipeline.

## First run

Treat week one as supervised. Approve as normal, let Monday's Routine schedule, then
**open Buffer and look at the queue before the first post goes out.** Confirm the
images, caption and time are right on both platforms. After that it can run unattended.

## If it turns out to be more trouble than it saves

Five posts a week is about fifteen minutes of manual scheduling in Buffer. If the
Routines break twice, turn them off and schedule by hand — the calendar and the
production system are the valuable parts. Spending three hours debugging a connector
to save fifteen minutes a week is exactly the waste this business is supposed to
eliminate.
