---
name: interactive-games
description: "Self-hosted interactive gaming on Windows/Linux/macOS — host a modded Minecraft server (CurseForge/Modrinth modpacks) AND play Pokemon via headless emulator + RAM reads. Two distinct workflows under one class-level umbrella."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [gaming, minecraft, pokemon, server, emulator, modpack]
    absorbed_from: [minecraft-modpack-server, pokemon-player]
---

# Interactive Games

Class-level umbrella for self-hosted interactive gaming. Two previously separate skills — pick the section that matches your task:

| The user wants to… | Section to load |
|---|---|
| Host a modded Minecraft server (CurseForge/Modrinth modpack) | [Host a Minecraft Server](#host-a-minecraft-server) |
| Have an AI play Pokemon (Red/Blue/Yellow/FireRed) via headless emulator | [AI Plays Pokemon](#ai-plays-pokemon) |

Each section is self-contained. Both skills are platform-checked: the Minecraft side requires Linux/macOS; the Pokemon side works on Windows/Linux/macOS. If only one section applies to the current task, read just that section.

---

## Host a Minecraft Server

### When to use

- User wants to set up a modded Minecraft server from a server pack zip
- User needs help with NeoForge/Forge server configuration
- User asks about Minecraft server performance tuning or backups

### Gather User Preferences First

Before starting setup, ask the user for:

- **Server name / MOTD** — what should it say in the server list?
- **Seed** — specific seed or random?
- **Difficulty** — peaceful / easy / normal / hard?
- **Gamemode** — survival / creative / adventure?
- **Online mode** — true (Mojang auth, legit accounts) or false (LAN/cracked friendly)?
- **Player count** — how many players expected? (affects RAM & view distance tuning)
- **RAM allocation** — or let agent decide based on mod count & available RAM?
- **View distance / simulation distance** — or let agent pick based on player count & hardware?
- **PvP** — on or off?
- **Whitelist** — open server or whitelist only?
- **Backups** — want automated backups? How often?

Use sensible defaults if the user doesn't care, but always ask before generating the config.

### Steps

#### 1. Download & Inspect the Pack

```bash
mkdir -p ~/minecraft-server
cd ~/minecraft-server
wget -O serverpack.zip "<URL>"
unzip -o serverpack.zip -d server
ls server/
```

Look for: `startserver.sh`, installer jar (neoforge/forge), `user_jvm_args.txt`, `mods/` folder. Check the script to determine: mod loader type, version, and required Java version.

#### 2. Install Java

- Minecraft 1.21+ → Java 21: `sudo apt install openjdk-21-jre-headless`
- Minecraft 1.18-1.20 → Java 17: `sudo apt install openjdk-17-jre-headless`
- Minecraft 1.16 and below → Java 8: `sudo apt install openjdk-8-jre-headless`
- Verify: `java -version`

#### 3. Install the Mod Loader

Most server packs include an install script. Use the INSTALL_ONLY env var to install without launching:

```bash
cd ~/minecraft-server/server
ATM10_INSTALL_ONLY=true bash startserver.sh
# Or for generic Forge packs:
# java -jar forge-*-installer.jar --installServer
```

This downloads libraries, patches the server jar, etc.

#### 4. Accept EULA

```bash
echo "eula=true" > ~/minecraft-server/server/eula.txt
```

#### 5. Configure server.properties

Key settings for modded/LAN:

```properties
motd=\u00a7b\u00a7lServer Name \u00a7r\u00a78| \u00a7aModpack Name
server-port=25565
online-mode=true          # false for LAN without Mojang auth
enforce-secure-profile=true  # match online-mode
difficulty=hard            # most modpacks balance around hard
allow-flight=true          # REQUIRED for modded (flying mounts/items)
spawn-protection=0         # let everyone build at spawn
max-tick-time=180000       # modded needs longer tick timeout
enable-command-block=true
```

Performance settings (scale to hardware):

```properties
# 2 players, beefy machine:
view-distance=16
simulation-distance=10

# 4-6 players, moderate machine:
view-distance=10
simulation-distance=6

# 8+ players or weaker hardware:
view-distance=8
simulation-distance=4
```

#### 6. Tune JVM Args (user_jvm_args.txt)

Scale RAM to player count and mod count. Rule of thumb for modded:

- 100-200 mods: 6-12GB
- 200-350+ mods: 12-24GB
- Leave at least 8GB free for the OS/other tasks

```
# user_jvm_args.txt
-Xms6G
-Xmx12G

# Aikar's Flags (recommended for 1.17+):
-XX:+UseG1GC
-XX:+ParallelRefProcEnabled
-XX:MaxGCPauseMillis=200
-XX:+UnlockExperimentalVMOptions
-XX:+DisableExplicitGC
-XX:G1NewSizePercent=30
-XX:G1MaxNewSizePercent=40
-XX:G1HeapRegionSize=8M
-XX:G1ReservePercent=20
-XX:G1HeapWastePercent=5
-XX:G1MixedGCCountTarget=4
-XX:InitiatingHeapOccupancyPercent=15
-XX:G1MixedGCLiveThresholdPercent=90
-XX:G1RSetUpdatingPauseTimePercent=5
-XX:SurvivorRatio=32
-XX:+PerfDisableSharedMem
-XX:MaxTenuringThreshold=1
```

#### 7. Start the Server (foreground to test)

```bash
cd ~/minecraft-server/server
bash startserver.sh
```

Watch for "Done (X.XXs)! For help, type 'help'" — that means it's ready.

#### 8. Move to Background / systemd

Once stable, install as a systemd service so it survives reboots:

```bash
sudo tee /etc/systemd/system/minecraft.service > /dev/null <<'EOF'
[Unit]
Description=Minecraft Server
After=network.target

[Service]
User=minecraft
WorkingDirectory=/home/minecraft/minecraft-server/server
ExecStart=/bin/bash startserver.sh
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now minecraft
sudo systemctl status minecraft
```

View logs: `journalctl -u minecraft -f` or `tail -f ~/minecraft-server/server/logs/latest.log`

#### 9. Backups (cron)

```bash
# Backup script: ~/minecraft-server/backup.sh
#!/bin/bash
tar -czf /backups/minecraft-$(date +%Y%m%d-%H%M%S).tar.gz \
    ~/minecraft-server/server/world \
    ~/minecraft-server/server/server.properties

# Keep last 14 days
find /backups -name "minecraft-*.tar.gz" -mtime +14 -delete
```

```bash
chmod +x ~/minecraft-server/backup.sh
# Run daily at 4am:
(crontab -l 2>/dev/null; echo "0 4 * * * /home/<user>/minecraft-server/backup.sh") | crontab -
```

### Common Pitfalls

1. **Wrong Java version** — 1.17+ requires Java 17, 1.21+ requires Java 21. Old packs may need Java 8.
2. **Online mode + whitelist mismatch** — pick one auth model. Mixing `online-mode=false` with `enforce-secure-profile=true` breaks clients.
3. **Under-allocated RAM** — most crashes trace to GC pressure. Bump `-Xmx` until CPU usage at idle is < 10%.
4. **Default view-distance too high** — 16 chunks works on a single player; 10 is more realistic for 4+ players with mods.
5. **Forgetting EULA** — without `eula=true` the server refuses to start.
6. **Modded lag** — 200+ mods need 12+ GB RAM. Profile with a Spark report (`/spark profiler start`) if you can't find the culprit.

---

## AI Plays Pokemon

Play Pokemon games via headless emulation using the `pokemon-agent` package.

### When to Use

- User says "play pokemon", "start pokemon", "pokemon game"
- User asks about Pokemon Red, Blue, Yellow, FireRed, etc.
- User wants to watch an AI play Pokemon
- User references a ROM file (.gb, .gbc, .gba)

### Startup Procedure

#### 1. First-time setup (clone, venv, install)

The repo is NousResearch/pokemon-agent on GitHub. Clone it, then set up a Python 3.10+ virtual environment. Use uv (preferred for speed) to create the venv and install the package in editable mode with the pyboy extra. If uv is not available, fall back to python3 -m venv + pip.

On this machine it is already set up at /home/teknium/pokemon-agent with a venv ready — just cd there and source .venv/bin/activate.

You also need a ROM file. Ask the user for theirs. On this machine one exists at roms/pokemon_red.gb inside that directory. **NEVER download or provide ROM files — always ask the user.**

#### 2. Start the game server

From inside the pokemon-agent directory with the venv activated, run `pokemon-agent serve` with `--rom` pointing to the ROM and `--port 9876`. Run it in the background with `&`. To resume from a saved game, add `--load-state` with the save name. Wait 4 seconds for startup, then verify with `GET /health`.

#### 3. Set up live dashboard for user to watch

Use an SSH reverse tunnel via localhost.run so the user can view the dashboard in their browser. Connect with ssh, forwarding local port 9876 to remote port 80 on `nokey@localhost.run`. Redirect output to a log file, wait 10 seconds, then grep the log for the `.lhr.life` URL. Give the user the URL with `/dashboard/` appended. The tunnel URL changes each time — give the user the new one if restarted.

### Save and Load

#### When to save

- Every 15-20 turns of gameplay
- **ALWAYS** before gym battles, rival encounters, or risky fights
- Before entering a new town or dungeon
- Before any action you are unsure about

#### How to save

`POST /save` with a descriptive name. Good examples: `before_brock`, `route1_start`, `mt_moon_entrance`, `got_cut`.

#### How to load

`POST /load` with the save name.

#### List available saves

`GET /saves` returns all saved states.

#### Loading on server startup

Use `--load-state` flag when starting the server to auto-load a save. This is faster than loading via the API after startup.

### The Gameplay Loop

1. **OBSERVE** — check state AND take a screenshot. `GET /state` for position, HP, battle, dialog. `GET /screenshot` and save to `/tmp/pokemon.png`, then use `vision_analyze`. **Always do BOTH** — RAM state gives numbers, vision gives spatial awareness.

2. **ORIENT** — Dialog/text on screen → advance it. In battle → fight or run. Party hurt → head to Pokemon Center. Near objective → navigate carefully.

3. **DECIDE** — Priority: dialog > battle > heal > story objective > training > explore.

4. **ACT** — move 2-4 steps max, then re-check. `POST /action` with a SHORT action list (2-4 actions, not 10-15).

5. **VERIFY** — screenshot after every move sequence. Take a screenshot and use `vision_analyze` to confirm you moved where intended. **This is the MOST IMPORTANT step. Without vision you WILL get lost.**

6. **RECORD** progress to memory with `PKM:` prefix.

7. **SAVE** periodically.

### Action Reference

- `press_a` — confirm, talk, select
- `press_b` — cancel, close menu
- `press_start` — open game menu
- `walk_up/down/left/right` — move one tile
- `hold_b_N` — hold B for N frames (use for speeding through text)
- `wait_60` — wait about 1 second (60 frames)
- `a_until_dialog_end` — press A repeatedly until dialog clears

### Critical Tips from Experience

**USE VISION CONSTANTLY** — Take a screenshot every 2-4 movement steps. The RAM state tells you position and HP but NOT what is around you. Ledges, fences, signs, building doors, NPCs — only visible via screenshot. Ask the vision model specific questions: "what is one tile north of me?" When stuck, always screenshot before trying random directions.

**Warp Transitions Need Extra Wait Time** — When walking through a door or stairs, the screen fades to black during the map transition. You MUST wait for it to complete. Add 2-3 `wait_60` actions after any door/stair warp. Without waiting, the position reads as stale and you will think you are still in the old map.

**Building Exit Trap** — When you exit a building, you appear directly IN FRONT of the door. If you walk north, you go right back inside. ALWAYS sidestep first by walking left or right 2 tiles, then proceed in your intended direction.

**Dialog Handling** — Gen 1 text scrolls slowly letter-by-letter. To speed through dialog, hold B for 120 frames then press A. Repeat as needed. Holding B makes text display at max speed. Then press A to advance to the next line. The `a_until_dialog_end` action checks the RAM dialog flag, but this flag does not catch ALL text states. If dialog seems stuck, use the manual `hold_b` + `press_a` pattern instead and verify via screenshot.

**Ledges Are One-Way** — Ledges (small cliff edges) can only be jumped DOWN (south), never climbed UP (north). If blocked by a ledge going north, you must go left or right to find the gap around it. Use vision to identify which direction the gap is. Ask the vision model explicitly.

**Navigation Strategy** — Move 2-4 steps at a time, then screenshot to check position. When entering a new area, screenshot immediately to orient. Ask the vision model "which direction to [destination]?" If stuck for 3+ attempts, screenshot and re-evaluate completely. Do not spam 10-15 movements — you will overshoot or get stuck.

**Running from Wild Battles** — On the battle menu, RUN is bottom-right. To reach it from the default cursor position (FIGHT, top-left): press down then right to move cursor to RUN, then press A. Wrap with `hold_b` to speed through text/animations.

**Battling (FIGHT)** — On the battle menu FIGHT is top-left (default cursor position). Press A to enter move selection, A again to use the first move. Then hold B to speed through attack animations and text.

### Battle Strategy

Decision tree:

1. Want to catch? → Weaken then throw Poke Ball
2. Wild you don't need? → RUN
3. Type advantage? → Use super-effective move
4. No advantage? → Use strongest STAB move
5. Low HP? → Switch or use Potion

**Gen 1 Type Chart (key matchups)**:

- Water beats Fire, Ground, Rock
- Fire beats Grass, Bug, Ice
- Grass beats Water, Ground, Rock
- Electric beats Water, Flying
- Ground beats Fire, Electric, Rock, Poison
- Psychic beats Fighting, Poison (dominant in Gen 1!)

**Gen 1 Quirks**:

- Special stat = both offense AND defense for special moves
- Psychic type is overpowered (Ghost moves bugged)
- Critical hits based on Speed stat
- Wrap/Bind prevent opponent from acting
- Focus Energy bug: REDUCES crit rate instead of raising it

### Memory Conventions

| Prefix | Purpose | Example |
|--------|---------|---------|
| `PKM:OBJECTIVE` | Current goal | Get Parcel from Viridian Mart |
| `PKM:MAP` | Navigation knowledge | Viridian: mart is northeast |
| `PKM:STRATEGY` | Battle/team plans | Need Grass type before Misty |
| `PKM:PROGRESS` | Milestone tracker | Beat rival, heading to Viridian |
| `PKM:STUCK` | Stuck situations | Ledge at y=28 go right to bypass |
| `PKM:TEAM` | Team notes | Squirtle Lv6, Tackle + Tail Whip |

### Progression Milestones

- Choose starter
- Deliver Parcel from Viridian Mart, receive Pokedex
- Boulder Badge — Brock (Rock) → use Water/Grass
- Cascade Badge — Misty (Water) → use Grass/Electric
- Thunder Badge — Lt. Surge (Electric) → use Ground
- Rainbow Badge — Erika (Grass) → use Fire/Ice/Flying
- Soul Badge — Koga (Poison) → use Ground/Psychic
- Marsh Badge — Sabrina (Psychic) → hardest gym
- Volcano Badge — Blaine (Fire) → use Water/Ground
- Earth Badge — Giovanni (Ground) → use Water/Grass/Ice
- Elite Four → Champion!

### Stopping Play

1. Save the game with a descriptive name via `POST /save`
2. Update memory with `PKM:PROGRESS`
3. Tell user: "Game saved as [name]! Say 'play pokemon' to resume."
4. Kill the server and tunnel background processes

### Pitfalls

- **NEVER** download or provide ROM files
- Do NOT send more than 4-5 actions without checking vision
- Always sidestep after exiting buildings before going north
- Always add `wait_60` x2-3 after door/stair warps
- Dialog detection via RAM is unreliable — verify with screenshots
- Save BEFORE risky encounters
- The tunnel URL changes each time you restart it
