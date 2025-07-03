#!/bin/bash
# Run mypy on changed Python package directories (monorepo structure)

set -e

changed_paths=$(git diff --cached --name-only)
status=0

# python 폴더 내 src 하위의 실제 패키지 경로 추출
pkg_dirs=$(echo "$changed_paths" \
  | grep '^python/' \
  | grep '/src/' \
  | sed -E 's|^(.*/src/[^/]+).*|\1|' \
  | sort -u)

if [ -z "$pkg_dirs" ]; then
  echo "No changed Python packages to check."
  exit 0
fi

for full_path in $pkg_dirs; do
  # 예: python/apps/iot-subscriber/src/iot_subscriber
  root_dir=$(echo "$full_path" | sed -E 's|(/src/[^/]+)$||')  # 예: python/apps/iot-subscriber
  pkg_path=$(echo "$full_path" | sed -E 's|.*/src/|src/|')     # 예: src/iot_subscriber

  echo "root_dir: $root_dir"
  echo "pkg_path: $pkg_path"

  if [ -f "$root_dir/pyproject.toml" ]; then
    echo "Running mypy in $root_dir/$pkg_path ..."
    (cd "$root_dir" && uv run mypy "$pkg_path") || status=1
  else
    echo "Skipping $root_dir (missing pyproject.toml)"
  fi
  echo "--------------------------------"
done

exit $status
