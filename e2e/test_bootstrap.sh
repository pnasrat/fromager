#!/bin/bash
# -*- indent-tabs-mode: nil; tab-width: 2; sh-indentation: 2; -*-

# Tests full bootstrap and installation of a complex package, without
# worrying about isolating the tools from upstream sources or
# restricting network access during the build. This allows us to test
# the overall logic of the build tools separately from the isolated
# build pipelines.

SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPTDIR/common.sh"

fromager \
  --log-file="$OUTDIR/bootstrap.log" \
  --error-log-file="$OUTDIR/fromager-errors.log" \
  --sdists-repo="$OUTDIR/sdists-repo" \
  --wheels-repo="$OUTDIR/wheels-repo" \
  --work-dir="$OUTDIR/work-dir" \
  bootstrap 'stevedore==5.2.0'

find "$OUTDIR/wheels-repo/" -name '*.whl'
find "$OUTDIR/sdists-repo/" -name '*.tar.gz'
ls "$OUTDIR"/work-dir/*/build.log || true

EXPECTED_FILES="
$OUTDIR/wheels-repo/downloads/setuptools-*.whl
$OUTDIR/wheels-repo/downloads/pbr-*.whl
$OUTDIR/wheels-repo/downloads/stevedore-*.whl

$OUTDIR/sdists-repo/downloads/stevedore-*.tar.gz
$OUTDIR/sdists-repo/downloads/setuptools-*.tar.gz
$OUTDIR/sdists-repo/downloads/pbr-*.tar.gz

$OUTDIR/sdists-repo/builds/stevedore-*.tar.gz
$OUTDIR/sdists-repo/builds/setuptools-*.tar.gz
$OUTDIR/sdists-repo/builds/pbr-*.tar.gz

$OUTDIR/work-dir/build-order.json
$OUTDIR/work-dir/constraints.txt

$OUTDIR/bootstrap.log
$OUTDIR/fromager-errors.log

$OUTDIR/work-dir/pbr-*/build.log
$OUTDIR/work-dir/setuptools-*/build.log
$OUTDIR/work-dir/stevedore-*/build.log
"

pass=true
for pattern in $EXPECTED_FILES; do
  if [ ! -f "${pattern}" ]; then
    echo "Did not find $pattern" 1>&2
    pass=false
  fi
done

build_order="$OUTDIR/work-dir/build-order.json"
bootstrap_constraints="$OUTDIR/work-dir/constraints.txt"
build_order_constraints="$OUTDIR/build-order-constraints.txt"
constraints_without_comments="$OUTDIR/constraints-without-comments.txt"

# Verify that the constraints file matches the build order file.
jq -r '.[] | .dist + "==" + .version' "$build_order" > "$build_order_constraints"
cat "$bootstrap_constraints" | sed 's/  #.*//g' > "$constraints_without_comments"
sort -o "$constraints_without_comments" "$constraints_without_comments"
sort -o "$build_order_constraints" "$build_order_constraints"
if ! diff "$constraints_without_comments" "$build_order_constraints";
then
  echo "FAIL: constraints do not match build order"
  pass=false
fi

# Verify that regenerating the constraints file from the build-order file gives
# the same results.
generated_constraints="$OUTDIR/generated-constraints.txt"
fromager build-order to-constraints "$build_order" "$generated_constraints"
if ! diff "$bootstrap_constraints" "$generated_constraints"; then
  echo "FAIL: generated constraints do not match original"
  pass=false
fi

$pass
