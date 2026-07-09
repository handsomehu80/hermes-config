# Edge-TTS Voice Catalog (curated for storybook use)

Microsoft Edge's `edge-tts` (https://github.com/rany2/edge-tts) provides ~300 neural voices. This is the curated subset most useful for storybook / narration work.

## Quick selector

| Use case | Voice | Locale | Gender | Notes |
|----------|-------|--------|--------|-------|
| **Chinese, warm female storyteller** | `zh-CN-XiaoxiaoNeural` | zh-CN | Female | **Default for kids storybook.** Most natural prosody. |
| Chinese, child / energetic | `zh-CN-XiaoyiNeural` | zh-CN | Female | Higher pitch, more animated. |
| Chinese, calm narrator | `zh-CN-XiaoyouNeural` | zh-CN | Female (child) | Softer child-style. |
| Chinese, male narrator | `zh-CN-YunxiNeural` | zh-CN | Male | Friendly male, good for heroic / epic content. |
| Chinese, male documentary | `zh-CN-YunjianNeural` | zh-CN | Male | Authoritative, sports/news tone. |
| English (US) female | `en-US-JennyNeural` | en-US | Female | Default for English narration. |
| English (US) male | `en-US-GuyNeural` | en-US | Male | |
| Japanese female | `ja-JP-NanamiNeural` | ja-JP | Female | |
| Korean female | `ko-KR-SunHiNeural` | ko-KR | Female | |

To list all voices:

```python
import asyncio, edge_tts
async def m():
    v = await edge_tts.list_voices()
    for x in v:
        if x['Locale'].startswith('zh-'):
            print(x['ShortName'], x['Gender'], x['Locale'])
asyncio.run(m())
```

## Prosody controls

| Parameter | Effect | Recommended for kids content |
|-----------|--------|------------------------------|
| `rate` | Speech speed. Negative = slower. | `-5%` (slightly slower than default) |
| `pitch` | Voice pitch shift. | `+0Hz` (neutral) or `+2Hz` for cheerfulness |
| `volume` | Loudness in dB. | `+0%` default; `+10%` if mixing with loud bed |

Usage in Python:

```python
import edge_tts
communicate = edge_tts.Communicate(
    text, 'zh-CN-XiaoxiaoNeural',
    rate='-5%',
    pitch='+0Hz',
    volume='+0%'
)
await communicate.save('output.mp3')
```

## Common failure modes

### "ModuleNotFoundError: No module named 'edge_tts'"

edge-tts is a standalone PyPI package. Install with:
```bash
python -m pip install edge-tts
```

It is NOT bundled with the system Python. If a previous session used edge-tts and then the environment was reset (pip uninstall, venv recreated, package upgraded), it disappears silently — and any code that did `import edge_tts` will fail.

### Silent English fallback

If `edge-tts` is installed but the runtime cannot reach the Edge TTS service (network blocked, proxy misconfigured, service outage), some versions **fall back** to SAPI / eSpeak which produce audio in the system default language — typically English with garbled CJK. The mp3 file IS created, but the content is wrong.

This is exactly the failure that produced this skill: a parent reported "只有数字的英文" (only English for the numbers) — the TTS had silently fallen back and was only able to pronounce the Arabic numerals from "今天是 2026 年 3 月 6 日".

### Auth failures

Microsoft Edge's TTS service doesn't require an API key, but it does send a synthetic client identity (the `edge-tts` package provides this via `Communicate`). If the service starts rejecting requests (returns HTTP 403/401), you may need to upgrade `edge-tts` (`pip install -U edge-tts`) — Microsoft rotates the synthetic identity periodically.

## Voice selection pattern (decision tree)

```
Need Chinese?
├── Yes → Need warm/calm or energetic?
│   ├── Warm/calm → zh-CN-XiaoxiaoNeural (default)
│   ├── Energetic/kid-excited → zh-CN-XiaoyiNeural
│   └── Male narrator → zh-CN-YunxiNeural
└── No → Need English?
    ├── Yes → en-US-JennyNeural (female) / en-US-GuyNeural (male)
    └── No  → fall through to ja-JP-NanamiNeural or look up other locale
```

## SSML — when to escalate

Edge-tts supports a subset of SSML for finer control (breaks, emphasis, prosody contours within a single utterance). For most storybook use the simple `text + rate + pitch` interface is sufficient. Escalate to SSML only when:

- You need a specific pause between phrases (use `<break time="500ms"/>`)
- You want emphasis on a word (`<emphasis level="strong">火星</emphasis>`)
- You need to switch voice mid-sentence

Example:

```python
ssml = '''
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:mstts="http://www.w3.org/2001/mstts"
       xml:lang="zh-CN">
  <voice name="zh-CN-XiaoxiaoNeural">
    今天是 2026 年 3 月 6 日。<break time="600ms"/>
    2012 年，<emphasis level="strong">"好奇号"</emphasis> 火星车飞过长长的星河……
  </voice>
</speak>
'''
communicate = edge_tts.Communicate(ssml, voice=None)  # voice already in SSML
```

For most storybook cases, plain text with `rate='-5%'` is plenty.