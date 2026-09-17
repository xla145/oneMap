#!/usr/bin/env bash
set -euo pipefail

version=""
channel="beta"
platform=""
upload_provider="jdcloud"
no_upload=0
dry_run_upload=0
print_only=0
create_tag=0
tag_name=""
push_tag=0
skip_installer=0
notes=""
notes_file=""
auto_notes=0
no_auto_notes=0
required_branch=""
allow_version_channel_mismatch=0

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../../.." && pwd)"
env_file="$repo_root/.env"

usage() {
  cat <<'EOF'
Usage:
  package-updater.sh --version 1.1.8-beta.1 --channel beta [--platform darwin-aarch64] [--create-tag]

Options:
  --version <version>                 Release version, e.g. 1.1.8-beta.1 or 1.1.8
  --channel <beta|prod>               Update channel, default beta
  --platform <platform>               windows-x86_64, darwin-aarch64, or darwin-x86_64
  --upload-provider <jdcloud|minio>   Upload provider, default jdcloud
  --no-upload                         Build only
  --dry-run-upload                    Preview upload paths/latest.json
  --print-only                        Print command without running build/upload/tag
  --create-tag                        Create annotated git tag after successful package command
  --tag-name <tag>                    Override default tag v<version>
  --push-tag                          Push tag to origin after creating/verifying it
  --skip-installer                    Skip building/uploading the installer artifact when supported
  --notes <markdown>                  Notes written to latest.json
  --notes-file <path>                 Read latest.json notes from a UTF-8 Markdown file
  --auto-notes                        Generate notes from latest git tag to HEAD
  --no-auto-notes                     Do not auto-generate notes when --notes is omitted
  --required-branch <branch>          Optional stricter branch within the channel allowlist
  --allow-version-channel-mismatch    Disable beta/prod version format guard
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version|-Version)
      version="${2:-}"
      shift 2
      ;;
    --channel|-Channel)
      channel="${2:-}"
      shift 2
      ;;
    --platform|-Platform)
      platform="${2:-}"
      shift 2
      ;;
    --upload-provider|-UploadProvider)
      upload_provider="${2:-}"
      shift 2
      ;;
    --no-upload|-NoUpload)
      no_upload=1
      shift
      ;;
    --dry-run-upload|-DryRunUpload)
      dry_run_upload=1
      shift
      ;;
    --print-only|-PrintOnly)
      print_only=1
      shift
      ;;
    --create-tag|-CreateTag)
      create_tag=1
      shift
      ;;
    --tag-name|-TagName)
      tag_name="${2:-}"
      shift 2
      ;;
    --push-tag|-PushTag)
      push_tag=1
      shift
      ;;
    --skip-installer|-SkipInstaller)
      skip_installer=1
      shift
      ;;
    --notes|-Notes)
      notes="${2:-}"
      shift 2
      ;;
    --notes-file|-NotesFile)
      notes_file="${2:-}"
      shift 2
      ;;
    --auto-notes|-AutoNotes)
      auto_notes=1
      shift
      ;;
    --no-auto-notes|-NoAutoNotes)
      no_auto_notes=1
      shift
      ;;
    --required-branch|-RequiredBranch)
      required_branch="${2:-}"
      shift 2
      ;;
    --allow-version-channel-mismatch|-AllowVersionChannelMismatch)
      allow_version_channel_mismatch=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$version" ]]; then
  echo "Missing required --version." >&2
  usage >&2
  exit 2
fi

load_env_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    return 0
  fi

  set -a
  # shellcheck disable=SC1090
  source "$file"
  set +a
}

load_env_file "$env_file"
cd "$repo_root"

if [[ "$channel" != "beta" && "$channel" != "prod" ]]; then
  echo "Invalid --channel: $channel. Expected beta or prod." >&2
  exit 2
fi

if [[ -z "$platform" ]]; then
  case "$(uname -s)" in
    Darwin)
      if [[ "$(uname -m)" == "arm64" ]]; then
        platform="darwin-aarch64"
      else
        platform="darwin-x86_64"
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*)
      platform="windows-x86_64"
      ;;
    *)
      platform="$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
      ;;
  esac
