# Submodule-aware profile backup

Use this recipe when a profile backup repository contains one or more Git **gitlinks** (`mode 160000`). A gitlink records only a submodule commit pointer in the parent repository; files copied underneath that path are **not** ordinary parent-repository blobs.

## 1. Detect gitlinks before syncing

```bash
git -C "$REPO" ls-tree -r HEAD --full-tree |
while read -r mode type sha path; do
  [ "$mode" = "160000" ] && printf '%s\t%s\n' "$path" "$sha"
done
```

Also verify the index form:

```bash
git -C "$REPO" ls-files --stage |
while read -r mode sha stage path; do
  [ "$mode" = "160000" ] && printf '%s\t%s\n' "$path" "$sha"
done
```

Record every path below the target profile. Normalize Windows separators to `/` before comparing paths.

## 2. Sync without changing the pointer

Run the normal profile sync. Do **not** replace an existing gitlink with a regular directory, and do not stage files copied underneath an uninitialized submodule checkout.

Stage only the target profile:

```bash
git -C "$REPO" add -- <profile>/
```

Then confirm no gitlink pointer changed:

```bash
git -C "$REPO" diff --cached --raw -- <gitlink-path>
```

No output means the existing pointer was retained. If a pointer changed unexpectedly, unstage it and investigate:

```bash
git -C "$REPO" restore --staged -- <gitlink-path>
```

If copied files remain under an uninitialized gitlink in the transient staging tree, ignore or remove them from staging; never count them as parent-repository backup files.

## 3. API-fallback handling

Before using the Contents API, query the recursive tree and collect entries whose `type` is `commit`:

```bash
gh api 'repos/<owner>/<repo>/git/trees/main?recursive=1' \
  --jq '.tree[] | select(.type == "commit") | [.path,.sha] | @tsv'
```

Filter every diff path that is equal to, or nested below, a gitlink path. The Contents API cannot write inside a submodule and otherwise returns HTTP 409 ("file exists where you're trying to create a directory").

## 4. Verification after push

Verify regular blobs and gitlinks separately:

```bash
gh api 'repos/<owner>/<repo>/git/trees/main?recursive=1' \
  --jq '[.tree[] | select(.path | startswith("<profile>/"))] |
        {blobs: ([.[] | select(.type == "blob")] | length),
         gitlinks: ([.[] | select(.type == "commit") | {path,sha}])}'
```

For each gitlink, compare the GitHub-side SHA with the pre-sync SHA. The parent backup succeeded only if:

1. intended regular-file changes are present;
2. forbidden sensitive paths are absent;
3. each retained gitlink still points to the expected commit; and
4. the report separates regular-file totals from gitlink pointers.

## Reporting language

Use an explicit statement such as:

> Backed up 550 regular files (4.85 MB). Retained 1 gitlink at `<path>` pointing to `<sha>`; files inside that submodule are not included in the parent repository's regular-file count.

Never say copied files under a gitlink were backed up by the superproject. To back up changed submodule contents, commit and push the submodule's own repository separately, then deliberately update the parent pointer in a reviewed change.
