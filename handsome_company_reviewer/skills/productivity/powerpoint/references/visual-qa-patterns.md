# Visual-QA Pattern Catalog

A deeper catalog of overlap / cut-off / misalignment patterns that vision QA should actively search for. Each pattern lists the **failure signature** (what to look for in the rendered PNG), the **root cause** (the typical python-pptx mistake), and the **fix recipe**.

Use this as a checklist when the high-level 10-item checklist in `SKILL.md §C` flags something — drill down here to see what shape it might be.

---

## Pattern 1 — Big glyph overlaps title text

**Signature:** A decorative `"` (open-quote) or other tall character sits on top of the second line of body text.

**Root cause:** Quoted text where the opening quote mark is in its own `textbox()` at a fixed `top`, sized larger than the quote's actual baseline. The glyph's descender / crossbar overlaps the next line.

**Fix:** Either drop the quote entirely, or place it in a small box ABOVE the quote (not BESIDE), and match the box height to the glyph's cap-height, not its em-square. Rule of thumb: if the glyph's `size` is more than ~1.5× the body text size, you need a custom placement.

---

## Pattern 2 — Caveat text rendered ON TOP of a rounded-rect border line

**Signature:** Bottom-edge text intersects the lower horizontal line of a container box; you can see the line going through the middle of the text characters.

**Root cause:** Container `add_rounded_rect(top=X, height=H)` and a `textbox(top=X', anchor='b')` placed close together. The `anchor='b'` puts text against the bottom of the textbox, but if `X'` + textbox_height extends below the rect's bottom edge, the text crosses the line.

**Fix:** Two options, both valid:
- Move the textbox `top` to be ≥ rect_top + rect_height (text entirely below the rect)
- Or move the textbox to be entirely INSIDE the rect (text below the rect bottom by enough to clear the border)

