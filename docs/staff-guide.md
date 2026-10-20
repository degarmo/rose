# Staff guide

For volunteers who help run the website. No technical knowledge needed.

## Logging in

1. Go to the staff address you were given (it is not the normal website address,
   and it is not shared publicly).
2. Enter your email and password, then **Continue**.
3. Open your authenticator app and type the six-digit code, then **Log in**.

The first time, you set up the authenticator app: scan the square code with your
phone, type the six-digit code it shows, and save the ten **backup codes** you
are shown. Each backup code works once, for when you do not have your phone.
Keep them in a password manager or somewhere locked, never in a photo.

You are logged out when you close the browser, and after 12 hours anyway.

## Finding your way

The menu down the left side is grouped by job:

- **Today**: the **Dashboard**, the **Door desk** and **Reports**.
- **Members**: members, memberships, ID checks and tiers (plans).
- **Events**: events, **RSVPs (counts only)** and event tags.
- **Content**: the journal, announcements, education, the words on the site (**Page copy**),
  the FAQ, the community guidelines and the membership agreement.
- **Community**: feed posts, the moderation log and appeals.
- **Money**: payments, donations and the membership summary.
- **Outreach**: newsletters, subscribers, rentals, volunteers and contact messages.
- **Settings**: site settings, **Team and roles**, **Image review** and the audit log.

You only see what your role allows; a group with nothing in it for you is not shown. A red
number beside an item is how many things are waiting there (people who paid online and need
an ID check, reports and first posts, unanswered messages). The search box at the top finds
any section. Your name at the bottom opens the staff guide, your password and a link to the
public site; the sun or moon there switches between light and dark. On a tablet or phone the
menu hides behind the button at the top left.

## The dashboard

The admin's home page, **Today**, is the only dashboard. Admins and staff land there after
logging in.

- **Cards** link to where you act: active members, new members this month, income this
  month, the email list, open reports, posts awaiting approval and ID checks waiting.
- **30 days, 90 days, 12 months** changes the charts: income, payments, RSVPs and feed posts.
- **Tables** show members by plan (active, new, renewing, lapsing and expired), income this
  month and last, feed activity and the events in the period.
- **Coming up** lists the next three events.
- **Export** downloads the same figures as a spreadsheet, and the download is recorded.
- **Age verification card** shows whether the age check is on. Admins can change it from
  there.

It only shows numbers, never names. Any number from 1 to 4 shows as **<5** (hold the mouse
over it: "fewer than 5"), so nobody can be picked out. The red numbers in the menu are the
same figures as the cards. Moderators see only open reports, posts awaiting approval and ID
checks needed. What every number means is in `docs/ops/metrics.md`.

## Posting to the journal

1. **Journal** > **Posts** > **Add post**.
2. Write the caption. Line breaks are kept and web addresses become links.
3. Add 1 to 10 images. For each one: describe it in **alt text** (what it shows,
   for people who cannot see it), tick **faces visible** if anyone's face can be
   recognised, and tick **consent confirmed** only when every person visible has
   agreed in writing.
4. Optionally link an event or add a button.
5. Tick **Published** and set the date. A future date publishes it then.

The site will not publish an image showing faces without confirmed consent.

## Events

1. **Events** > **Add event**. Fill in the title, the summary (one or two
   sentences), the date and time, and the place.
2. **Audience**: *Public* (anyone with an account can RSVP), *Account* (only
   people signed in can even see it) or *Members* (only members can RSVP).
3. **Capacity** is the number of people, including guests. Tick **waitlist**
   if people may queue when it is full.
4. Tick **Published** when it is ready.

**Repeat weekly**: tick the event in the list, choose **Repeat weekly** from the
actions box that appears above the list, press **Run**, pick how many weeks, and confirm. Copies keep the same time of day.
Copies that already exist are skipped.

**Door list**: press **Door list** on the event's row in **Events**, or in
**Events > RSVPs (counts only)**, which shows how many are going, waiting and checked in. It shows display names and
party sizes, never emails. Tick people in as they arrive.

