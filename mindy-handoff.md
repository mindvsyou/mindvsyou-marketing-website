# Mindy handoff: add the mascot to quiz.mindvsyou.io

Paste this whole file to the Claude working on the quiz app repo. Source of truth is the marketing repo
(`mindvsyou-marketing-website`), files `mindy.svg`, `style.css` (lines 80-97) and `home.css` (lines 84-89).
If you can read that repo, copy `mindy.svg` byte-for-byte. Otherwise use the code below.

## Who Mindy is

Mindy is the MindVsYou chat buddy for CBSE Class 10 students (mostly under 18). She is a small green
robot: rounded green head with a dark "screen" face, glowing white capsule eyes, mint smile, two side
"headphone" ears, an **orange antenna ball with a white M**, and a torso with a white chat-bubble badge.

- Palette: green `#25D366` / `#3ED67B` / `#1FB559` / `#1AAE54`, orange `#FF6B2B`, navy `#0D1B2A`, white, mint `#EAFBF1`.
- Fonts on the site: Poppins 700/800 (display), Plus Jakarta Sans 400-600 (body).
- Voice: friendly, first person, short. "Mindy here." / "Hi, I am Mindy, your study assistant."
  Say "chat-style practice". Do NOT claim "AI tutor" (the product is a chat-style quiz with basic tracking).
- Sell the benefit; never bluntly state restrictions (e.g. not "Requires login").

## Rules (learned the hard way)

1. **Solid fills only in the SVG.** No gradients, no `url(#id)` paint servers, no filters inside `mindy.svg`.
   iPhone Safari cannot resolve them through an external `<use>` and shapes render empty. Chrome hides this bug.
   Test on a real iPhone or ask the owner for a phone screenshot after any SVG change.
2. **Never use the `think` pose on a page.** It looks sad/worried to the owner. Use only happy poses:
   `sit`, `cheer`, `wave`, `hint`, `face`.
3. **Sparingly.** The owner prefers less clutter. One Mindy per view/moment is plenty.
4. Decorative use: `aria-hidden="true" focusable="false"` on the `<svg>`; put meaning in the adjacent text.
5. No analytics or personal data involved. If any Mindy element is clickable and you add tracking, never send names,
   student IDs, phones or emails (DPDP Act, users are children).
