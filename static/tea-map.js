/* Catalyst EB-5 TEA Map.
   Indicative targeted employment area check, entirely in the browser.

   Data:
   - Boundaries, metro areas and city populations: U.S. Census Bureau TIGERweb (public, no key)
   - Unemployment: ACS 5-year estimates (B23025), from the site's /api/acs function when a
     CENSUS_API_KEY is set in Netlify, otherwise from Esri Living Atlas ACS layers (public, no key)
   - Address search: U.S. Census Geocoder, falling back to OpenStreetMap Nominatim
*/
(function () {
  'use strict';
  if (!window.L || !document.getElementById('teaMap')) return;

  var TIGER = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/';
  var TRACTS = TIGER + 'tigerWMS_Current/MapServer/8/query';
  var MSA = TIGER + 'tigerWMS_Current/MapServer/93/query';
  var MICRO = TIGER + 'tigerWMS_Current/MapServer/91/query';
  var PLACES = TIGER + 'tigerWMS_Census2020/MapServer/26/query';   // incorporated places, with POP100
  var ESRI = 'https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/ACS_Employment_Status_Boundaries/FeatureServer/';
  var API = '/api/acs';
  var THRESH = 1.5;
  var RURAL_POP = 20000;

  var map = L.map('teaMap', { scrollWheelZoom: false, zoomControl: true }).setView([39.5, -98.35], 4);
  // Basemap: Esri Light Gray Canvas (no API key). Place labels sit in their own pane
  // above the tract shading so street and city names stay readable. If Esri tiles
  // fail repeatedly, switch to OpenStreetMap's standard tiles.
  var ESRI_TILES = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/';
  var ESRI_ATTR = 'Basemap &copy; Esri, HERE, Garmin, &copy; OpenStreetMap contributors | Boundaries and data: U.S. Census Bureau';
  map.createPane('labels');
  map.getPane('labels').style.zIndex = 450;
  map.getPane('labels').style.pointerEvents = 'none';
  var base = L.tileLayer(ESRI_TILES + 'World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 16, attribution: ESRI_ATTR
  }).addTo(map);
  var labels = L.tileLayer(ESRI_TILES + 'World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 16, pane: 'labels'
  }).addTo(map);
  var tileErrors = 0;
  base.on('tileerror', function () {
    if (++tileErrors !== 4) return;
    map.removeLayer(base); map.removeLayer(labels);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Boundaries and data: U.S. Census Bureau'
    }).addTo(map);
  });
  map.on('focus', function () { map.scrollWheelZoom.enable(); });
  map.on('blur', function () { map.scrollWheelZoom.disable(); });

  var out = document.getElementById('teaOut');
  var form = document.getElementById('teaForm');
  var input = document.getElementById('teaAddr');

  var state = null;   // current analysis
  var layer = null;   // geojson layer of tracts
  var marker = null;
  var natCache = null;
  var busy = 0;

  /* ---------------------------------------------------------- helpers */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function pct(x) { return (x * 100).toFixed(1) + '%'; }
  function num(x) { return Math.round(x).toLocaleString('en-US'); }

  function arc(url, params, post) {
    var body = new URLSearchParams(params);
    body.set('f', params.f || 'json');
    var req = post
      ? fetch(url, { method: 'POST', body: body, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
      : fetch(url + '?' + body.toString());
    return req.then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (j) {
      if (j && j.error) throw new Error(j.error.message || 'Query failed');
      return j;
    });
  }

  function pointParams(lon, lat, fields) {
    return {
      geometry: lon + ',' + lat, geometryType: 'esriGeometryPoint', inSR: '4326',
      spatialRel: 'esriSpatialRelIntersects', outFields: fields, returnGeometry: 'false'
    };
  }

  function jsonp(url, timeout) {
    return new Promise(function (resolve, reject) {
      var cb = 'teaCb' + Date.now() + Math.floor(Math.random() * 1000);
      var s = document.createElement('script');
      var t = setTimeout(function () { done(); reject(new Error('timeout')); }, timeout || 8000);
      function done() { clearTimeout(t); delete window[cb]; if (s.parentNode) s.parentNode.removeChild(s); }
      window[cb] = function (data) { done(); resolve(data); };
      s.onerror = function () { done(); reject(new Error('geocoder unavailable')); };
      s.src = url + (url.indexOf('?') > -1 ? '&' : '?') + 'callback=' + cb;
      document.head.appendChild(s);
    });
  }

  /* ---------------------------------------------------------- geocoding */
  function geocode(q) {
    var census = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?benchmark=Public_AR_Current&format=jsonp&address='
      + encodeURIComponent(q);
    return jsonp(census, 7000).then(function (d) {
      var m = d && d.result && d.result.addressMatches && d.result.addressMatches[0];
      if (!m) throw new Error('no match');
      return { lon: m.coordinates.x, lat: m.coordinates.y, label: m.matchedAddress, src: 'U.S. Census Geocoder' };
    }).catch(function () {
      var url = 'https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=us&q=' + encodeURIComponent(q);
      return fetch(url, { headers: { 'Accept': 'application/json' } }).then(function (r) { return r.json(); }).then(function (a) {
        if (!a || !a.length) throw new Error('We could not find that address. Try adding the city and state, or click the map.');
        return { lon: +a[0].lon, lat: +a[0].lat, label: a[0].display_name, src: 'OpenStreetMap Nominatim' };
      });
    });
  }

  /* ---------------------------------------------------------- tracts */
  function projectTract(lon, lat) {
    var p = pointParams(lon, lat, 'GEOID,NAME,STATE,COUNTY');
    p.returnGeometry = 'true'; p.outSR = '4326'; p.geometryPrecision = '6';
    return arc(TRACTS, p).then(function (j) {
      if (!j.features || !j.features.length) throw new Error('No census tract found here. TEA analysis applies to U.S. locations only.');
      return j.features[0];
    });
  }

  function adjacentTracts(feat) {
    var geom = JSON.stringify({ rings: feat.geometry.rings, spatialReference: { wkid: 4326 } });
    return arc(TRACTS, {
      geometry: geom, geometryType: 'esriGeometryPolygon', inSR: '4326', spatialRel: 'esriSpatialRelIntersects',
      outFields: 'GEOID,NAME,STATE,COUNTY', returnGeometry: 'true', outSR: '4326', geometryPrecision: '5',
      maxAllowableOffset: '0.00005', f: 'geojson'
    }, true);
  }

  /* ---------------------------------------------------------- ACS data */
  function acsFromApi(geoids) {
    return fetch(API + '?tracts=' + geoids.join(',')).then(function (r) {
      if (!r.ok) throw new Error('api ' + r.status);
      return r.json();
    }).then(function (d) {
      if (!d || !d.tracts || !d.national) throw new Error('api shape');
      return d;
    });
  }

  var esriVintage = null;
  function esriLabel() {
    if (esriVintage) return Promise.resolve(esriVintage);
    return arc(ESRI + '2', {}).then(function (j) {
      var txt = (j.description || '') + ' ' + (j.copyrightText || '');
      var m = txt.match(/(20\d\d)\s*[-–]\s*(20\d\d)/);
      esriVintage = m ? 'ACS ' + m[1] + '-' + m[2] + ' 5-year estimates' : 'ACS 5-year estimates';
      return esriVintage;
    }).catch(function () { esriVintage = 'ACS 5-year estimates'; return esriVintage; });
  }

  function acsFromEsri(geoids) {
    var where = "GEOID IN ('" + geoids.join("','") + "')";
    var tr = arc(ESRI + '2/query', {
      where: where, outFields: 'GEOID,NAME,B23025_003E,B23025_005E', returnGeometry: 'false', resultRecordCount: '200'
    }, true);
    var nat = natCache ? Promise.resolve(natCache) : arc(ESRI + '0/query', {
      where: "GEOID <> '72'", returnGeometry: 'false',
      outStatistics: JSON.stringify([
        { statisticType: 'sum', onStatisticField: 'B23025_003E', outStatisticFieldName: 'lf' },
        { statisticType: 'sum', onStatisticField: 'B23025_005E', outStatisticFieldName: 'un' }])
    }).then(function (j) {
      var a = j.features[0].attributes;
      return { lf: a.lf || a.LF, un: a.un || a.UN };
    });
    return Promise.all([tr, nat, esriLabel()]).then(function (r) {
      var tracts = {};
      (r[0].features || []).forEach(function (f) {
        var a = f.attributes;
        tracts[a.GEOID] = { lf: a.B23025_003E || 0, un: a.B23025_005E || 0, name: a.NAME };
      });
      return { source: 'Esri Living Atlas (U.S. Census Bureau ACS)', vintage: r[2], national: r[1], tracts: tracts };
    });
  }

  function acs(geoids) {
    return acsFromApi(geoids).catch(function () { return acsFromEsri(geoids); }).then(function (d) {
      natCache = d.national;
      return d;
    });
  }

  /* ---------------------------------------------------------- rural */
  function rural(lon, lat) {
    var msa = arc(MSA, pointParams(lon, lat, 'NAME,GEOID')).catch(function () { return null; });
    var micro = arc(MICRO, pointParams(lon, lat, 'NAME')).catch(function () { return null; });
    var place = arc(PLACES, pointParams(lon, lat, 'NAME,POP100,LSADC')).catch(function () { return null; });
    return Promise.all([msa, micro, place]).then(function (r) {
      var m = r[0] && r[0].features && r[0].features[0];
      var mi = r[1] && r[1].features && r[1].features[0];
      var p = r[2] && r[2].features && r[2].features[0];
      if (!r[0] || !r[2]) return { ok: null, why: 'The metro area or city boundary service did not respond. Try again in a moment.' };
      if (m) return { ok: false, why: 'Inside the ' + m.attributes.NAME.replace(/ Metro Area$/, '') + ' metropolitan statistical area.' };
      if (p && p.attributes.POP100 >= RURAL_POP) {
        return { ok: false, why: 'Outside any metro area, but inside ' + p.attributes.NAME + ', population ' + num(p.attributes.POP100) + ' (2020 Census).' };
      }
      var why = 'Outside any metropolitan statistical area';
      why += p ? ', and inside ' + p.attributes.NAME + ' (population ' + num(p.attributes.POP100) + ', under 20,000).' : ', and outside any incorporated city.';
      if (mi) why += ' Located in the ' + mi.attributes.NAME.replace(/ Micro Area$/, '') + ' micropolitan area, which does not disqualify a rural TEA.';
      return { ok: true, why: why };
    });
  }

  /* ---------------------------------------------------------- math */
  function rateOf(t) { return t && t.lf > 0 ? t.un / t.lf : null; }

  function combo(ids) {
    var lf = 0, un = 0;
    ids.forEach(function (g) { var t = state.data.tracts[g]; if (t && t.lf > 0) { lf += t.lf; un += t.un; } });
    return { lf: lf, un: un, rate: lf > 0 ? un / lf : null };
  }

  /* Best combination: the project tract plus the adjacent tracts with the highest rates,
     added in descending order while each one raises the weighted average. Adding items
     in ratio order and stopping at the first that does not help maximizes the ratio. */
  function best() {
    var sel = [state.pid];
    var cur = combo(sel);
    state.neighbors.slice().sort(function (a, b) {
      return (rateOf(state.data.tracts[b]) || 0) - (rateOf(state.data.tracts[a]) || 0);
    }).forEach(function (g) {
      var r = rateOf(state.data.tracts[g]);
      if (r != null && cur.rate != null && r > cur.rate) { sel.push(g); cur = combo(sel); }
    });
    return sel;
  }

  /* ---------------------------------------------------------- rendering */
  function styleFor(g) {
    var t = state.data.tracts[g];
    var r = rateOf(t);
    var q = r != null && r >= state.threshold - 1e-9;
    var on = state.selected.indexOf(g) > -1;
    if (g === state.pid) return { color: '#0E1A3D', weight: 3.5, fillColor: q ? '#B79A4F' : '#0E1A3D', fillOpacity: q ? 0.5 : 0.12 };
    if (on) return { color: '#B79A4F', weight: 2, fillColor: '#B79A4F', fillOpacity: q ? 0.55 : 0.25 };
    return { color: '#7C8496', weight: 1, fillColor: q ? '#B79A4F' : '#0E1A3D', fillOpacity: q ? 0.3 : 0.05, dashArray: '3 3' };
  }

  function drawLayer(fc) {
    if (layer) map.removeLayer(layer);
    layer = L.geoJSON(fc, {
      style: function (f) { return styleFor(f.properties.GEOID); },
      onEachFeature: function (f, l) {
        var g = f.properties.GEOID;
        var r = rateOf(state.data.tracts[g]);
        l.bindTooltip(esc(f.properties.NAME) + '<br>' + (r == null ? 'No labor force data' : 'Unemployment ' + pct(r)), { className: 'tt', sticky: true });
        l.on('click', function (ev) {
          L.DomEvent.stopPropagation(ev);
          if (g !== state.pid) toggle(g);
        });
      }
    }).addTo(map);
    map.fitBounds(layer.getBounds(), { padding: [24, 24] });
  }

  function restyle() { if (layer) layer.eachLayer(function (l) { l.setStyle(styleFor(l.feature.properties.GEOID)); }); }

  function toggle(g) {
    var i = state.selected.indexOf(g);
    if (i > -1) state.selected.splice(i, 1); else state.selected.push(g);
    restyle(); panel();
  }

  function verdict(cls, title, value, detail) {
    return '<div class="verdict ' + cls + '"><div class="vt">' + title + '</div><div class="vv">' + value + '</div>'
      + (detail ? '<div class="vd">' + detail + '</div>' : '') + '</div>';
  }

  function panel() {
    var s = state;
    var nat = s.natRate;
    var c = combo(s.selected);
    var proj = rateOf(s.data.tracts[s.pid]);
    var b = combo(s.bestSel);
    var bestOk = b.rate != null && b.rate >= s.threshold - 1e-9;
    var selOk = c.rate != null && c.rate >= s.threshold - 1e-9;
    var html = '<div class="tea-addr"><strong>' + esc(s.label) + '</strong>' + esc(s.tractName) + ' &middot; GEOID ' + esc(s.pid) + '</div>';

    var anyOk = bestOk || (s.rural && s.rural.ok);
    var ruralPending = !s.rural;
    html += verdict(anyOk ? 'yes' : (ruralPending ? 'wait' : 'no'), 'Indicative result',
      anyOk ? 'May qualify as a TEA' : (ruralPending ? 'Checking rural status&hellip;' : 'Does not appear to qualify'),
      anyOk ? 'Based on ' + (bestOk && s.rural && s.rural.ok ? 'both the high-unemployment and rural tests.' : bestOk ? 'the high-unemployment test.' : 'the rural test.') : '');

    html += verdict(bestOk ? 'yes' : 'no', 'High unemployment',
      bestOk ? (s.bestSel.length === 1 ? 'Project tract qualifies on its own' : 'Qualifies with ' + (s.bestSel.length - 1) + ' adjacent tract' + (s.bestSel.length > 2 ? 's' : ''))
             : 'Does not reach 150% of the national rate',
      'Threshold ' + pct(s.threshold) + ' (150% of the ' + pct(nat) + ' national rate). Project tract ' + (proj == null ? 'has no labor force data' : pct(proj))
      + '. Best combination ' + (b.rate == null ? 'n/a' : pct(b.rate)) + '.');

    html += s.rural
      ? verdict(s.rural.ok ? 'yes' : (s.rural.ok === false ? 'no' : 'wait'), 'Rural',
          s.rural.ok ? 'Appears to meet the rural definition' : (s.rural.ok === false ? 'Not rural' : 'Unavailable'), esc(s.rural.why))
      : verdict('wait', 'Rural', '<span class="spin"></span>Checking metro area and city boundaries', '');

    var rows = [s.pid].concat(s.neighbors.slice().sort(function (a, b2) {
      return (rateOf(s.data.tracts[b2]) || -1) - (rateOf(s.data.tracts[a]) || -1);
    })).map(function (g) {
      var t = s.data.tracts[g] || { lf: 0, un: 0 };
      var r = rateOf(t);
      var on = s.selected.indexOf(g) > -1;
      var cls = (g === s.pid ? 'proj ' : '') + (r != null && r >= s.threshold - 1e-9 ? 'q' : '');
      var nm = (s.names[g] || g).replace('Census Tract ', 'Tract ');
      return '<tr class="' + cls + '"><td><input type="checkbox" data-g="' + g + '"' + (on ? ' checked' : '') + (g === s.pid ? ' disabled' : '') + ' aria-label="Include ' + esc(nm) + '"></td>'
        + '<td>' + esc(nm) + (g === s.pid ? ' (project)' : '') + '</td>'
        + '<td class="r">' + num(t.lf) + '</td><td class="r">' + (r == null ? '&ndash;' : pct(r)) + '</td></tr>';
    }).join('');

    html += '<div class="tea-sec"><h5>Your combination: ' + (c.rate == null ? 'n/a' : pct(c.rate)) + (selOk ? ' &middot; meets threshold' : ' &middot; below threshold') + '</h5>'
      + '<div class="tea-btns"><button type="button" data-act="best">Use best combination</button><button type="button" data-act="proj">Project tract only</button>'
      + '<button type="button" data-act="all">All adjacent</button><button type="button" data-act="copy">Copy summary</button></div>'
      + '<table class="ttable"><thead><tr><th></th><th>Tract</th><th class="r">Labor force</th><th class="r">Unemp.</th></tr></thead><tbody>' + rows + '</tbody></table></div>';

    html += '<p class="tea-src">Unemployment: ' + esc(s.data.vintage) + ', ' + esc(s.data.source) + '. Combined rates are labor-force weighted (total unemployed divided by total civilian labor force). '
      + 'Boundaries and populations: U.S. Census Bureau TIGERweb. Location: ' + esc(s.geoSrc) + '. Indicative only; USCIS makes TEA determinations.</p>';
    out.innerHTML = html;
  }

  function summary() {
    var s = state, c = combo(s.selected);
    var lines = ['Catalyst EB-5 TEA Map, indicative result', 'Location: ' + s.label, 'Project tract: ' + s.tractName + ' (' + s.pid + ')',
      'Data: ' + s.data.vintage + ', ' + s.data.source,
      'National rate: ' + pct(s.natRate) + ', threshold: ' + pct(s.threshold),
      'Selected combination (' + s.selected.length + ' tracts): ' + (c.rate == null ? 'n/a' : pct(c.rate)) + (c.rate >= s.threshold - 1e-9 ? ', meets threshold' : ', below threshold'),
      'Tracts: ' + s.selected.join(', ')];
    if (s.rural) lines.push('Rural: ' + (s.rural.ok ? 'appears rural' : 'not rural') + '. ' + s.rural.why);
    return lines.join('\n');
  }

  out.addEventListener('change', function (ev) {
    var g = ev.target.getAttribute && ev.target.getAttribute('data-g');
    if (g) toggle(g);
  });
  out.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('button[data-act]');
    if (!b || !state) return;
    var a = b.getAttribute('data-act');
    if (a === 'best') state.selected = state.bestSel.slice();
    if (a === 'proj') state.selected = [state.pid];
    if (a === 'all') state.selected = [state.pid].concat(state.neighbors);
    if (a === 'copy') {
      var txt = summary();
      if (navigator.clipboard) navigator.clipboard.writeText(txt).then(function () { b.textContent = 'Copied'; });
      return;
    }
    restyle(); panel();
  });

  function loading(msg) {
    out.innerHTML = '<div class="verdict wait"><div class="vt">Working</div><div class="vv"><span class="spin"></span>' + esc(msg) + '</div></div>';
  }
  function fail(err) {
    out.innerHTML = '<div class="verdict no"><div class="vt">Something went wrong</div><div class="vv">We could not complete the check.</div><div class="vd">'
      + esc(err && err.message ? err.message : err) + '</div></div>';
  }

  /* ---------------------------------------------------------- pipeline */
  function analyze(lon, lat, label, geoSrc) {
    var run = ++busy;
    if (marker) map.removeLayer(marker);
    marker = L.circleMarker([lat, lon], { radius: 7, color: '#fff', weight: 2, fillColor: '#B79A4F', fillOpacity: 1 }).addTo(map);
    loading('Finding the census tract');
    var feat;
    projectTract(lon, lat).then(function (f) {
      feat = f;
      loading('Finding adjacent tracts');
      return adjacentTracts(f);
    }).then(function (fc) {
      if (run !== busy) return;
      var pid = feat.attributes.GEOID;
      var names = {};
      (fc.features || []).forEach(function (f) { names[f.properties.GEOID] = f.properties.NAME; });
      var ids = Object.keys(names);
      if (ids.indexOf(pid) < 0) ids.push(pid);
      loading('Loading ACS unemployment data');
      return acs(ids).then(function (d) {
        if (run !== busy) return;
        var natRate = d.national.un / d.national.lf;
        state = {
          pid: pid, names: names, neighbors: ids.filter(function (g) { return g !== pid; }),
          data: d, natRate: natRate, threshold: natRate * THRESH, label: label || (lat.toFixed(5) + ', ' + lon.toFixed(5)),
          tractName: feat.attributes.NAME, geoSrc: geoSrc || 'map click', rural: null
        };
        state.bestSel = best();
        state.selected = state.bestSel.slice();
        drawLayer(fc);
        panel();
        rural(lon, lat).then(function (r) { if (run === busy) { state.rural = r; panel(); } });
      });
    }).catch(function (err) { if (run === busy) fail(err); });
  }

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var q = input.value.trim();
    if (!q) return;
    loading('Locating address');
    geocode(q).then(function (g) {
      analyze(g.lon, g.lat, g.label, g.src);
    }).catch(fail);
  });

  map.on('click', function (ev) {
    analyze(ev.latlng.lng, ev.latlng.lat, null, 'map click');
  });

  /* deep link: /tea-map/?address=... */
  var qs = new URLSearchParams(location.search).get('address');
  if (qs) { input.value = qs; form.dispatchEvent(new Event('submit', { cancelable: true })); }
})();