## The door desk

On the tablet at the door, sign in on the website as usual (email, password, then the
six-digit code) and you land on the **Door desk** in the member app, at
`/members/staff/door`: a big search box, a **Scan QR** button and large buttons, made for a
tablet or a phone. If you are on the team it is also under **Door desk** beside **Staff** in
the member app's menu. It is the only door desk: **Today > Door desk** in the admin, a
membership's **Open** link and the dashboard's **ID checks needed** card all open it. This
guide is also in the admin: click your name at the bottom of the menu, then **Staff guide**.

On the tablet desk each person shows as a card with their display name, plan, status,
**ID verified** or **ID check needed**, events left this month and guests included, and a
red **Do not admit** banner when that applies (then no buttons are offered: ask a member of
the team). Press a big button (**Check in**, **ID check**, **Record payment and activate**,
**Guest visit**, **Renew**) and a box opens with what that action needs.

1. **Find the person**: type their reference code (like `R7K-42Q`, with or
   without the dash) or display name, or press **Scan QR** and point the camera
   at the code on their phone.
2. **Check their photo ID** before any first activation: they must be 18 or
   older. Look at it, hand it back. Never photograph or copy an ID, and never
   write down its details.
3. Choose the action:
   - **Record payment and activate**: pick cash or card, check the amount, tick
     **Photo ID checked, 18+** if asked, and press the button.
   - **Activate** (when they already paid online, or chose a free plan such as Community
     or First Fridays: there is nothing to take): tick the ID box and press it.
   - **Check in tonight** (a member at tonight's members-only event without an RSVP):
     choose the event and whether they bring a guest. It follows their plan: it uses one of
     the month's events and is refused if the plan does not include the event or the month
     is used up.
   - **Renew**: for someone whose membership is running out or has lapsed.
   - **Complimentary membership**: needs a short reason.
   - **Suspend** or **Reinstate**: needs a short reason.
   - **Refund**: in the payments list, type the amount and press Refund.
4. Each card shows the plan's rules: **Events this month** (how many are left, or
   "Unlimited"), how many guests come free per event, and **Guest discount** when their
   guests pay the lower price.
5. **Show signature name** reveals the full name someone typed when they signed
   the agreement. Only use it when you truly need it; every use is recorded.

### The age check

Nobody sees or posts photos in the member feed until someone on the team has checked their
photo ID in person. That includes the team: your own feed, and the pictures in reports, open
only once your own check is recorded.

- **What to look at:** a valid photo ID showing they are 18 or older. Look, hand it back.
  Never photograph, copy or write down anything from it. The site keeps only that you saw it.
- **Needs ID check** (on the door desk) lists everyone waiting: memberships without a check,
  and people with no membership who have feed access (team members, and people the staff
  granted the feed to, shown as **Granted, awaiting ID check**). Search by display name finds
  those people too.
- **Record ID check** records the check on its own. Activating, comping, renewing a lapsed
  membership or reinstating one also asks for the **Photo ID checked, 18+** box when there
  is no check on file.
- **Your own check:** another team member can record it, or you record it and choose a
  second team member, there with you, as witness. Both names go in the log.
- **Revoke ID check** (with a reason) if a check was recorded by mistake. Their member feed
  closes at once. A check never needs renewing otherwise.

The person gets a plain "You're all set" email and their feed opens without logging out.

**Turning the age check off or on.** The club can switch the age check for the member feed
off, for example before the door desk is staffed. Only an admin can do it: **Change** on the
age verification card on the admin dashboard, or **Settings > Site settings > Age verification
for the member feed > Open** in the admin. It asks for a reason and a new code from your
authenticator app, says what will happen, and the change is logged. While it is off, an amber
banner says so on every staff page, the verify card disappears for members, and the door desk
keeps showing who is checked. Turning it back on closes the feed at once to everyone without a
check (each of them gets one plain email). The door desk's ID check before a membership
starts, the 18+ promise on uploads and "possibly under 18" reports work the same either way.