fi

case "$platform" in
  windows-x86_64|darwin-aarch64|darwin-x86_64) ;;
  *)
    echo "Invalid --platform: $platform." >&2
    exit 2
    ;;
esac

if [[ "$upload_provider" != "jdcloud" && "$upload_provider" != "minio" ]]; then
  echo "Invalid --upload-provider: $upload_provider. Expected jdcloud or minio." >&2
  exit 2
fi

auto_release_notes() {
  local latest_tag=""
  local range_label="最近 20 条提交"
  local lines=""
  if latest_tag="$(git describe --tags --abbrev=0 2>/dev/null)" && [[ -n "$latest_tag" ]]; then
    range_label="$latest_tag..HEAD"
    lines="$(git log --no-merges --pretty=format:'- %s' "$latest_tag..HEAD")"
  else
    lines="$(git log --no-merges -20 --pretty=format:'- %s')"
  fi

  if [[ -z "$lines" ]]; then
    lines="- 本次版本包含稳定性改进。"
  fi

  printf '### 更新内容\n%s\n\n范围：%s' "$lines" "$range_label"
}

has_apple_notary_credentials() {
  if [[ -n "${APPLE_ID:-}" && -n "${APPLE_PASSWORD:-}" && -n "${APPLE_TEAM_ID:-}" ]]; then
    return 0
  fi
  if [[ -n "${APPLE_API_KEY:-}" && -n "${APPLE_API_ISSUER:-}" && -n "${APPLE_API_KEY_PATH:-}" ]]; then
    return 0
  fi
  return 1
}

macos_signing_identity() {
  local identity=""
  identity="${APPLE_SIGNING_IDENTITY:-${TAURI_SIGNING_IDENTITY:-}}"
  if [[ -n "$identity" ]]; then
    printf '%s\n' "$identity"
    return 0
  fi

  node -e "const fs=require('fs'); const p='src-tauri/tauri.macos.conf.json'; if (fs.existsSync(p)) console.log(JSON.parse(fs.readFileSync(p,'utf8'))?.bundle?.macOS?.signingIdentity || '')"
}

find_mac_dmg() {
  local dmg_dir="src-tauri/target/release/bundle/dmg"
  local versioned=""
  if [[ ! -d "$dmg_dir" ]]; then
    return 1
  fi

  versioned="$(find "$dmg_dir" -maxdepth 1 -type f -name "*.dmg" -print | grep "_${version}_" | sort | tail -n 1 || true)"
  if [[ -n "$versioned" ]]; then
    printf '%s\n' "$versioned"
    return 0
  fi

  find "$dmg_dir" -maxdepth 1 -type f -name "*.dmg" -print | sort | tail -n 1
}

sign_mac_dmg() {
  local dmg_path="$1"
  local identity=""
  identity="$(macos_signing_identity)"
  if [[ -z "$identity" ]]; then
    echo "Missing macOS signing identity. Set APPLE_SIGNING_IDENTITY/TAURI_SIGNING_IDENTITY or bundle.macOS.signingIdentity." >&2
    exit 1
  fi

  echo "[release-packaging] signing dmg: $dmg_path"
  codesign --force --timestamp --sign "$identity" "$dmg_path"
  codesign --verify --verbose=4 "$dmg_path"
}

