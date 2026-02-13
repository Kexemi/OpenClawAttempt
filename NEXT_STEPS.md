# Next Steps (Your Part)

Run `python scripts/verify_setup.py` — it reports what’s missing.

## Required

1. **`.env`** — Replace `your_buffer_access_token_here` with your real Buffer access token.
2. **`config/accounts.yaml`** — Replace each `YOUR_*_PROFILE_ID` with your Buffer profile IDs (from Buffer after connecting TikTok/IG).
3. **Assets** — For each key in `config/asset_mapping.yaml`, add `assets/{theme}/{key}/video.mp4` or `images/*.png`. See `ASSETS.md`.

## Optional for first run

- Use `--no-video` on `generate_batch.py` to create text-only drafts before adding assets.

## Publishing

- Drafts with video/image will not post until upload-to-public-URL is implemented.
- Text-only drafts can post if Buffer credentials are set.
