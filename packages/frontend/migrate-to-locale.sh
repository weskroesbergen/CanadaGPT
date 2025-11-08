#!/bin/bash

# Script to migrate Next.js app directory to [locale] structure
# This will move all routes except /api into /[locale]

set -e

APP_DIR="/Users/matthewdufresne/FedMCP/packages/frontend/src/app"
LOCALE_DIR="$APP_DIR/[locale]"

echo "Creating [locale] directory..."
mkdir -p "$LOCALE_DIR"

echo "Moving routes into [locale] directory..."

# Move all directories except api and [locale] itself
for dir in "$APP_DIR"/*; do
  if [ -d "$dir" ]; then
    dirname=$(basename "$dir")
    # Skip api, [locale], and hidden directories
    if [ "$dirname" != "api" ] && [ "$dirname" != "[locale]" ] && [[ "$dirname" != .* ]]; then
      echo "  Moving $dirname..."
      mv "$dir" "$LOCALE_DIR/"
    fi
  fi
done

# Move page.tsx to [locale]
if [ -f "$APP_DIR/page.tsx" ]; then
  echo "Moving page.tsx..."
  mv "$APP_DIR/page.tsx" "$LOCALE_DIR/"
fi

# Move layout.tsx to [locale] (this will be the locale-specific layout)
if [ -f "$APP_DIR/layout.tsx" ]; then
  echo "Moving layout.tsx to [locale]/layout.tsx..."
  mv "$APP_DIR/layout.tsx" "$LOCALE_DIR/layout.tsx"
fi

# Move any other root files that should be in [locale]
for file in "$APP_DIR"/*.tsx "$APP_DIR"/*.ts; do
  if [ -f "$file" ]; then
    filename=$(basename "$file")
    # Skip certain files that should stay at root
    if [ "$filename" != "layout.tsx" ] && [ "$filename" != "global.css" ]; then
      echo "  Moving $filename..."
      mv "$file" "$LOCALE_DIR/"
    fi
  fi
done

echo "Migration complete!"
echo "Note: You'll need to create a new root layout.tsx manually"