notarize_mac_dmg() {
  if [[ "$platform" == "windows-x86_64" || "$skip_installer" -eq 1 ]]; then
    return 0
  fi

  if ! has_apple_notary_credentials; then
    echo "Missing Apple notarization credentials. Set APPLE_ID/APPLE_PASSWORD/APPLE_TEAM_ID or APPLE_API_KEY/APPLE_API_ISSUER/APPLE_API_KEY_PATH in .env." >&2
    exit 1
  fi

  local dmg_path=""
  dmg_path="$(find_mac_dmg)"
  if [[ -z "$dmg_path" || ! -f "$dmg_path" ]]; then
    echo "macOS DMG not found; cannot notarize installer before upload." >&2
    exit 1
  fi

  echo "[release-packaging] notarizing dmg: $dmg_path"
  sign_mac_dmg "$dmg_path"

  if [[ -n "${APPLE_ID:-}" && -n "${APPLE_PASSWORD:-}" && -n "${APPLE_TEAM_ID:-}" ]]; then
    xcrun notarytool submit "$dmg_path" \
      --apple-id "$APPLE_ID" \
      --password "$APPLE_PASSWORD" \
      --team-id "$APPLE_TEAM_ID" \
      --wait
  else
    xcrun notarytool submit "$dmg_path" \
      --key "$APPLE_API_KEY_PATH" \
      --key-id "$APPLE_API_KEY" \
      --issuer "$APPLE_API_ISSUER" \
      --wait
  fi

  xcrun stapler staple "$dmg_path"
  xcrun stapler validate "$dmg_path"
  spctl -a -vvv -t open --context context:primary-signature "$dmg_path"
}

current_branch="$(git branch --show-current)"
if [[ -z "$current_branch" ]]; then
  echo "Cannot determine current git branch. Refusing to package." >&2
  exit 1
fi

if [[ "$channel" == "prod" ]]; then
  allowed_branches=(release)
else
  allowed_branches=(test release)
fi

branch_allowed=0
for allowed_branch in "${allowed_branches[@]}"; do
  if [[ "$current_branch" == "$allowed_branch" ]]; then
    branch_allowed=1
    break
  fi
done

if [[ "$branch_allowed" -ne 1 ]]; then
  if [[ "$channel" == "prod" ]]; then
    echo "Prod packaging is only allowed on branch 'release'. Current branch is '$current_branch'." >&2
  else
    echo "Beta packaging is only allowed on branches 'test' or 'release'. Current branch is '$current_branch'." >&2
  fi
  exit 1
fi

if [[ -n "$required_branch" ]]; then
  required_branch_is_allowed=0
  for allowed_branch in "${allowed_branches[@]}"; do
    if [[ "$required_branch" == "$allowed_branch" ]]; then
      required_branch_is_allowed=1
      break
    fi
  done
  if [[ "$required_branch_is_allowed" -ne 1 ]]; then
    echo "--required-branch '$required_branch' is not allowed for channel '$channel'." >&2
    exit 2
  fi
  if [[ "$current_branch" != "$required_branch" ]]; then
    echo "Packaging was restricted to branch '$required_branch'. Current branch is '$current_branch'." >&2
    exit 1
  fi
fi

if [[ "$allow_version_channel_mismatch" -eq 0 ]]; then
  if [[ "$channel" == "beta" && ! "$version" =~ -beta\. ]]; then
    echo "Beta channel requires a prerelease version such as 1.1.8-beta.1." >&2
    exit 1
  fi
  if [[ "$channel" == "prod" && "$version" == *-* ]]; then
    echo "Prod channel should use a stable version such as 1.1.8." >&2
    exit 1
  fi
fi

if [[ -n "$notes" && -n "$notes_file" ]]; then
  echo "Pass only one of --notes or --notes-file." >&2
  exit 2
fi

resolved_notes=""
if [[ -n "$notes_file" ]]; then
  if [[ ! -f "$notes_file" ]]; then
    echo "Notes file not found: $notes_file" >&2
    exit 1
  fi
  resolved_notes="$(cat "$notes_file")"
elif [[ -n "$notes" ]]; then
  resolved_notes="$notes"
elif [[ "$auto_notes" -eq 1 || "$no_auto_notes" -eq 0 ]]; then
  resolved_notes="$(auto_release_notes)"
fi

prefix="bytecp-plus/$channel"
resolved_tag_name="${tag_name:-v$version}"
if [[ "$channel" == "prod" ]]; then
  build_mode_suffix=":pro"
else
  build_mode_suffix=":beta"
fi