### Event tags and plan rules

Some plans only reach some members-only events (Community: events tagged **Community**;
First Fridays: events tagged **First Friday**). Tag an event under **RSVP > Access tags**
when you create it. **Guest allowance** on an event lets members bring extra guests beyond
what their plan includes. A plan's price, events per month, guests, guest discount, premium
Discord, member community and tags are under **Memberships > Tiers**; the membership page
shows them straight away.

### Guests at the door

A guest signs up online (from the **Guests** page) and arrives with a reference code.

1. Search for the code or their display name. Guest passes say **Guest pass**.
2. Under **Guest visit**: check their photo ID (tick the box only if there is no ID check on
   file yet), pick cash or card, check the amount and press **Record payment, in for tonight**.
3. The pass ends by itself the next day. When they come back, find the same code and do
   **Guest visit** again: no new sign-up, and no new ID check.

**Convert to member**: open it on their card and let them scan the code with their own
phone. They choose a membership and sign there, in their own account. Then search for them
again and use **Record payment and activate**; their ID check carries over.

### Recording a donation at the door

Open **Record donation** at the top of the door desk. Choose cash, card or check, type the
amount, and optionally a name to record (leave it blank for Anonymous) and an email for an
acknowledgement. The acknowledgement is emailed with a plain subject and the address is
then forgotten.

## Rentals

**Rental inquiries** > **Pipeline view** shows every open request by status, soonest first.
A red **Clash** means the requested time overlaps a published event or another booking.

- Open an inquiry to read it. **Move to** changes its status (In discussion, Quoted,
  Declined, Cancelled); every change is recorded.
- **Mark confirmed** opens a page where you can also **add a private placeholder to the
  calendar**. It holds the time so nobody double-books it, and it is never shown on the site.
  Declining or cancelling later removes it.
- Photoshoot requests are only accepted once the person has promised everyone photographed
  will consent and no other guests or members will appear. Hold them to it.
- Ninety days after a request is declined or cancelled, its contact details are deleted
  automatically. Do not copy them anywhere else.

## Volunteers

**Outreach > Volunteers** lists everyone who offered to help. Filter by interest or status
under **Filters**. Use the actions box above the list to mark people contacted, active or inactive. **Export CSV**
downloads a list without email addresses; only an administrator can add them, and every
download is recorded. Delete the file when you are done with it.

## Donations

**Donations** lists every gift. Nothing here can be edited or deleted: a correction is a
refund recorded by the payment provider. Gifts show as Anonymous unless the donor chose to
show their display name, and no list of donors is ever published.

