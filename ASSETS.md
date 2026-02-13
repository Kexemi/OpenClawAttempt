# Adding Assets

Each `asset_key` in `config/asset_mapping.yaml` must have actual files. Add them here:

## Structure

```
assets/{theme}/{asset_key}/
  video.mp4          # single video
  OR
  images/
    *.png or *.jpg   # for slideshow
```

## Example: blockbuster_store

Mapping: `blockbuster_store: 90s_retail/blockbuster_store`

Create:
- `assets/90s_retail/blockbuster_store/video.mp4` — one video
- OR `assets/90s_retail/blockbuster_store/images/` — folder of PNG/JPG

## Where to get clips

- **Pexels** (pexels.com) — free stock video, download MP4
- **Archive.org** — public domain / vintage footage
- **Pixabay** — free video

Download, place in the path from `asset_mapping.yaml`, name `video.mp4` or put images in `images/`.

## Current mappings

See `config/asset_mapping.yaml`. For each key, create the folder and add media.