if [[ "$platform" == "windows-x86_64" ]]; then
  npm_script="tauri:build:upload:updater:win${build_mode_suffix}"
else
  npm_script="tauri:build:upload:updater:mac${build_mode_suffix}"
fi

build_args=(
  run
  "$npm_script"
  --
  "--release-version=$version"
  --platform
  "$platform"
  "--upload-provider=$upload_provider"
)

if [[ "$platform" != "windows-x86_64" && "$skip_installer" -eq 1 ]]; then
  build_args+=(--bundles=app)
fi

if [[ "$platform" != "windows-x86_64" || "$no_upload" -eq 1 ]]; then
  build_args+=(--no-upload)
fi

if [[ "$platform" == "windows-x86_64" && "$dry_run_upload" -eq 1 ]]; then
  build_args+=(--dry-run-upload)
fi

if [[ "$platform" == "windows-x86_64" ]]; then
  build_args+=(--upload-args "--prefix=$prefix" "--platform=$platform")
  if [[ -n "$resolved_notes" ]]; then
    build_args+=("--notes=$resolved_notes")
  fi
fi

upload_args=()
if [[ "$platform" != "windows-x86_64" && "$no_upload" -eq 0 ]]; then
  if [[ "$upload_provider" == "jdcloud" ]]; then
    upload_script="tauri:upload:updater:jdcloud"
  else
    upload_script="tauri:upload:updater"
  fi

  upload_args=(
    run
    "$upload_script"
    --
    "--version=$version"
    "--platform=$platform"
    "--prefix=$prefix"
  )
  if [[ "$dry_run_upload" -eq 1 ]]; then
    upload_args+=(--dry-run)
  fi
  if [[ "$skip_installer" -eq 1 ]]; then
    upload_args+=(--skip-installer)
  fi
  if [[ -n "$resolved_notes" ]]; then
    upload_args+=("--notes=$resolved_notes")
  fi
fi

echo "[release-packaging] channel=$channel version=$version platform=$platform prefix=$prefix"
echo "[release-packaging] branch=$current_branch"
if [[ "$platform" != "windows-x86_64" ]]; then
  echo "[release-packaging] env=$env_file"
  echo "[release-packaging] mac flow=build no-upload -> notarize/staple dmg -> upload"
fi
if [[ -n "$resolved_notes" ]]; then
  echo "[release-packaging] notes:"
  printf '%s\n' "$resolved_notes"
fi
printf '[release-packaging] npm'
printf ' %q' "${build_args[@]}"
printf '\n'
if [[ "${#upload_args[@]}" -gt 0 ]]; then
  printf '[release-packaging] npm'
  printf ' %q' "${upload_args[@]}"
  printf '\n'
fi
if [[ "$create_tag" -eq 1 ]]; then
  echo "[release-packaging] tag=$resolved_tag_name pushTag=$push_tag"
fi

if [[ "$print_only" -eq 1 ]]; then
  exit 0
fi

npm "${build_args[@]}"
if [[ "$platform" != "windows-x86_64" ]]; then
  notarize_mac_dmg
fi
if [[ "${#upload_args[@]}" -gt 0 ]]; then
  npm "${upload_args[@]}"
fi

if [[ "$create_tag" -eq 1 ]]; then
  if git rev-parse -q --verify "refs/tags/$resolved_tag_name" >/dev/null; then
    existing_tag_commit="$(git rev-list -n 1 "$resolved_tag_name")"
    head_commit="$(git rev-parse HEAD)"
    if [[ "$existing_tag_commit" == "$head_commit" ]]; then
      echo "[release-packaging] tag already exists on HEAD: $resolved_tag_name"
    else
      echo "Tag $resolved_tag_name already exists on another commit. Refusing to move it." >&2
      exit 1
    fi
  else
    git tag -a "$resolved_tag_name" -m "Release $version ($channel)"
    echo "[release-packaging] created tag $resolved_tag_name"
  fi

  if [[ "$push_tag" -eq 1 ]]; then
    git push origin "$resolved_tag_name"
  fi
fi
