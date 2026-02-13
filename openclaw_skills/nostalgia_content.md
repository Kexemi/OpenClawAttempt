# Nostalgia Content Generation Skill

When generating nostalgia content for social media:

1. Load the persona from `personas/{account}.yaml` (genz, genx, millennial)
2. Generate platform-optimized copy: caption, hashtags, hook (opening line)
3. For video/image posts, output video_prompt (visual scene description), voiceover_text (for narrator), music_style (for background music)
4. Output format: end with a JSON block in this exact structure:

```json
{
  "drafts": [
    {
      "account": "genz",
      "platform": "tiktok",
      "caption": "Your caption text here...",
      "hashtags": "#nostalgia #genz #2000s",
      "hook": "POV: You just remembered...",
      "asset_type": "video",
      "video_prompt": "Cozy 2000s bedroom, Webkinz plushies on a shelf, warm lighting, nostalgic Gen Z aesthetic",
      "voiceover_text": "POV: It's 2008 and you're begging your parents for a new Webkinz plushie...",
      "music_style": "upbeat 2000s pop, nostalgic, subtle background"
    }
  ]
}
```

Valid accounts: genz, genx, millennial
Valid platforms: tiktok, reels
Valid asset_types: video, image

For asset_type "video": include video_prompt, voiceover_text, music_style. For asset_type "image": include video_prompt only (used as image prompt).
