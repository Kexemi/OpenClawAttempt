# Fallback Asset Folder

Not used automatically. asset_key must exist in config/asset_mapping.yaml.

To use generic assets, add an explicit mapping in config/asset_mapping.yaml, e.g.:
  generic_nostalgia: fallback/generic

Then add assets: generic/video.mp4 or generic/images/*.png
