---
name: apple-platform
description: "Control Apple Notes, Reminders, Find My, and iMessage from Hermes on macOS — each section is the canonical playbook for one Apple app's CLI or AppleScript integration. Use when the user wants to script a macOS Apple app (Notes, Reminders, Find My, iMessage) from Hermes. For generic macOS GUI automation across any app, use the `macos-computer-use` skill instead."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Apple, macOS, notes, reminders, findmy, imessage, imsg, memo, remindctl]
    related_skills: [macos-computer-use, obsidian]
---

# Apple Platform Integration

Class-level playbook for scripting four native Apple apps from Hermes on macOS. Each section is the canonical workflow for one app:

| App | CLI / API | Section |
|---|---|---|
| Apple Notes | `memo` (Homebrew) | [Apple Notes](#apple-notes) |
| Apple Reminders | `remindctl` (Homebrew) | [Apple Reminders](#apple-reminders) |
| Find My (devices + AirTags) | AppleScript + `peekaboo` | [Find My](#find-my) |
| iMessage / SMS | `imsg` (Homebrew) | [iMessage](#imessage) |

**Before starting any section**, make sure Terminal has the relevant macOS permissions:

- **AppleScript / Automation** — System Settings → Privacy & Security → Automation → allow Terminal to control the target app
- **Full Disk Access** (imessage history) — System Settings → Privacy & Security → Full Disk Access → add Terminal
- **Screen Recording** (findmy screenshots) — System Settings → Privacy & Security → Screen Recording → add Terminal

All four CLIs install via `brew tap` + `brew install`. If the user is on a Mac without Homebrew, the section commands won't work — point them at `https://brew.sh` first.

**Not what you need?** For generic GUI automation (click, drag, type in any Mac app via the `computer_use` tool), use the **`macos-computer-use`** skill instead. It is intentionally a separate skill because it covers a different tool family (Hermes's `computer_use` action API), not a specific Apple app.

---

## Apple Notes

Use `memo` to manage Apple Notes directly from the terminal. Notes sync across all Apple devices via iCloud.

### Prerequisites

- **macOS** with Notes.app
- Install: `brew tap antoniorodr/memo && brew install antoniorodr/memo/memo`
- Grant Automation access to Notes.app when prompted (System Settings → Privacy → Automation)

### When to Use

- User asks to create, view, or search Apple Notes
- Saving information to Notes.app for cross-device access
- Organizing notes into folders
- Exporting notes to Markdown/HTML

### When NOT to Use

- Obsidian vault management → use the `obsidian` skill
- Bear Notes → separate app (not supported here)
- Quick agent-only notes → use the `memory` tool instead

### Quick Reference

```bash
memo notes                        # List all notes
memo notes -f "Folder Name"       # Filter by folder
memo notes -s "query"             # Search notes (fuzzy)
memo notes -a                     # Interactive editor
memo notes -a "Note Title"        # Quick add with title
memo notes -e                     # Interactive selection to edit
memo notes -d                     # Interactive selection to delete
memo notes -m                     # Move note to folder (interactive)
memo notes -ex                    # Export to HTML/Markdown
```

### Limitations

- Cannot edit notes containing images or attachments
- Interactive prompts require terminal access (use pty=true if needed)
- macOS only — requires Apple Notes.app

### Rules

1. Prefer Apple Notes when user wants cross-device sync (iPhone/iPad/Mac)
2. Use the `memory` tool for agent-internal notes that don't need to sync
3. Use the `obsidian` skill for Markdown-native knowledge management

---

## Apple Reminders

Use `remindctl` to manage Apple Reminders directly from the terminal. Tasks sync across all Apple devices via iCloud.

### Prerequisites

- **macOS** with Reminders.app
- Install: `brew install steipete/tap/remindctl`
- Grant Reminders permission when prompted
- Check: `remindctl status` / Request: `remindctl authorize`

### When to Use

- User mentions "reminder" or "Reminders app"
- Creating personal to-dos with due dates that sync to iOS
- Managing Apple Reminders lists
- User wants tasks to appear on their iPhone/iPad

### When NOT to Use

- Scheduling agent alerts → use the cronjob tool instead
- Calendar events → use Apple Calendar or Google Calendar
- Project task management → use GitHub Issues, Notion, etc.
- If user says "remind me" but means an agent alert → clarify first

### Quick Reference

```bash
remindctl                    # Today's reminders
remindctl today              # Today
remindctl tomorrow           # Tomorrow
remindctl week               # This week
remindctl overdue            # Past due
remindctl all                # Everything
remindctl 2026-01-04         # Specific date
remindctl list               # List all lists
remindctl list Work          # Show specific list
remindctl list Projects --create    # Create list
remindctl list Work --delete        # Delete list
remindctl add "Buy milk"
remindctl add --title "Call mom" --list Personal --due tomorrow
remindctl add --title "Meeting prep" --due "2026-02-15 09:00"
remindctl complete 1 2 3          # Complete by ID
remindctl delete 4A83 --force     # Delete by ID
remindctl today --json       # JSON for scripting
remindctl today --plain      # TSV format
remindctl today --quiet      # Counts only
```

### Due Time vs Alarm / Early Nudge

`--due` and `--alarm` are different fields:

- `--due` sets the reminder's due date/time.
- `--alarm` sets the EventKit alarm/notification trigger. Timed due reminders may default to an alarm at the due time, but pass `--alarm` explicitly when the user asks for an earlier nudge.

For a reminder due at 2:00 PM with a notification 30 minutes earlier:

```bash
remindctl add --title "Hairdresser" --due "2026-05-15 14:00" --alarm "2026-05-15 13:30"
```

To edit an existing reminder:

```bash
remindctl edit 87354 --due "2026-05-15 14:00" --alarm "2026-05-15 13:30"
```

The Reminders UI may show or group the item by the alarm time because that is when the notification fires. Verify with JSON instead of assuming the due time moved:

```bash
remindctl today --json
```

Expected shape:

- `dueDate`: actual due time
- `alarmDate`: notification / early nudge time

Apple's public `EKReminder` docs list only reminder-specific properties. Alarm support comes from inherited `EKCalendarItem` behavior exposed by remindctl's `--alarm` flag.

### Date Formats

Accepted by `--due` and date filters:
- `today`, `tomorrow`, `yesterday`
- `YYYY-MM-DD`
- `YYYY-MM-DD HH:mm`
- ISO 8601 (`2026-01-04T12:34:56Z`)

### Rules

1. When user says "remind me", clarify: Apple Reminders (syncs to phone) vs agent cronjob alert
2. Always confirm reminder content and due date before creating
3. Use `--json` for programmatic parsing

---

## Find My

Track Apple devices and AirTags via the FindMy.app on macOS. Since Apple doesn't
provide a CLI for FindMy, this skill uses AppleScript to open the app and
screen capture to read device locations.

### Prerequisites

- **macOS** with Find My app and iCloud signed in
- Devices/AirTags already registered in Find My
- Screen Recording permission for terminal (System Settings → Privacy → Screen Recording)
- **Optional but recommended**: Install `peekaboo` for better UI automation:
  `brew install steipete/tap/peekaboo`

### When to Use

- User asks "where is my [device/cat/keys/bag]?"
- Tracking AirTag locations
- Checking device locations (iPhone, iPad, Mac, AirPods)
- Monitoring pet or item movement over time (AirTag patrol routes)

### Method 1: AppleScript + Screenshot (Basic)

```bash
# Open FindMy and wait for it to load
osascript -e 'tell application "FindMy" to activate'
sleep 3
screencapture -w -o /tmp/findmy.png
```

Then use `vision_analyze` to read the screenshot:

```
vision_analyze(image_url="/tmp/findmy.png", question="What devices/items are shown and what are their locations?")
```

Switch between tabs:

```bash
# Devices tab
osascript -e '
tell application "System Events"
    tell process "FindMy"
        click button "Devices" of toolbar 1 of window 1
    end tell
end tell'

# Items tab (AirTags)
osascript -e '
tell application "System Events"
    tell process "FindMy"
        click button "Items" of toolbar 1 of window 1
    end tell
end tell'
```

### Method 2: Peekaboo UI Automation (Recommended)

```bash
# Open Find My
osascript -e 'tell application "FindMy" to activate'
sleep 3

# Capture and annotate the UI
peekaboo see --app "FindMy" --annotate --path /tmp/findmy-ui.png

# Click on a specific device/item by element ID
peekaboo click --on B3 --app "FindMy"

# Capture the detail view
peekaboo image --app "FindMy" --path /tmp/findmy-detail.png
```

Then analyze with vision:

```
vision_analyze(image_url="/tmp/findmy-detail.png", question="What is the location shown for this device/item? Include address and coordinates if visible.")
```

### Track an AirTag Over Time

```bash
# 1. Open FindMy to Items tab
osascript -e 'tell application "FindMy" to activate'
sleep 3

# 2. Click on the AirTag item (stay on page — AirTag only updates when page is open)

# 3. Periodically capture location
while true; do
    screencapture -w -o /tmp/findmy-$(date +%H%M%S).png
    sleep 300  # Every 5 minutes
done
```

Analyze each screenshot with vision to extract coordinates, then compile a route.

### Limitations

- FindMy has **no CLI or API** — must use UI automation
- AirTags only update location while the FindMy page is actively displayed
- Location accuracy depends on nearby Apple devices in the FindMy network
- Screen Recording permission required for screenshots
- AppleScript UI automation may break across macOS versions

### Rules

1. Keep FindMy app in the foreground when tracking AirTags (updates stop when minimized)
2. Use `vision_analyze` to read screenshot content — don't try to parse pixels
3. For ongoing tracking, use a cronjob to periodically capture and log locations
4. Respect privacy — only track devices/items the user owns

---

## iMessage

Use `imsg` to read and send iMessage/SMS via macOS Messages.app.

### Prerequisites

- **macOS** with Messages.app signed in
- Install: `brew install steipete/tap/imsg`
- Grant Full Disk Access for terminal (System Settings → Privacy → Full Disk Access)
- Grant Automation permission for Messages.app when prompted

### When to Use

- User asks to send an iMessage or text message
- Reading iMessage conversation history
- Checking recent Messages.app chats
- Sending to phone numbers or Apple IDs

### When NOT to Use

- Telegram/Discord/Slack/WhatsApp messages → use the appropriate gateway channel
- Group chat management (adding/removing members) → not supported
- Bulk/mass messaging → always confirm with user first

### Quick Reference

```bash
imsg chats --limit 10 --json

# By chat ID
imsg history --chat-id 1 --limit 20 --json

# With attachments info
imsg history --chat-id 1 --limit 20 --attachments --json

# Text only
imsg send --to "+141****1212" --text "Hello!"

# With attachment
imsg send --to "+141****1212" --text "Check this out" --file /path/to/image.jpg

# Force iMessage or SMS
imsg send --to "+141****1212" --text "Hi" --service imessage
imsg send --to "+141****1212" --text "Hi" --service sms

# Watch for new messages
imsg watch --chat-id 1 --attachments
```

### Service Options

- `--service imessage` — Force iMessage (requires recipient has iMessage)
- `--service sms` — Force SMS (green bubble)
- `--service auto` — Let Messages.app decide (default)

### Example Workflow

User: "Text mom that I'll be late"

```bash
# 1. Find mom's chat
imsg chats --limit 20 --json | jq '.[] | select(.displayName | contains("Mom"))'

# 2. Confirm with user: "Found Mom at +155****3456. Send 'I'll be late' via iMessage?"

# 3. Send after confirmation
imsg send --to "+155****3456" --text "I'll be late"
```

### Rules

1. **Always confirm recipient and message content** before sending
2. **Never send to unknown numbers** without explicit user approval
3. **Verify file paths** exist before attaching
4. **Don't spam** — rate-limit yourself
