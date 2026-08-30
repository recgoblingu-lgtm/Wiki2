# Wiki2 automated encyclopedia

Wiki2 is an old-school, static HTML encyclopedia that grows automatically in the GitHub repository. A GitHub-hosted workflow runs twice per hour, selects an unused realistic topic, retrieves public encyclopedic source material from Wikimedia, renders a complete article under `articles/`, updates the article index, commits the result, and pushes it back to `main`.

## Automatic operation

The workflow is defined in [`.github/workflows/wiki-generator.yml`](.github/workflows/wiki-generator.yml). It runs at minute 17 and 47 of every hour, and it can also be started from the repository’s **Actions** tab with **Run workflow**. The recurring schedule means the process continues across separate short-lived GitHub-hosted jobs instead of depending on a computer, terminal, or browser remaining open. After the starter topics are used, the generator asks Wikimedia for random main-namespace encyclopedia pages and continues selecting unused subjects dynamically.

Each run creates at most one article. This keeps commits small, prevents API bursts, and makes each addition independently visible in the repository history. GitHub may delay scheduled workflows by a few minutes during busy periods; that is normal for scheduled automation.

## Duplicate protection

The file [`.wiki-generated.json`](.wiki-generated.json) is the durable topic ledger. The generator checks both the ledger and the actual `articles/` directory before writing. It refuses to overwrite an existing filename and records the source URL, category, title, and generation time after a successful article creation.

## Article design

Every generated page is a complete HTML document with a serif font, sidebar navigation, title, overview, two to four subject sections, related links, a source reference, and a “Last edited” date. The pages use the existing `style.css` and contain no framework or client-side application dependency.

## Manual controls

No recurring manual operation is required. To pause the system, disable the **Grow Wiki2** workflow in GitHub. To resume it, re-enable the workflow. To request an immediate article, use **Run workflow**. To change the pace, edit the `cron` expression in the workflow file. The workflow is designed to keep discovering new subjects; it can only stop adding articles if Wikimedia is unavailable, GitHub Actions is disabled or unavailable, or the source corpus is exhausted.

For local testing only, install the dependencies and run:

```bash
python -m pip install requests beautifulsoup4
python generator.py --once
python generator.py --forever --interval 1800
```

The local `--forever` mode is optional and is not needed for the hosted automation.

## Data and attribution

The generator uses Wikimedia’s public APIs and keeps a source link in every generated article. It does not require an AI key, private server, paid hosting, or a continuously running personal computer. Source text is cleaned and presented as a compact reference article; the source link should be retained when articles are reused.

## Repository permissions

The workflow requests only `contents: write`, which is required to commit and push generated files. The repository must allow GitHub Actions to write to repository contents under **Settings → Actions → General → Workflow permissions**. The workflow does not need any additional secret.