6. Respects `prefers-reduced-motion` (already handled inside the SVG's own `<style>`).

## Poses and where to use them in the quiz

| Pose | ID | Use in quiz app |
|---|---|---|
| Head only | `#face` | Round chat avatar next to bot messages, nav/header logo, loading state |
| Cheer (arms up, sparkles, open smile) | `#cheer` | Correct answer feedback, quiz finished / good score |
| Hint (orange "redo" badge) | `#hint` | A missed question comes back / "Want to retry the ones you missed?" |
| Wave | `#wave` | Welcome / login greeting / empty state |
| Sit (perched on a button edge, dangling feet) | `#sit` | On top of the main CTA button (e.g. "Start Practice") |
| ~~Think~~ | `#think` | **Do not use** |

Mirror the marketing site's chat demo: bot message rows are `[Mindy avatar] [white bubble]`, a correct
answer shows `cheer` beside a mint feedback bubble, and missed questions show `hint` beside a bubble like
"You missed **4 Electricity** and **2 Life Processes** questions. Want to try them again?"

## How to embed

Serve `mindy.svg` as a static file at the app root (put it in `public/` or whatever the framework serves
as-is, so it is same-origin at `/mindy.svg`). Then reference a pose by fragment:

```html
<!-- full-body poses: viewBox 0 0 130 130 -->
<svg class="mindy" viewBox="0 0 130 130" aria-hidden="true" focusable="false"><use href="/mindy.svg#cheer"/></svg>

<!-- head-only avatar: use the cropped viewBox -->
<svg viewBox="3 2 114 108" aria-hidden="true" focusable="false"><use href="/mindy.svg#face"/></svg>
```

`<use>` with an external file must be same-origin. If the framework bundles or hashes static assets, or
the app is a SPA where that is awkward, inline the `<defs>` block once in the HTML shell (hidden
`<svg width="0" height="0" style="position:absolute">`) and use `<use href="#cheer"/>`. In that case, keep the
`<style>` block too. Do not use the SVG as an `<img>` if you want the pose selection; `<img>` only shows the
(empty) default.

## CSS (from the marketing site; adjust variable names to the quiz app's tokens)

```css
:root { --green:#25D366; --green-dark:#1AAE54; --orange:#FF6B2B; --navy:#0D1B2A; --border:#E2E8F0; --mint:#EAFBF1; }

/* Mindy, the chat buddy */
.mindy { display: block; width: 100%; height: auto; overflow: visible; }

/* Mindy sitting on top of a CTA button */
.sitbtn { position: relative; }
.sitter { position: absolute; right: 26px; bottom: calc(100% - 12px); width: 78px; pointer-events: none; filter: drop-shadow(0 8px 12px rgba(13,27,42,.22)); }
.sitwrap { position: relative; display: inline-block; }   /* wrap the button when adding the greeting bubble */

/* "Hi, I am Mindy" speech bubble to the left of the sitting Mindy */
.mindy-hi { position: absolute; right: calc(26px + 78px + 12px); bottom: calc(100% + 14px); width: max-content; max-width: min(200px, calc(100% - 118px)); background: #fff; color: var(--navy); font-size: .86rem; font-weight: 700; line-height: 1.3; padding: 8px 12px; border-radius: 14px 14px 4px 14px; box-shadow: 0 8px 20px rgba(0,0,0,.25); }
.mindy-hi::after { content: ''; position: absolute; right: -6px; bottom: 12px; border: 6px solid transparent; border-right: 0; border-left-color: #fff; }

/* "Mindy here" callout: big Mindy beside a speech bubble */
.mindy-say { display: flex; align-items: flex-end; gap: 14px; margin: 30px 0 34px; }
.mindy-say .mindy { width: 92px; flex: none; }
.mindy-say-b { position: relative; background: #fff; border: 1.5px solid var(--border); border-radius: 20px 20px 20px 5px; padding: 18px 20px 20px; box-shadow: 0 10px 30px rgba(13,27,42,.07); }
@media (max-width: 560px) { .mindy-say { flex-direction: column; align-items: flex-start; } .mindy-say .mindy { width: 76px; } .mindy-say-b { border-radius: 20px; } }

/* Chat rows: small Mindy beside a bot bubble */
.hm-brow { display: flex; align-items: flex-end; gap: 8px; max-width: 100%; }
.hm-brow .mini { width: 36px; flex: none; }
.hm-brow .hm-b { max-width: calc(100% - 46px); }

/* Chat bubbles */
.hm-b { max-width: 88%; padding: 11px 14px; border-radius: 18px; font-size: .88rem; line-height: 1.45; }
.hm-b.bot { background: #fff; border: 1px solid var(--border); border-top-left-radius: 5px; }
.hm-b.me  { background: var(--navy); color: #fff; border-top-right-radius: 5px; align-self: flex-end; }
.hm-b.fb  { background: var(--mint); border-color: #b9ecd0; }   /* correct-answer feedback */
.hm-b.fb b { color: var(--green-dark); }

/* Round avatar holding the head-only pose */
.hm-av { width: 40px; height: 40px; border-radius: 50%; background: var(--mint); overflow: hidden; flex: none; }
.hm-av svg { display: block; width: 100%; height: 100%; }

/* Mindy peeks over the top of a header/nav button (head only, bottom 30% clipped) */
.nav-cta { position: relative; }
.nav-peek { position: absolute; left: 50%; bottom: calc(100% - 6.5px); width: 22px; height: auto; display: block; clip-path: inset(0 0 30% 0); pointer-events: none; transform: translateX(-50%); transition: transform .2s ease; }
.nav-cta:hover .nav-peek { transform: translateX(-50%) translateY(-3px); }
```

## Markup patterns used on the marketing site

```html
<!-- Sitting on the primary CTA button -->
<div class="sitwrap">
  <span class="mindy-hi">Hi, I am Mindy, your study assistant</span>   <!-- optional greeting -->
  <a href="#" class="btn btn-green sitbtn">
    <svg class="mindy sitter" viewBox="0 0 130 130" aria-hidden="true" focusable="false"><use href="/mindy.svg#sit"/></svg>
    Start Practice
  </a>
</div>

<!-- Correct answer feedback -->
<div class="hm-brow">
  <svg class="mindy mini" viewBox="0 0 130 130" aria-hidden="true" focusable="false"><use href="/mindy.svg#cheer"/></svg>
  <div class="hm-b bot fb"><b>✓ Correct!</b> Zinc displaces hydrogen from the acid, so hydrogen gas is released.</div>
</div>

<!-- Missed questions come back -->
<div class="hm-brow">
  <svg class="mindy mini" viewBox="0 0 130 130" aria-hidden="true" focusable="false"><use href="/mindy.svg#hint"/></svg>
  <div class="hm-b bot">You missed <b>4 Electricity</b> and <b>2 Life Processes</b> questions. Want to try them again?</div>
</div>

<!-- Chat avatar -->
<div class="hm-av"><svg viewBox="3 2 114 108" aria-hidden="true" focusable="false"><use href="/mindy.svg#face"/></svg></div>

<!-- "Mindy here" callout -->
<div class="mindy-say">
  <svg class="mindy" viewBox="0 0 130 130" aria-hidden="true" focusable="false"><use href="/mindy.svg#cheer"/></svg>
  <div class="mindy-say-b"><p><strong>Mindy here.</strong> ...</p></div>
</div>
```

Notes: the sit pose's feet dangle below the button's top edge; keep `.sitter { bottom: calc(100% - 12px) }` and
leave ~56px of space above the button (`margin-top`) so she is not clipped by the element above.
Head-only avatars use `viewBox="3 2 114 108"`; full-body poses use `viewBox="0 0 130 130"`.

## Suggested minimum for the quiz app

1. Copy `mindy.svg` to the app's static root and add the `.mindy` CSS above.
2. Correct answer: `cheer` + mint feedback bubble.
3. Wrong answer / missed questions coming back: `hint`.
4. Chat-style question screen: `face` avatar on bot messages.
5. Home / start screen: `sit` on the main CTA. Optionally a `wave` greeting on first load.
6. Keep everything else clean. Check on iPhone Safari.

## mindy.svg (full source, copy exactly)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 130 130">
  <!-- Mindy, the MindVsYou chat buddy. Use with: <svg viewBox="0 0 130 130"><use href="mindy.svg#wave"/></svg>
       Poses: #face (head only, for avatars), #wave, #think, #cheer, #hint, #sit (perched on a button) -->
  <style>
    .mindy-eyes { transform-box: fill-box; transform-origin: center; animation: mindy-blink 4.6s infinite; }
    .mindy-hand { transform-origin: 82px 106px; animation: mindy-wave 1.5s ease-in-out infinite; }
    .mindy-pop { transform-box: fill-box; transform-origin: center; animation: mindy-pop 1.8s ease-in-out infinite; }
    .mindy-ant { transform-box: fill-box; transform-origin: center; animation: mindy-glow 2.4s ease-in-out infinite; }
    @keyframes mindy-blink { 0%, 92%, 100% { transform: scaleY(1); } 95% { transform: scaleY(.1); } }
    @keyframes mindy-wave { 0%, 100% { transform: rotate(0); } 50% { transform: rotate(-14deg); } }
    @keyframes mindy-pop { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(.65); opacity: .6; } }
    @keyframes mindy-glow { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.18); } }
    @media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
  </style>

  <defs>

    <!-- antenna, ears, head and screen shared by every pose -->
    <g id="m-head">
      <line x1="60" y1="26" x2="60" y2="13" stroke="#0D1B2A" stroke-width="4" stroke-linecap="round"/>
      <g class="mindy-ant">
        <circle cx="60" cy="11" r="10" fill="#FF6B2B" stroke="#fff" stroke-width="2.5"/>
        <path d="M55 15.5 L55 6.5 L60 11 L65 6.5 L65 15.5" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
      <rect x="7" y="52" width="12" height="26" rx="6" fill="#0D1B2A"/>
      <rect x="101" y="52" width="12" height="26" rx="6" fill="#0D1B2A"/>
      <rect x="9.5" y="57" width="3" height="10" rx="1.5" fill="#25D366" opacity=".9"/>
      <rect x="107.5" y="57" width="3" height="10" rx="1.5" fill="#25D366" opacity=".9"/>
      <rect x="16" y="24" width="88" height="80" rx="31" fill="#3ED67B" stroke="#fff" stroke-width="4"/>
      <rect x="18" y="26" width="84" height="38" rx="29" fill="#fff" opacity=".13"/>
      <path d="M27 42 Q29 33 41 31" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round" opacity=".55"/>
      <rect x="25" y="36" width="70" height="54" rx="23" fill="#0F2134" stroke="#2C4B66" stroke-width="1.2"/>
      <circle cx="35" cy="78" r="5" fill="#FF6B2B" opacity=".38"/>
      <circle cx="85" cy="78" r="5" fill="#FF6B2B" opacity=".38"/>
    </g>
    <!-- torso with a chat-bubble badge -->
    <g id="m-body">
      <rect x="34" y="96" width="52" height="28" rx="14" fill="#1FB559" stroke="#fff" stroke-width="3"/>
      <rect x="49" y="103" width="22" height="14" rx="6" fill="#fff"/>
      <path d="M54 116 L52 122 L60 116Z" fill="#fff"/>
      <circle cx="55" cy="110" r="1.7" fill="#0D1B2A"/><circle cx="60" cy="110" r="1.7" fill="#0D1B2A"/><circle cx="65" cy="110" r="1.7" fill="#0D1B2A"/>
    </g>
    <!-- default glowing capsule eyes -->
    <g id="m-eyes">
      <rect x="38" y="46" width="16" height="22" rx="8" fill="#25D366" opacity=".28"/>
      <rect x="66" y="46" width="16" height="22" rx="8" fill="#25D366" opacity=".28"/>
      <rect x="40.5" y="49" width="11" height="16" rx="5.5" fill="#fff"/>
      <rect x="68.5" y="49" width="11" height="16" rx="5.5" fill="#fff"/>
      <circle cx="48.5" cy="53.5" r="2" fill="#B9FFD6"/><circle cx="76.5" cy="53.5" r="2" fill="#B9FFD6"/>
    </g>
    <path id="m-smile" d="M50 74 Q60 83 70 74" stroke="#5BE897" stroke-width="4" fill="none" stroke-linecap="round"/>
    <path id="m-spark" d="M0-8 L2.4-2.4 L8 0 L2.4 2.4 L0 8 L-2.4 2.4 L-8 0 L-2.4-2.4Z" fill="#FF6B2B"/>
    <g id="m-arm-down-l">
      <path d="M36 108 Q26 112 22 120" stroke="#1AAE54" stroke-width="9" fill="none" stroke-linecap="round"/>
      <circle cx="21" cy="121" r="6.5" fill="#fff" stroke="#1AAE54" stroke-width="1.5"/>
    </g>
    <g id="m-arm-down-r">
      <path d="M84 108 Q94 112 98 120" stroke="#1AAE54" stroke-width="9" fill="none" stroke-linecap="round"/>
      <circle cx="99" cy="121" r="6.5" fill="#fff" stroke="#1AAE54" stroke-width="1.5"/>
    </g>

    <!-- face only: for round avatars -->
    <g id="face">
      <use href="#m-head"/>
      <g class="mindy-eyes"><use href="#m-eyes"/></g>
      <use href="#m-smile"/>
    </g>

    <!-- wave: greeting -->
    <g id="wave">
      <use href="#m-arm-down-l"/>
      <use href="#m-body"/>
      <use href="#m-head"/>
      <g class="mindy-eyes"><use href="#m-eyes"/></g>
      <use href="#m-smile"/>
      <g class="mindy-hand">
        <path d="M82 108 Q110 106 116 82" stroke="#1AAE54" stroke-width="9" fill="none" stroke-linecap="round"/>
        <circle cx="116" cy="76" r="8" fill="#fff" stroke="#1AAE54" stroke-width="1.5"/>
      </g>
    </g>

    <!-- sit: perches on the edge of a button (feet dangle below the edge line at y=109) -->
    <g id="sit">
      <rect x="44" y="102" width="11" height="20" rx="5.5" fill="#1FB559" stroke="#fff" stroke-width="2"/>
      <rect x="65" y="102" width="11" height="20" rx="5.5" fill="#1FB559" stroke="#fff" stroke-width="2"/>
      <ellipse cx="49" cy="123.5" rx="8" ry="4.5" fill="#0D1B2A"/>
      <ellipse cx="71" cy="123.5" rx="8" ry="4.5" fill="#0D1B2A"/>
      <g transform="translate(6 -2) scale(.9)">
        <use href="#m-arm-down-l"/>
        <use href="#m-body"/>
        <use href="#m-head"/>
        <g class="mindy-eyes"><use href="#m-eyes"/></g>
        <use href="#m-smile"/>
        <g class="mindy-hand">
          <path d="M82 108 Q110 106 116 82" stroke="#1AAE54" stroke-width="9" fill="none" stroke-linecap="round"/>
          <circle cx="116" cy="76" r="8" fill="#fff" stroke="#1AAE54" stroke-width="1.5"/>
        </g>
      </g>
    </g>

    <!-- think: working out a question (DO NOT USE on pages, looks sad) -->
    <g id="think">
      <use href="#m-arm-down-l"/>
      <use href="#m-body"/>
      <use href="#m-head"/>
      <path d="M82 108 Q104 110 98 96" stroke="#1AAE54" stroke-width="9" fill="none" stroke-linecap="round"/>
      <circle cx="97" cy="93" r="6.5" fill="#fff" stroke="#1AAE54" stroke-width="1.5"/>
      <g class="mindy-eyes">
        <rect x="40" y="48" width="12" height="17" rx="6" fill="#fff"/><rect x="68" y="48" width="12" height="17" rx="6" fill="#fff"/>
        <circle cx="48" cy="52.5" r="3.6" fill="#0D1B2A"/><circle cx="76" cy="52.5" r="3.6" fill="#0D1B2A"/>
      </g>
      <path d="M38 44 L54 42 M66 39 L82 43" stroke="#fff" stroke-width="3" stroke-linecap="round"/>
      <path d="M54 75 L66 75" stroke="#5BE897" stroke-width="4" stroke-linecap="round"/>
      <circle cx="108" cy="32" r="3" fill="#0D1B2A" opacity=".55"/>
      <circle cx="114" cy="24" r="4" fill="#0D1B2A" opacity=".55"/>
      <rect x="98" y="1" width="30" height="18" rx="9" fill="#fff" stroke="#0D1B2A" stroke-width="2"/>
      <circle cx="106" cy="10" r="2" fill="#0D1B2A"/><circle cx="113" cy="10" r="2" fill="#0D1B2A"/><circle cx="120" cy="10" r="2" fill="#0D1B2A"/>
    </g>

    <!-- cheer: correct answer -->
    <g id="cheer">
      <path d="M38 106 Q14 104 9 80" stroke="#1AAE54" stroke-width="9" fill="none" stroke-linecap="round"/>
      <path d="M82 106 Q106 104 111 80" stroke="#1AAE54" stroke-width="9" fill="none" stroke-linecap="round"/>
      <circle cx="9" cy="74" r="8" fill="#fff" stroke="#1AAE54" stroke-width="1.5"/><circle cx="111" cy="74" r="8" fill="#fff" stroke="#1AAE54" stroke-width="1.5"/>
      <use href="#m-body"/>
      <use href="#m-head"/>
      <g class="mindy-eyes">
        <path d="M38 62 Q46 47 54 62 M66 62 Q74 47 82 62" stroke="#fff" stroke-width="4.5" fill="none" stroke-linecap="round"/>
      </g>
      <path d="M46 70 Q60 93 74 70 Z" fill="#fff"/>
      <path d="M54 80 Q60 75 66 80 Q60 87 54 80Z" fill="#FF6B2B"/>
      <use class="mindy-pop" href="#m-spark" x="22" y="20"/>
      <use class="mindy-pop" href="#m-spark" x="106" y="18"/>
      <circle cx="30" cy="8" r="2.5" fill="#25D366"/><circle cx="96" cy="6" r="2.5" fill="#FF6B2B"/>
      <circle cx="4" cy="46" r="2.5" fill="#FF6B2B"/><circle cx="126" cy="46" r="2.5" fill="#25D366"/>
    </g>

    <!-- hint: a missed question comes back -->
    <g id="hint">
      <use href="#m-arm-down-l"/>
      <use href="#m-arm-down-r"/>
      <use href="#m-body"/>
      <use href="#m-head"/>
      <g class="mindy-eyes"><use href="#m-eyes"/></g>
      <path d="M38 47 L53 43 M67 43 L82 47" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".85"/>
      <path d="M51 74 Q60 80 69 74" stroke="#5BE897" stroke-width="4" fill="none" stroke-linecap="round"/>
      <circle cx="108" cy="24" r="15" fill="#FF6B2B" stroke="#fff" stroke-width="3"/>
      <path d="M101 25 A7.5 7.5 0 1 1 105 31" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M97 21 L101.5 27.5 L106 20.5Z" fill="#fff"/>
    </g>
  </defs>
</svg>
```