**Open** next to a gift shows its acknowledgement, using the wording in **Acknowledgement
wording** (with the club's legal name and EIN from Site settings). Print it, or email it if
the donor left an address and it was not sent yet.

## Newsletters

1. **Email list** > **Newsletters** > **Add newsletter**. Write the subject, the preheader
   (the grey line inboxes show after the subject) and the body.
2. **Keep the subject and preheader neutral.** They show on lock screens and shared
   computers. Never the club's name, what happens here, or anything you would not want a
   housemate to see. The **inbox preview** at the top of the page shows, as you type, exactly
   how the sender, subject and preheader will look in an inbox.
3. Save, then **Send test to me**: it goes only to your own address.
4. To send: tick the box and press **Send**, or set the status to Scheduled with a time.
   It goes only to people who confirmed their address. Opens and clicks are never tracked.

You cannot add people to the list yourself: everyone confirms their own address. If
someone asks to be removed, select them in **Subscribers** and use **Unsubscribe the
selected people**.

## Editing the words on the site

**Pages** > **Page copy** holds every heading and paragraph on the public pages, by page
and key (for example `home` / `hero.title`). Change the text and save; the site shows it
within a minute. "Formatted" values allow paragraphs, lists, bold, italics and links; plain
values keep their line breaks. **Staff profiles** and **FAQ items** are edited the same way.

### Approving draft content

The copy from the old website was drafted into files marked "draft - needs club approval".
A board member reads each file and its notes, corrects it, and changes its status to
"approved". An administrator then loads it at **Page copy** > **Load site content**: upload
the files, check what would change, then tick **Write the changes**. Drafts are refused on
the live site unless an administrator deliberately allows them, which is recorded.

## Moderation queue

**Today > Reports** in the admin lists reported posts, comments and profiles, and first
posts waiting for review. The dashboard's **Open reports** counts reports; one post can have
several. Most of this work now happens in the member app's staff section, below.

- **Approve** puts a post back. **Remove** takes it down (you must give a reason;
  the author sees it). **Dismiss** closes a report that needs no action.
- **Warn**, **Suspend** (for a number of days) and **Ban** are for people.
- Posts reported as *posted without consent* or *may involve someone under 18*
  are hidden at once. Treat them first: reports marked **Possibly under 18** are always at
  the top.
- People who report never learn the outcome, and authors never learn who
  reported them. Do not tell anyone either.

## The staff section (in the member app)

Moderators, staff and admins work in the member app, under **Staff** in the sidebar (on a
phone: your profile, then Settings, then Staff). It holds the hands-on tools: the door desk,
the reports inbox, members and, for admins, the team. It has no figures; **Dashboard** there
opens the admin's. Moderators land on the reports inbox after logging in. Logging in on the website asks for the code
from your authenticator app straight after your password, and that unlocks the staff section
for the session; a new team member sets one up the first time they open it.

- **Roles.** A *moderator* handles reports and member actions. *Staff* also see the whole
  admin dashboard. An *admin* also manages the team (**Team**) and can see who sent a report.
- **Reports.** Open, In review, Resolved and Dismissed, plus **Appeals**. Reports cover
  posts, comments, profiles and concerns about something at an event or the club (from
  members, or from anyone through **Report a concern** on the website). What was reported
  stays blurred until you press **View reported content**. Who sent it stays hidden; only
  an admin can reveal it, and that is logged. Use **Assigned to** and **Internal notes** to
  share the work; notes are only for the team.
- **Actions.** From a report, or from a member's page under **Members**: a warning, removing
  the reported content, a feed suspension (7 or 30 days, or until a date), an event
  suspension (no RSVPs, and the door desk shows it) or a ban (ends their membership, closes
  the app, the door desk shows **Do not admit**, and you can stop the email registering
  again). Every action needs the rule it relates to and a reason; the member reads both in
  Settings, under Notices. Emails only say "An update about your account".
- **Reversing.** Any action can be reversed with a reason, from the member's page or the
  report. The log keeps both.
- **Appeals.** A member can appeal each action once. Appeals go to someone other than the
  moderator who acted; if that was you, someone else decides.

People who report learn only that their report was received, then reviewed. Never tell
anyone more, and never tell a member who reported them.

## Image review

**Settings > Image review** (for staff who edit events, the journal, education or the staff
page) shows every site image and whether it is shown or hidden, and why. An image with faces visible and no confirmed
consent is always hidden. To change one, open the record it belongs to and fix
the alt text or consent boxes.

## Membership summary

**Money > Membership summary** shows how many memberships are in each state, new,
renewed and lapsed this month, and income by month. **Download CSV** gives a
list of display names, tiers and dates; only an administrator can add email
addresses, and every download is recorded.

## What never to export, photograph or share

- Member lists, door lists, RSVP lists or exports, outside the staff screens.
- Anything from the member feed, including screenshots (every image carries the
  viewer's name in a faint watermark, so a leak can be traced).
- Signature names, emails, phone numbers or payment details.
- Photo IDs, ever.
- Your backup codes, password or the staff address.

If you think something has leaked, tell the incident lead straight away. Do not
try to clean it up yourself.

## The club's name

The name shown on the website, in the admin, as the sender of every email, on receipts,
in calendar files and in the authenticator app comes from **Site settings** > **Site name**.
Leave it blank to use the name set when the site was installed. A change shows within a few
minutes everywhere.
