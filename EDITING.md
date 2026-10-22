# How to edit the site

Netlify hosts files and runs builds; it has no content editor. All site text lives in six JSON files in `content/`. Edit them directly on GitHub (pencil icon, change the text, **Commit changes**) and Netlify rebuilds in about a minute. If a file is broken, the deploy fails and the live site keeps serving the last good version.

| File | What it controls |
|---|---|
| `content/site.json` | Name, domain, address, phone, email, nav, homepage stat tiles, risk cards, current mandate, footer disclaimer |
| `content/services.json` | Construction administration and loan servicing stages, draw cycle, compliance record, engagement models, value to you |
| `content/loans.json` | The 16 representative EB-5 loans |
| `content/team.json` | The three bios |
| `content/developer.json` | The Catalyst Community Development projects and stats |
| `content/info.json` | Info Center categories, articles, investor timeline and glossary |

### The three rules for changing text

1. **Keep the quotation marks.** Change what is inside them, never delete them.
2. **Keep the commas** at the end of each line.
3. **Apostrophes are fine, straight double quotes are not.** Inside text, write `\"` instead of `"`, or use curly quotes.

### Hiding something

Every loan, team member and article has `"visible": true`. Change it to `false` and it disappears from the site, including from totals and related-article lists. Nothing is lost.

### Adding a loan

Copy a block in `loans.json`, give it a new `slug`, and drop a matching photo into `source-photos/deck/<slug>.jpg`. Run `python3 tools-process-images.py` locally to produce the web versions, then commit. Without a photo the card shows a navy placeholder.

### Adding an Info Center article

Copy an article block in `info.json` and give it a new `slug` and one of the category slugs (`basics`, `structure`, `funding`, `requirements`, `timeline`, `construction`, `risk`, `updates`). The page appears at `/info-center/<slug>/` automatically.

The `body` is a list of blocks:

```json
{"h": "A subheading"},
{"p": "A paragraph."},
{"ul": ["A bullet", "Another bullet"]},
{"table": {"head": ["Form", "Fee"], "rows": [["I-526E", "$7,850"]]}},
{"callout": "A highlighted note."}
```

Optional fields: `"date"` (shown on the card, used for Program Updates), `"featured": true` (pinned to the homepage), `"image"` (one of the photo slugs, shown at the top of the article).

### House style

Catalyst copy does not use em dashes or en dashes as pauses. Use a comma, semicolon, colon or parentheses instead.

### Not in the content files

- **Photography:** `tools-process-images.py` and `static/img/`.
- **Logo:** `static/img/brand/`, the same files as catalystcd.com.
- **Colors, type, layout:** `static/styles.css` and `build.py`.
- **TEA Map behavior:** `static/tea-map.js`; the Census key is a Netlify environment variable (`CENSUS_API_KEY`).
- **Redirects:** `static/_redirects`.
- **Form notifications:** Netlify dashboard, **Forms**.
