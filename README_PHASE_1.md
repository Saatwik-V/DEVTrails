# 🛡️ GigKavach

### *Zero-touch parametric income protection for India's gig workers*



> **GigKavach** is an AI-powered parametric insurance platform that automatically detects income-disrupting events, computes payouts using a real-time Disruption Composite Index, and credits money to a gig worker's UPI account by end of day — without the worker filing a single claim.



<div align="center">

|🏍️ 10M+ Workers Targeted|⚡ Same Day Payout|🌐 5 Languages|🛡️ 27 Edge Cases|₹0 API Cost|
|:-:|:-:|:-:|:-:|:-:|

</div>

---

## 📋 Table of Contents

1. [The Problem](#1-the-problem)
2. [The Solution](#2-the-solution)
3. [Why GigKavach Is Different](#3-why-gigkavach-is-different)
4. [Persona Deep Dive](#4-persona-deep-dive)
5. [Application Workflow](#5-application-workflow)
6. [The DCI Engine](#6-the-dci-engine)
7. [Weekly Premium Model](#7-weekly-premium-model)
8. [Parametric Triggers](#8-parametric-triggers)
9. [AI/ML Integration](#9-aiml-integration)
10. [Fraud Detection Architecture](#10-fraud-detection-architecture)
11. [Adversarial Defense \& Anti-Spoofing Strategy](#11-adversarial-defense--anti-spoofing-strategy)
12. [Edge Case Handling](#12-edge-case-handling)
13. [Special Features](#13-special-features)
14. [Multilingual Support](#14-multilingual-support)
15. [Tech Stack](#15-tech-stack)
16. [API Integrations](#16-api-integrations)
17. [Database Design](#17-database-design)
18. [Six-Week Development Roadmap](#18-six-week-development-roadmap)
19. [Team](#19-team)
20. [Demo Video](#20-demo-video)
21. [Summary](#21-summary)

---

## 1\. The Problem

Ravi is a food delivery partner (Zomato/Swiggy) in Koramangala, Bengaluru. He earns approximately ₹700 a day — enough to cover rent, food, and send money home to his family in Dharwad. On a Tuesday in July, heavy rain floods his delivery zone. Orders stop. He earns ₹0 that day.

There is no insurance for this. No claim he can file. No safety net. He simply loses the day.

This happens to over 10 million platform-based delivery workers across India. External disruptions — extreme weather, severe pollution, unplanned curfews, local strikes — can wipe out **20–30% of a gig worker's monthly income**. They bear this loss entirely alone, with no financial product designed to protect them.

> \*We are not solving vehicle repair or health coverage. We are solving one specific, overlooked problem: \*\*income lost because of events completely outside the worker's control.\*\*\*

---

## 2\. The Solution

**GigKavach** is a parametric income protection platform built exclusively for food delivery partners (Zomato/Swiggy). It works on a simple principle:

> When an objective, measurable disruption event occurs in a worker's zone during their active shift — the system detects it, monitors the disruption duration, calculates the payout at end of shift, and sends money to their UPI. The worker does nothing.

**No app to download. Just a WhatsApp interface. No claim to file. No adjuster to wait for.**

A worker joins via WhatsApp in under 4 minutes, pays a weekly premium as low as ₹69, and is automatically protected for the week. When disruption hits, they receive a WhatsApp alert confirming the disruption was detected. At end of day, they receive a payment confirmation. That is the entire experience.

<div align="center">

### How GigKavach Works

|**Step 1** 📱|**Step 2** 🌧️|**Step 3** 💸|
|:-:|:-:|:-:|
|Join via WhatsApp|Disruption Detected|Money in Your UPI|
|*4 minutes*|*Automatic*|*Same day*|

</div>

---

## 3\. Why GigKavach Is Different

|Feature|Traditional Insurance|Generic InsurTech|**GigKavach**|
|-|-|-|-|
|Claim process|Manual, weeks of waiting|Digital form, days of waiting|**Zero — fully automated**|
|Pricing cycle|Monthly/Annual|Monthly|**Weekly — matches gig earnings**|
|Trigger mechanism|Human adjuster|Rule-based threshold|**AI composite score (DCI)**|
|Worker interface|Agent/App|App|**WhatsApp — no download needed**|
|Payout time|Weeks|Days|**Same day**|
|Fraud detection|Manual review|Basic rules|**Isolation Forest ML model**|
|Language support|English only|English only|**5 Indian languages**|
|Coverage scope|Broad|Broad|**Income loss only — laser focused**|
|Zone granularity|State level|City level|**Pin-code level**|

---

## 4\. Persona Deep Dive

**Persona: Food Delivery Partner — Zomato / Swiggy**

We chose this persona because food delivery workers are the most weather-sensitive delivery segment — rain directly halts orders — and Indian monsoon season creates predictable, recurring income disruption for hundreds of thousands of workers.

|Attribute|Detail|
|-|-|
|Typical daily earnings|₹500 – ₹900|
|Working days per week|5–6 days|
|Typical shift|9AM – 9PM (with breaks)|
|Primary language|Hindi (many are migrants)|
|Phone type|Budget Android (₹5,000 – ₹12,000)|
|WhatsApp usage|Daily — primary communication tool|
|Insurance awareness|Very low|
|Willingness to pay|₹69–₹99/week if payout is guaranteed|
|Biggest fear|Losing an entire day's earnings to disruptions|

**Key Insight:** This worker will not download a new app. They will not navigate a claims portal. They will not call a helpline. Any product that requires any of these has already failed for this persona. GigKavach works entirely within WhatsApp — a tool already open on their phone every day.

---

## 5\. Application Workflow

### Worker Onboarding (4 minutes via WhatsApp)

```
Worker sends "JOIN" to GigKavach WhatsApp number
    ↓
Step 0: Language selection (English / ಕನ್ನಡ / हिंदी / தமிழ் / తెలుగు)
    ↓
Step 1: Platform selection (Zomato/Swiggy)
    ↓
Step 2: Shift selection (Morning / Day / Night / Flexible)
    ↓
Step 3: Verify gig worker using Digilocker (AADHAR, PAN, DL)
    ↓
Step 3: UPI ID for payouts
    ↓
Step 4: Pin codes (zone assignment)
    ↓
Step 5: Weekly plan selection (Shield Basic / Plus / Pro)
    ↓
Coverage activates 24 hours after premium payment
(24-hour delay prevents moral hazard — joining because a storm is forecast)
```

### When Disruption Hits

```
DCI Engine polls APIs every 5 minutes
    ↓
DCI score computed for all active zones
    ↓
DCI ≥ 65 detected in worker's zone during active shift
    ↓
Eligibility check:
  → Active policy this week?
  → Coverage started before disruption?
  → Worker logged in recently / active pattern confirmed?
    ↓
WhatsApp Alert sent immediately:
  "Disruption detected in your zone (DCI: 72).
   Your coverage is active. Payout will be
   calculated at end of your shift today."
    ↓
System continues monitoring disruption duration throughout shift
    ↓
End of shift: Total disrupted hours tallied
    ↓
Payout amount calculated using Earnings Fingerprint baseline
    ↓
Anti-Spoofing \& Fraud Detection layer runs automatically:
  → 6-signal composite fraud score computed per worker
  → Score < 3 signals  →  Path A: Clean — full payout proceeds
  → Score 3–4 signals  →  Path B: Soft Flag — 50% payout now,
                           silent re-verification over 48hrs,
                           remaining 50% auto-credited if clear
  → Score 5–6 signals  →  Path C: Hard Block — payout withheld,
                           Tier 2 / Tier 3 penalization applied
    ↓
Razorpay UPI payout fires (for Path A and Path B)
    ↓
WhatsApp Confirmation: "₹280 sent to ravi@upi. Ref: RZP12345
  Your income is protected."
```

### Worker Commands (Anytime)

|Command|Action|
|-|-|
|`JOIN`|For WhatsApp Onboarding|
|`STATUS`|Current DCI, coverage details, zone status|
|`RENEW`|Renew policy for next week|
|`SHIFT`|Update working hours for this week|
|`LANG`|Switch language|
|`HELP`|Show all commands|
|`APPEAL`|Contest a fraudulent claim (48 hours)|

---

## 6\. The DCI Engine

The **Disruption Composite Index (DCI)** is GigKavach's core intelligence layer. It aggregates independent data streams into a single 0–100 score computed at pin-code level every 5 minutes.

**Weights for each data stream vary from city to city and are determined during model training.**

### Formula

*(Below mentioned numerical values are for demonstrative purposes only)*

```
DCI = (Rainfall × 0.30) + (AQI × 0.20) + (Heat × 0.20)
    + (Social Disruption × 0.20) + (Platform Activity Drop × 0.10)
```

<details>
<summary><b>📊 View Full Component Breakdown</b></summary>

|Component|Weight|Trigger Condition|Data Source|
|-|-|-|-|
|Rainfall|30%|> 15mm/hr sustained 2hrs|Tomorrow.io (primary)|
|AQI|20%|> 300 (Severe category) for 4hrs|AQICN + CPCB|
|Extreme Heat|20%|> 42°C during 10AM–4PM|Tomorrow.io + IMD|
|Social Disruption|20%|Bandh / curfew / strike detected|Deccan Herald RSS + NLP|
|Platform Activity Drop|10%|> 60% order drop from zone baseline|Mock platform API|

</details>

### Severity Tiers

|DCI Score|Severity|Eligibility Logic|Payout|
|-|-|-|-|
|0–65|No disruption|No trigger|None|
|65–84|Moderate disruption|Login today OR worked recently|Full/half payout|
|85–100|Catastrophic|Active policy only — login impossible|Full payout|

### Important DCI Rules

* **Working hours filter:** Disruptions outside a worker's declared shift window do not trigger payouts. A 2AM curfew does not pay a day-shift worker.
* **Natural disaster override:** An active NDMA alert for Karnataka automatically overrides DCI to 90+, bypassing the composite calculation entirely.
* **Multi parameter fallback trigger:** If DCI misses threshold but any individual signal independently crosses its own threshold, then DCI calculation is bypassed and payout is processed.

### 4-Layer Data Redundancy

GigKavach never relies on a single data source for a component (APIs). If one layer fails, the next activates instantly:

```
Layer 1: Tomorrow.io (primary — best hyperlocal accuracy)
    ↓ fails
Layer 2: Open-Meteo + OpenWeatherMap (fallback APIs — free, unlimited)
    ↓ fails
Layer 3: Redis cache (last known DCI, max 30 mins old)
    ↓ cache miss
Layer 4: IMD RSS color alert (government source, district level)
    ↓ all fail > 30 mins
SLA Breach: Auto-payout at probability-adjusted rate fires
```

If our AI model is genuinely down or all data feeds fail, the SLA breach payout is processed.

Our architecture makes these payouts extremely rare — four independent layers (multiple API sources) must all fail simultaneously before one triggers.

---

## 7\. Weekly Premium Model

### Three Tiers

|Plan|Weekly Premium|Coverage|
|-|-|-|
|Shield Basic|₹69|40% of daily earnings|
|Shield Plus|₹89|50% of daily earnings|
|Shield Pro|₹99|70% of daily earnings|

### Why Weekly?

Gig workers operate on daily earnings cycles — they receive platform payouts daily and manage expenses weekly. A monthly premium of ₹200–₹400 is a large upfront commitment for a worker earning ₹700/day. A weekly ₹69–₹99 aligns with how they already think about money.

### Premium Structure

Weekly premiums are **fixed tiers** — workers choose their plan at onboarding and pay the same amount every week. Premiums do not change dynamically. This keeps the product simple, predictable, and trustworthy for workers who cannot afford surprises in their weekly costs.

Dynamic ML (XGBoost) is applied to **payout calculation only** — not premium pricing. The model determines how much a worker receives based on city-specific disruption weights, not how much they pay. This separation ensures workers always know exactly what they owe each week while still benefiting from intelligent, fair payout computation.

### Moral Hazard Prevention

* **Tier lock:** Plan upgrades apply from the next weekly cycle only. A worker cannot upgrade to Shield Pro on Thursday because a storm is forecast for Friday.
* **Coverage delay:** First-time coverage begins 24 hours after initial payment. Workers cannot sign up during an active disaster.

---

## 8\. Parametric Triggers

GigKavach insures **income lost during external disruption events only.**

**Weights for each disruption type vary from city to city and are determined during model training.**

### What Is Covered

*(Below mentioned numerical values are for demonstrative purposes only)*

|Disruption Type|Example|DCI Component Triggered|
|-|-|-|
|Extreme rainfall|> 15mm/hr for 2 hours|Rainfall (30%)|
|Severe air pollution|AQI > 300 for 4 hours|AQI (20%)|
|Extreme heat|> 42°C during working hours|Heat (20%)|
|Unplanned bandh / curfew|Sudden civic shutdown|Social (20%)|
|Local strikes|Auto/delivery strike, market closure|Social (20%)|
|Platform-wide outage|Massive order drop > 60%|Platform (10%)|
|Natural disaster|NDMA-declared flood/earthquake|Automatic override|

### What Is Strictly Excluded

* ❌ Vehicle repair costs
* ❌ Health or medical expenses
* ❌ Accident compensation
* ❌ Life insurance
* ❌ Personal decisions to take leave

> *GigKavach is a safety net for uncontrollable external events that prevent a willing worker from earning. It is not a general income supplement.*

---

## 9\. AI/ML Integration

### Model 1: XGBoost — Dynamic Payout Calculation

**What it does:** Calculates the optimal payout value for each worker based on the weights of disruption type as decided by the model for that particular city.

**Features used:** Disruption types prevalent in that city with their corresponding weight values.

**Why XGBoost:** Handles mixed tabular features well, fast inference, interpretable feature importance — important for explaining changes in payout to workers.

**Training data:** Synthetic data generated from various APIs and realistic worker profiles.

### Model 2: Isolation Forest — Fraud Detection

**What it does:** Learns what a normal claim event looks like and flags anything statistically anomalous without needing labeled fraud examples.

**Features used:** DCI score at trigger time, number of claims in zone in last 2 minutes, GPS verification percentage, platform activity status, registration age.

**Why Isolation Forest:** Unsupervised — does not need labeled fraud data (which we don't have for a new platform). Abnormal claim patterns are inherently easier to isolate than normal ones.

**Training:** Trained on synthetic normal claim data. Contamination parameter set to 0.05 (assumes 5% of claims may be anomalous).

### Model 3: HuggingFace NLP — Social Disruption Detection

**What it does:** Classifies RSS news headlines from Deccan Herald and The Hindu Karnataka as disruption-relevant or not, feeding the social component of DCI.

**How it works:**

```
RSS feed article: "Karnataka bandh called on April 21 over CAA protests"
    ↓
Keyword pre-filter: "bandh" detected
    ↓
Zero-shot classifier: P(civic disruption) = 0.94
    ↓
Zone extraction: "Karnataka" → all Karnataka zones
    ↓
DCI social component += 35 for affected zones
```

**Why NLP over keyword matching:** Pure keyword matching misses context. "Traffic bandh due to festival parade" is not an income disruption. The NLP classifier understands context, not just keywords.

### Model 4: Earnings Fingerprint — Baseline Calculation

**What it does:** Computes a worker's expected daily earnings per day-of-week using a rolling 4-week median, adjusting for festival weeks and disruption days.

**Why median not mean:** A sick week with ₹200 earnings doesn't tank the baseline. The median is naturally robust to outlier weeks.

**Transition for new workers:** City-segment average blends into personal history over 4 weeks (30% personal at week 3, 60% at week 4, 100% personal from week 5).

---

## 10\. Fraud Detection Architecture

GigKavach's fraud system operates on two principles: **detect at the individual level** and **penalize proportionally**.

### Detection Signals

|Signal|What It Detects|
|-|-|
|GPS vs IP address mismatch|VPN spoofing or location faking|
|Claim burst in < 2 minutes|Coordinated fraud ring|
|DCI barely above threshold|Gaming the minimum trigger|
|Worker offline on platform all day|Not working but claiming|
|Registration date = today|Account created for this event|
|Same device ID, multiple accounts|Fake account farming|
|Platform inactive + GPS unverified|Combined fraud signal|
|Stationary GPS all day + zero order completions|Two-phone fraud — planted device in zone|

**Signal breakdown:**

* **GPS vs IP address mismatch —** GPS says Koramangala, IP resolves to Marathahalli. Two independent location layers that a spoofing app cannot simultaneously fake.
* **Claim burst in < 2 minutes —** Telegram-coordinated syndicates trigger in under 90 seconds. Genuine disruptions produce organic eligibility spread over 15–20 minutes. The timestamp distribution reveals coordination.
* **DCI barely above threshold —** Legitimate disruptions score well above 65. Consistent clustering at 65–68 across a worker's claim history indicates threshold gaming, not genuine income loss.
* **Worker offline on platform all day —** A genuinely stranded worker earned something before the storm hit. Zero platform earnings all day combined with sudden zone GPS appearance = spoofer who never left home.
* **Registration date = today —** Syndicate accounts are created the day of the event. Workers with same-day registration claiming during a disruption are automatically elevated to high-risk.
* **Same device ID, multiple accounts —** One device registering multiple worker identities is classic fake account farming. Device fingerprint is captured at onboarding and cross-checked on every eligibility run.
* **Platform inactive + GPS unverified —** Neither platform activity nor GPS independently confirm presence. Two failing signals together constitute a combined hard indicator.
* **Stationary GPS + zero order completions —** A delivery worker on a bike produces natural movement and order activity. A phone planted in a zone stays perfectly still and accepts no orders. Physics and platform data together make this signal nearly unfakeable.

### Three-Tier Penalization

**Tier 1 — Soft Flag (Silent)**
2–3 fraud signals are suspicious but not definitive — consistent with genuine network degradation during a storm. Payout fires at EOD at 50% of the calculated amount. System continues silent GPS re-verification over 48 hours with no worker action required. If signals normalize, remaining 50% auto-credits automatically. Worker message: *"Your payout is processing. Verification active due to signal conditions in your zone. No action needed."* No accusation. Zero friction.

**Tier 2 — Hard Flag (Account Review)**
5 or more fraud signals confirm a coordinated spoofing attempt or Tier 1 escalation. Payout withheld. Worker notified via WhatsApp. Current week premium forfeited. The `APPEAL` command opens a 48-hour data discrepancy window — cross-checked automatically against IMD and KSNDMC official records. System resolves without human discretion. No override possible.

**Tier 3 — Blacklist**
Confirmed fraud ring participation, GPS spoofing with repeat offense, or syndicate coordination confirmed. Permanent platform ban. UPI flagged in fraud registry. Reported to insurer. No appeal path via WhatsApp — must contact support directly.

### Individual Scoring — Not Batch Rejection

In a cluster of 500 simultaneous claims, GigKavach scores each worker individually:

```python
for worker in flagged\_cluster:
    individual\_score = calculate\_individual\_fraud\_score(worker)
    if individual\_score > threshold:
        flag\_individual(worker)      # bad actor
    else:
        process\_payout(worker)       # legitimate worker still gets paid
```

Innocent workers in the same zone as a fraud ring are never punished.

### Appeals Process

The `APPEAL` command allows workers to challenge the fraudulent claim done by the AI model. The request is processed within 48 hours and payout is automatically processed if the claim turned out to be false.

---

## 11\. Adversarial Defense \& Anti-Spoofing Strategy

GigKavach's fraud architecture was designed from the ground up with coordinated GPS-spoofing syndicates in mind. The individual scoring system described in Section 10 is the foundation — but the anti-spoofing layer goes significantly deeper, using 6 independent non-GPS signals to separate genuine stranded workers from bad actors.

---

### The Differentiation

Simple GPS verification is insufficient. A genuine stranded worker and a GPS spoofer can share identical coordinates. The key differentiator is **behavioral trajectory** — what happened in the 2 hours *before* DCI crossed 65.

* A genuine worker has a natural GPS movement history inside the zone — restaurant pickups, route patterns, micro-drift from shelter-seeking as rain intensifies.
* A spoofer teleports into the zone minutes before the trigger fires, with zero prior movement history. This is nearly impossible to fake convincingly at scale.

GigKavach's system already scores every worker individually within a flagged cluster — never batch-rejecting an entire zone:

```python
for worker in flagged\_cluster:
    individual\_score = calculate\_individual\_fraud\_score(worker)
    if individual\_score > threshold:
        flag\_individual(worker)      # bad actor
    else:
        process\_payout(worker)       # legitimate worker still gets paid
```

This individual scoring foundation is what makes the anti-spoofing response surgical rather than blunt.

---

### The Data — 6 Signals Beyond Basic GPS

**Signal 1 — Cell Tower Triangulation vs GPS**

* Every smartphone simultaneously reports GPS coordinates and cell tower IDs.
* GPS spoofing apps manipulate only the GPS layer. Cell tower IDs are controlled by the carrier network and cannot be faked by any consumer spoofing application.
* If GPS reports Koramangala but cell towers resolve to Marathahalli → **hard fraud signal.**

---

**Signal 2 — IP Geolocation Cross-Check**

* Already part of GigKavach's detection table as *"GPS vs IP address mismatch."*
* In the syndicate scenario, this signal scales powerfully: 500 workers simultaneously claiming to be in Koramangala while their IP addresses resolve across 12 different residential ISP nodes is a statistical impossibility that no genuine disruption event produces.

---

**Signal 3 — Pre-Disruption Earnings Velocity**

* Already captured in GigKavach's detection table as *"Worker offline on platform all day."*
* A genuinely stranded worker earned something before the storm halted orders. A spoofer who never left home shows ₹0 platform earnings for the entire day.
* Zero pre-disruption earnings + GPS appearing in zone only after DCI became imminent → **elevated fraud score.**

---

**Signal 4 — GPS Movement Entropy**

* Genuine delivery workers on bikes produce natural micro-movement — GPS drift, acceleration, deceleration, route-following patterns.
* GPS spoofing apps broadcast perfectly static coordinates or mathematically straight-line movement.
* Movement entropy computed over the 30 minutes before the trigger separates human motion signatures from synthetic ones. A human on a delivery bike cannot hold coordinates to 6 decimal places.

---

**Signal 5 — Claim Timing Clustering — The Telegram Signature**

* GigKavach already flags *"Claim burst in < 2 minutes"* as a coordinated fraud ring signal.
* Genuine disruptions produce organic eligibility patterns distributed over 15–20 minutes as workers independently notice orders stopping. Standard deviation of eligibility timestamps: \~12–18 minutes.
* Telegram-coordinated syndicates produce timestamp clustering with standard deviation under 90 seconds — statistically impossible in natural disruptions.
* **Critically, this signal does not compromise the parametric nature of GigKavach.** Workers are not filing claims. The system is detecting coordination in the pattern of eligibility checks it runs autonomously. The parametric DCI trigger fires or does not fire based purely on objective external data — this signal only determines whether the automated payout for an already-triggered event is legitimate.

---

**Signal 6 — Zone Historical Loyalty**

* During WhatsApp onboarding, every worker declares the pin codes they deliver in. GigKavach additionally builds 4 weeks of activity history tracking which zones each worker has actually operated in.
* A worker who declared HSR Layout at onboarding and has 4 weeks of history there — but whose GPS suddenly places them in a high-DCI Koramangala zone they have never delivered in — is exhibiting a pattern no genuine delivery worker produces.
* Syndicate members pick whichever zone has the highest DCI with no regard for their actual delivery geography. Zone loyalty mismatch is clean, objective, and rooted in data the worker themselves provided.

---

### The UX Balance — Contextual Fraud Scoring

The fraud score is a weighted composite of the 6 signals above. The threshold required to act on that score is **dynamically adjusted based on DCI severity** — because during catastrophic events, legitimate signal degradation (cell tower outages, IP routing failures, GPS noise) affects genuine workers too. The system must not penalize real workers for infrastructure failures caused by the very event it is protecting against.

```
If DCI >= 85 (catastrophic):
    Require 5 of 6 signals to confirm fraud before hard block
    Signal degradation is expected — benefit of doubt applies
    Genuine workers must not be penalized for network failures

If DCI 65–84 (moderate):
    Require 3 of 6 signals → Soft Flag (Tier 1)
    Require 5 of 6 signals → Hard Block (Tier 2 / Tier 3)
```

**Path A — Clean → No Flag (Tier 0)**

All 6 signals pass. Payout fires at EOD. Worker receives payment confirmation. No friction, no accusation, no awareness that a verification check occurred.

**Path B — Ambiguous → Tier 1 (Soft Flag)**

2–3 signals are suspicious but not definitive — consistent with genuine network degradation during a storm. Maps directly to GigKavach's **Tier 1 Silent Flag.** Payout fires at EOD at 50% of the calculated amount. System continues silent re-verification over 48 hours. If signals normalize, remaining 50% auto-credits with no worker action required. Worker message: *"Your payout is processing. Verification active due to signal conditions in your zone. No action needed."* No accusation. Zero friction. Fully automated resolution.

**Path C — Confirmed Fraud → Tier 2 / Tier 3**

5 or more signals confirm fraud. Maps directly to GigKavach's **Tier 2 Hard Flag or Tier 3 Blacklist** depending on whether syndicate coordination is confirmed. Payout blocked. Worker notified. The `APPEAL` command opens a 48-hour data discrepancy window — cross-checked automatically against IMD and KSNDMC official records. System resolves without human discretion. The parametric contract remains intact at every stage.

> **Architectural principle:** Workers are never told "you look fraudulent." Signal degradation language is used consistently — framing every verification as a system condition, not a personal accusation. This protects innocent workers psychologically while blocking bad actors operationally.

---

## 12\. Edge Case Handling

GigKavach has systematically addressed 27 documented edge cases across 7 system modules. This section summarises the most critical ones. The full edge case handbook (27 cases with pseudocode) is available in [`/docs/edge_cases.pdf`](./docs/edge_cases.pdf).

<details>
<summary><b>👷 View Worker Eligibility Edge Cases</b></summary>

|Edge Case|Resolution|
|-|-|
|Worker on planned leave|Platform activity check — no login + no recent history = no payout|
|Multi-day disaster (nobody can log in)|DCI ≥ 85 = active policy only check. Login impossible = not required|
|Worker joins mid-week|24-hour coverage delay prevents disaster chasing|

</details>

<details>
<summary><b>💰 View Payout Calculation Edge Cases</b></summary>

|Edge Case|Resolution|
|-|-|
|Disruption spans midnight|Split at midnight, each day calculated against its own baseline|
|Festival week inflating baseline|Known festival weeks excluded from 4-week rolling calculation|
|UPI payment failure|3 retries over 2 hours, then 48-hour escrow hold with WhatsApp alert|
|Payout exceeds actual loss|Capped at min(tier coverage amount, disruption ratio × baseline)|

</details>

<details>
<summary><b>⚙️ View System Reliability Edge Cases</b></summary>

|Edge Case|Resolution|
|-|-|
|Weather API outage|4-layer redundancy — SLA payout only after all 4 layers fail > 30 mins|
|Conflicting API signals|Environmental signals weighted higher than platform signals (platform lags 20-30 mins)|
|Worker changes phone number|New number must verify old UPI + selfie match before transfer|

</details>

---

## 13\. Special Features

### 🗺️ Live Disruption Heatmap

Admin dashboard shows a real-time pin-code level map of Karnataka with DCI scores colour-coded by zone. Active payouts fire visually on the map as they process. Predicted high-risk zones for the next 24 hours shown in a forecast overlay. This is GigKavach's live demo moment — trigger a simulated rainstorm, watch the map turn red, watch payouts fire in real time.

### ⚡ Surge Protection Multiplier

Food delivery platforms issue surge pricing when demand spikes — ironically, demand spikes most during bad weather, exactly when disruptions are most likely. GigKavach detects active surge zones and automatically increases the coverage multiplier for that window. If a worker was earning more during surge, they lose more during disruption — GigKavach protects proportionally more.

```
Normal earnings baseline: ₹700/day
Surge multiplier: 1.5x during 7PM–10PM
Disruption hits during surge window:
Coverage = 60% × (₹700 × 1.5 window factor) = proportionally higher payout
```

### 🌙 Night Shift Worker Support

Shift windows are personalised per worker. Night shift workers (6PM–2AM) have their eligibility and payout calculations anchored to their actual working hours, not a default daytime window. Workers can update their shift every week via `SHIFT` command. A 2AM disruption that a night shift worker was actively working through is covered. The same disruption for a morning shift worker is not.

### 🔄 Platform Integration Hook (B2B Path)

GigKavach's admin dashboard includes a mock "Zomato Partner Benefits" integration page demonstrating how the platform can be offered as a white-label benefit to delivery workers directly through their app. One platform deal = instant access to hundreds of thousands of workers. This is the production go-to-market path.

---

## 14\. Multilingual Support

GigKavach supports **5 languages** because a financial safety net that workers cannot understand is not a safety net.

|Language|Script|Target Community|
|-|-|-|
|English|Latin|Urban educated workers|
|ಕನ್ನಡ Kannada|Kannada|Local Karnataka workers|
|हिंदी Hindi|Devanagari|North Indian migrant workers (largest segment in Bengaluru)|
|தமிழ் Tamil|Tamil|Tamil Nadu workers in Bengaluru|
|తెలుగు Telugu|Telugu|Andhra/Telangana workers in Bengaluru|

Language is selected at onboarding Step 0 and can be changed anytime via the `LANG` command. All 30 worker-facing messages — onboarding, alerts, payout confirmations, weekly updates — are pre-translated and stored in a static dictionary. No runtime translation API calls. Instant, free, reliable.

> *"बंद आपके ज़ोन में डिटेक्ट हुआ। ₹280 आपके UPI में भेजा जा रहा है।"* — This is what protection actually feels like to a Hindi-speaking delivery partner.

---

## 15\. Tech Stack

|Layer|Technology|Purpose|
|-|-|-|
|Frontend|React.js + TailwindCSS|Admin dashboard + Worker PWA|
|Backend|FastAPI (Python)/NodeJS|API endpoints, webhook handler, DCI engine|
|Database|Supabase (PostgreSQL)|All persistent data — workers, policies, payouts|
|Cache|Upstash Redis|DCI score cache + payout deduplication lock|
|ML|scikit-learn + XGBoost|Payout calculation + fraud detection|
|NLP|HuggingFace Transformers|Social disruption classification from RSS feeds|
|WhatsApp|Twilio WhatsApp Sandbox|Worker interface — onboarding, alerts, confirmations|
|SMS Fallback|Twilio SMS|Workers without WhatsApp|
|Payments|Razorpay Test Mode|UPI payout simulation|
|Maps|Leaflet.js + OpenStreetMap|Live disruption heatmap|
|Hosting|Render.com (Backend) + Vercel (Frontend)|Free tier, always-on|
|Weather|Tomorrow.io + Open-Meteo + IMD RSS|DCI weather component|
|AQI|AQICN + CPCB|DCI air quality component|
|Disasters|NDMA RSS + USGS + KSNDMC|DCI natural disaster override|
|Social|Deccan Herald RSS + The Hindu RSS|DCI social disruption component|
|Geocoding|MAPPLS + OSM Nominatim + Karnataka GeoJSON|Zone assignment from GPS|

---

## 16\. API Integrations

<details>
<summary><b>🔌 View Full API Integration Table</b></summary>

|API|Type|DCI Component|Cost|
|-|-|-|-|
|Digilocker API|Verification|Log in|Free|
|Tomorrow.io|Weather — hyperlocal|Rainfall + Heat (primary)|Free (500 calls/day)|
|Open-Meteo|Weather — forecast|7-day prediction + fallback|Free (unlimited)|
|IMD RSS|Weather — official alerts|Red/Orange alert override|Free|
|AQICN|Air quality|AQI component|Free token|
|CPCB Dashboard|Air quality — official|Cross-validation|Free (scrape)|
|NDMA RSS|Natural disasters|Disaster override|Free|
|USGS Earthquake|Seismic events|Disaster override|Free (no limits)|
|KSNDMC|Karnataka-specific floods|Local disaster|Free (scrape)|
|Deccan Herald RSS|Karnataka news|Social disruption|Free|
|The Hindu Karnataka RSS|Karnataka news|Social disruption cross-check|Free|
|OSM Nominatim|Reverse geocoding|Zone assignment|Free|
|Karnataka GeoJSON|Boundary polygons|Zone assignment|Free (static file)|
|Twilio WhatsApp|Messaging|Worker interface|Free trial ($15)|
|Razorpay|UPI payouts|Payout processing|Free test mode|
|Upstash Redis|Caching|DCI cache + locks|Free (10k calls/day)|

</details>

**Total API cost for hackathon: ₹0**

---

## 17\. Database Design

GigKavach uses **8 tables** in Supabase PostgreSQL. Data is stored for exactly as long as needed and no longer.

<details>
<summary><b>🗄️ View Full Database Schema</b></summary>

|Table|Retention|Purpose|
|-|-|-|
|`workers`|Permanent|Worker identity, language, shift, UPI, GigScore|
|`policies`|Permanent|Weekly policy records per worker|
|`activity_log`|4 weeks rolling|Raw daily login activity — source of truth for baselines|
|`activity_history`|Current only|Computed weekly summary (avg start/end/hours per day)|
|`dci_events`|30 days|Disruption log per zone — triggers and scores|
|`payouts`|Permanent|Every payout record — audit trail, never deleted|
|`fraud_flags`|Permanent|All fraud signals — never deleted|
|`api_health_log`|7 days|API uptime tracking for SLA breach eligibility|

</details>

**Why 4 weeks for activity log?** All eligibility checks, baseline calculations, and intent verification reference "last 4 weeks." Storing more wastes space. Storing less breaks the formulas. 4 weeks is the exact minimum correct answer.

**Storage estimate for demo:** ~20MB total against 500MB free tier. Cost: ₹0.

---

## 18\. Six-Week Development Roadmap

### Phase 1 — March 4–20: Ideation \& Foundation ✅

* [x] Problem research and persona definition
* [x] DCI formula design and component selection
* [x] Weekly premium model design
* [x] Parametric trigger thresholds defined
* [x] Tech stack selection
* [x] Edge case documentation (27 cases)
* [x] API research and Karnataka coverage assessment
* [x] Database schema design
* [x] WhatsApp conversation flow design
* [x] Adversarial defense \& anti-spoofing strategy
* [x] README documentation

### Phase 2 — March 21–April 4: Automation \& Protection

* [ ] FastAPI backend setup + Supabase integration
* [ ] WhatsApp webhook handler (Twilio)
* [ ] Full onboarding conversation flow (5 languages)
* [ ] DCI engine with 4-layer redundancy
* [ ] XGBoost payout model (synthetic training data)
* [ ] Dynamic payout calculation API
* [ ] Policy management system
* [ ] Claims auto-trigger pipeline
* [ ] Razorpay test mode payout integration
* [ ] Worker dashboard (PWA)

### Phase 3 — April 5–17: Scale \& Optimise

* [ ] Isolation Forest fraud detection model
* [ ] GPS validation layer
* [ ] Claim clustering detection
* [ ] Three-tier penalization system
* [ ] Appeals workflow
* [ ] Live disruption heatmap (Leaflet.js)
* [ ] Insurer analytics dashboard
* [ ] Disruption forecast feature
* [ ] GigScore implementation
* [ ] Surge protection multiplier
* [ ] Solidarity pool
* [ ] Full end-to-end demo recording

---

## 19\. Team

**Team Quadcore** — Guidewire DEVTrails 2026

|Name|Role|
|-|-|
|Varshit|Backend + DCI Engine|
|Vijeth|ML Models + Fraud Detection|
|V Saatwik|Frontend + Dashboard|
|Sumukh Shandilya|WhatsApp Interface + API Integrations|

📁 Repository: [https://github.com/VG2476/DEVTrails](https://github.com/VG2476/DEVTrails)

---

## 20\. Demo Video

📹 **Phase 1 Demo Video:** <br>  https://drive.google.com/file/d/14i5vJTVcu6uJG37t0oL7duJEv63TAdXr/view?usp=sharing

The video covers:

* Ravi's story — the problem in 30 seconds
* DCI concept explanation
* WhatsApp onboarding flow mockup
* Weekly premium model walkthrough
* Tech stack overview
* 6-week execution plan

---

## 21\. Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                        GIGKAVACH                                │
│         Zero-Touch Parametric Income Protection                 │
│              for India's Food Delivery Workers                  │
└─────────────────────────────────────────────────────────────────┘

  WHO      →  Zomato/Swiggy delivery partners.

  WHAT     →  Automatic income protection when disruptions hit
               No claim. No form. No waiting.

  HOW      →  DCI Engine scores parameters every 5 minutes
               DCI ≥ 65 → payout calculated EOD and fired to UPI.

  PRICE    →  ₹69 / ₹89 / ₹99 per week (fixed tiers)
               Payout amounts dynamically calculated via XGBoost.

  INTERFACE → WhatsApp-first. No app download required.
               Works on any ₹5,000 Android with internet.

  LANGUAGES → English · ಕನ್ನಡ · हिंदी · தமிழ் · తెలుగు

  FRAUD    →  Isolation Forest · GPS validation · Cluster detection
               3-tier penalization · Full appeals process

  EDGE CASES → 27 documented · Moral hazard prevention built-in
                Night shift support · Multi-day disaster handling

  STACK    →  FastAPI · React · Supabase · Redis · XGBoost
               Twilio · Razorpay · Tomorrow.io · Leaflet.js

  COST     →  ₹69–₹99/week for workers
               ₹0 in API costs during development

┌─────────────────────────────────────────────────────────────────┐
│  When a storm hits Koramangala at 2PM on a Tuesday,             │
│  Ravi gets a WhatsApp alert. By end of day, ₹280 lands          │
│  in his UPI account. He didn't file a claim.                    │
│  He didn't call anyone. He just stayed safe.                    │  
│                                                                 │
│  That is GigKavach.                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

*Built with ❤️
by Team Quadcore for Guidewire DEVTrails 2026
Varshit · Vijeth · V Saatwik · Sumukh Shandilya*