A good rule: when stacking elements vertically, ensure each element's `top + height` is `<= next_element's top - 0.05 in` (small gap).

---

## Pattern 3 — Callout bar placed at exact same y as card bottom

**Signature:** A dark "callout" / "footer" / "highlight" rectangle appears to overlap or share a border with the card grid above it.

**Root cause:** The callout's `top` is computed as `card_top + card_height + row_gap`, but a typo or off-by-one drops it to `card_top + card_height` — sharing the border.

**Fix:** Verify the math at design time. The 6-card 2×3 grid is the worst offender:
- row 1: `top=2.1, height=2.0` → bottom at 4.1
- gap_y: 0.20
- row 2: `top=4.30, height=2.0` → bottom at 6.30
- callout: `top >= 6.40` (10-EMU gap)

The gap must be **additive**, not subtracted. If you set `cell_h = 2.1` and `gap = 0.2` you get row 2 ending at 6.50, callout needing `top >= 6.55`. Mistakes here are silent — they only show in render.

---

## Pattern 4 — Bottom anchor text overlapping the card's rounded bottom corners

**Signature:** An "anchor" / "summary" / "footer caption" line at the bottom of a slide touches or crosses into a card's bottom rounded corner.

**Root cause:** Anchor textbox placed with `top >= card_bottom` but the textbox is wider than the gap between cards. The text wraps, overflows upward, or visually clips into the card border.

**Fix:** Two strategies, pick based on slide layout:
- Shrink cards: `cell_h = card_h - delta`, so the gap below them grows
- Move anchor down: `anchor_top = card_bottom + 0.1`, but verify the **footer bar** (at 7.10-7.30) is not yet reached

If the anchor is itself meant to be in a band, place it INSIDE its own thin rounded-rect (matches design language) — then the card-vs-anchor relationship becomes "rect above rect", which is much easier to reason about than "textbox spilling".

---

## Pattern 5 — Footer bar at very bottom collides with elements above

**Signature:** A "thin gold accent line" + "footer text" + "page number" all stacked at the bottom of the slide, with text cut off at the very bottom edge or accent line going through text.

**Root cause:** Footer bar placed at `top=7.20` (slide is 7.5 in tall), and textbox placed at `top=7.28` (with `height=0.22`). The text is in the 0.08-in gap between footer top and slide bottom — but default textbox height doesn't fit 11pt text in 0.22 in. Result: text gets clipped.

**Fix:** Standard footer geometry for 16:9:
- Footer bar: `top=7.10, height=0.20` (7.10–7.30 in)
- Footer textbox: `top=7.16, height=0.25` — overlap with bar is intentional (text sits on bar)
- Page number: same band, right-aligned, width=3.5 in, left=9.5 in
- **Leave 7.30-7.50 in EMPTY** — no content, slide bottom margin

This isn't a "watermark" issue — it's that PPT has no concept of safe area, you have to enforce it.

---

## Pattern 6 — Bullet dot circles bleeding outside card

**Signature:** A "•" / numbered circle sits half-outside the card border.

**Root cause:** Bullet position computed as `bullet_x = card_left + 0.3`, oval size = 0.18. The card's rounded corner is at radius ~0.10 in. If the card's left border is at `card_left` and the bullet center is at `card_left + 0.3 + 0.09` (radius), the bullet is at `card_left + 0.39` center. The card's right edge ends at `card_left + card_w`. If `card_w < 0.6` (e.g. very narrow 3-column layout), the bullet could overflow right.

**Fix:** Bullet x must satisfy: `bullet_x + bullet_size <= card_left + card_w - 0.1` (leave 0.1 in margin from right edge). For 3-column cards with `card_w = 4.0`, that's `bullet_x <= card_left + 3.72`. With `bullet_x = card_left + 0.3`, fine. But for 4-column with `card_w = 3.0`, the bullet at `card_left + 0.3 + 0.18 = card_left + 0.48` is fine but if the card is `card_w = 2.5` then bullet at `card_left + 0.3 + 0.18 = card_left + 0.48` is at 19% of card — still fine — but you get the idea, test narrow cards.

---

## Pattern 7 — Page number "11/11" cut off at very bottom

**Signature:** `loop engineering · 11/11` shows but the right edge of the "11" is cropped.

**Root cause:** Page number textbox width too small for 2-digit slide number + label. Or: textbox right margin extends past slide width (13.333 in for 16:9).

**Fix:** Right-align the textbox explicitly: `p.alignment = PP_ALIGN.RIGHT`, `left = SLIDE_W - 3.5`, `width = 3.0`. Then there's always 0.5 in of right margin to the slide edge.

---

## Pattern 8 — Single-line label wraps to two lines

**Signature:** A short label like "Q2: agent 跑得起来但不收敛?" should fit on one line but renders as:
```
Q2: agent 跑得起来但不收敛
?
```
The "?" ends up on its own line.

**Root cause:** Textbox width too narrow for the text, OR font size too large for the available width. Especially common with East Asian + Latin mixed text (Microsoft YaHei is wider than Calibri).

**Fix:** Two options:
- Shorten the text (often the better UX choice — see "Q2: 跑得起来但不收敛?" — drop the redundant "agent")
- Widen the textbox (if space allows)
- Reduce font size (sparingly — readability matters)

**Lesson:** Run text through a width-budget check during design: at 22pt with Microsoft YaHei, a Chinese char ≈ 0.30 in, ASCII char ≈ 0.15 in. If your textbox is 6.0 in, you have ~30 chars max in pure CJK, ~40 chars in pure ASCII.

---

## Pattern 9 — Stacked accent rect overlapping attribution line

**Signature:** A small accent rectangle (gold bar / line decoration) is positioned over a longer line of text. The accent covers part of the text.

**Root cause:** Two horizontal elements at the same `top` but different widths. If the accent's `left` is between the text's `left` and `right`, the rect covers the text.

**Fix:** Either (a) move the accent above or below the text, or (b) reduce accent width so it's only under the title.

---

## Pattern 10 — Card content with huge white-space gap

**Signature:** Cards have a lot of empty space below the content. The card looks "empty" or "under-filled".

**Root cause:** `card_h` is hardcoded too high, OR content is too short for the card.

**Fix:** Match `card_h` to content. If you have 3 bullets at 0.4 in each, header at 0.5 in, you need `card_h = 0.5 + 3*0.4 + 0.3 padding = 2.0 in`. If the slide has more vertical space than that, make the card SMALLER, not the content LARGER.

**Anti-pattern to avoid:** Stretching the card to fill the slide and hoping content looks balanced. It doesn't. Better to have a smaller card with comfortable padding than a big card with awkward empty space.

---

## Pattern 11 — The subtle double-fix: gitignore-style `pattern  # comment`

**Signature:** Not a PPT issue, but a corollary: when adding patterns with inline comments (e.g. in `.gitignore`), `git` (and many other parsers) does NOT support `pattern  # comment` syntax. The entire `pattern  # comment` is treated as one pattern that won't match.

**Fix:** Put the comment on its own line:
```gitignore
# this is a comment
pattern
# another comment
other-pattern
```

---

## Pattern 12 — Symlink-based subcommands fail silently on Windows

**Signature:** Bash sub-commands work on macOS/Linux but `command-not-found` on Windows git-bash, even though `ls -la` shows the file exists.

**Root cause:** `ln -sf` on Windows git-bash creates a copy (or fails silently) instead of a real symlink. The file exists but `basename $0` returns the target's basename, not the symlink's. Sub-commands dispatching on `basename $0` then route wrong.

**Fix:** On Windows, use `cp file linkname` for sub-commands, not `ln -sf`. And in the script, use a `case "$prog" in` block that matches the actual file name (the copy will have the desired name).

---

## Pattern 13 — One fix breaks another (the loop rule)

**Observation:** When you fix overlap pattern N, you often shift the y-coordinate of a region. That shift can cause new overlap with elements below it (footer, anchor, callout). One fix → 1.5 problems solved on average.

**Rule:** After EVERY fix, re-render and re-inspect the affected slide. Do not batch fixes. Do not assume. The "fix and pray" pattern is what causes users to come back with "再仔细核对一下排版".

**Minimum verification cadence:**
- 1-3 fixes: re-render all slides in the affected section
- 4-6 fixes: re-render the entire deck
- 7+ fixes: re-render and consider re-designing (might mean the layout was fundamentally off)
