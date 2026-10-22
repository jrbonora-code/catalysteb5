// Census ACS proxy for the TEA Map.
//
// The Census Data API now requires a key on every request. Keys are free:
// https://api.census.gov/data/key_signup.html
// Add it in Netlify under Site configuration > Environment variables as CENSUS_API_KEY.
//
// Without a key this function returns 501 and the TEA Map falls back to the
// public Esri Living Atlas ACS layers automatically. With a key, the map uses
// the newest ACS 5-year release straight from the Census Bureau.
//
// GET /api/acs?tracts=12071080300,12071080400
// -> { source, vintage, national: {lf, un}, tracts: { GEOID: {lf, un, name} } }

const VINTAGES = [2025, 2024, 2023]; // newest first; the first that answers is used
const VARS = "NAME,B23025_003E,B23025_005E";

const json = (body, status = 200, cache = true) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
      "cache-control": cache && status === 200 ? "public, max-age=86400" : "no-store",
    },
  });

async function census(year, params, key) {
  const url = `https://api.census.gov/data/${year}/acs/acs5?get=${VARS}&${params}&key=${encodeURIComponent(key)}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`census ${year} ${r.status}`);
  const rows = await r.json();
  const [head, ...data] = rows;
  const ix = (k) => head.indexOf(k);
  return data.map((row) => ({
    name: row[ix("NAME")],
    lf: Number(row[ix("B23025_003E")]) || 0,
    un: Number(row[ix("B23025_005E")]) || 0,
    state: row[ix("state")],
    county: row[ix("county")],
    tract: row[ix("tract")],
  }));
}

export default async (req) => {
  const key = (globalThis.Netlify && Netlify.env.get("CENSUS_API_KEY")) || process.env.CENSUS_API_KEY;
  if (!key) return json({ error: "CENSUS_API_KEY is not set" }, 501, false);

  const url = new URL(req.url);
  const geoids = [...new Set((url.searchParams.get("tracts") || "").split(","))]
    .filter((g) => /^\d{11}$/.test(g))
    .slice(0, 80);
  if (!geoids.length) return json({ error: "Pass ?tracts= with 11-digit tract GEOIDs" }, 400, false);

  // Group tracts by state and county, one Census call per county.
  const groups = {};
  for (const g of geoids) (groups[g.slice(0, 5)] ||= []).push(g.slice(5));

  for (const year of VINTAGES) {
    try {
      const [nat] = await census(year, "for=us:1", key);
      const tracts = {};
      for (const [sc, list] of Object.entries(groups)) {
        const rows = await census(year, `for=tract:${list.join(",")}&in=state:${sc.slice(0, 2)}%20county:${sc.slice(2)}`, key);
        for (const t of rows) tracts[t.state + t.county + t.tract] = { lf: t.lf, un: t.un, name: t.name };
      }
      return json({
        source: "U.S. Census Bureau Data API",
        vintage: `ACS ${year - 4}-${year} 5-year estimates`,
        national: { lf: nat.lf, un: nat.un },
        tracts,
      });
    } catch (e) {
      // try the next vintage
    }
  }
  return json({ error: "Census API did not respond" }, 502, false);
};

export const config = { path: "/api/acs" };
