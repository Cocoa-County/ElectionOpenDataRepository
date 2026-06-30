const fs = require('fs');
const path = require('path');

const parseArgs = () => {
  const args = process.argv.slice(2);
  const opts = {
    url: '',
    repoOutput: '',
    rawDir: path.join(__dirname, 'downloads'),
    lang: 'en',
    debug: false
  };

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];

    if (arg === '-u' || arg === '--url') {
      opts.url = args[i + 1] || '';
      i += 1;
      continue;
    }

    if (arg === '-o' || arg === '--repo-output') {
      opts.repoOutput = args[i + 1] || '';
      i += 1;
      continue;
    }

    if (arg === '--raw-dir') {
      opts.rawDir = args[i + 1] || opts.rawDir;
      i += 1;
      continue;
    }

    if (arg === '--lang') {
      opts.lang = args[i + 1] || 'en';
      i += 1;
      continue;
    }

    if (arg === '-d' || arg === '--debug') {
      opts.debug = true;
      continue;
    }

    if (arg === '-h' || arg === '--help') {
      console.log('Usage: node scrape.js -u <clarity-election-url> -o <repo-election.json> [--raw-dir downloads] [--lang en] [-d]');
      process.exit(0);
    }
  }

  if (!opts.url) {
    throw new Error('Missing required -u/--url argument');
  }

  if (!opts.repoOutput) {
    throw new Error('Missing required -o/--repo-output argument');
  }

  return opts;
};

const normalizeUrl = (url) => url.replace(/\/+$/, '');

const parseElectionPath = (baseUrl) => {
  const parsed = new URL(baseUrl);
  const segments = parsed.pathname.split('/').filter(Boolean);
  if (segments.length < 3) {
    throw new Error(`Unexpected Clarity URL path: ${parsed.pathname}`);
  }

  const [state, county, electionId] = segments;
  return { state, county, electionId };
};

const fetchText = async (url) => {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} while fetching ${url}`);
  }
  return response.text();
};

const fetchJson = async (url) => {
  const text = await fetchText(url);
  try {
    return JSON.parse(text);
  } catch (_error) {
    throw new Error(`Invalid JSON at ${url}`);
  }
};

const ensureDirForFile = (filePath) => {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });
};

const writeJson = (filePath, data) => {
  ensureDirForFile(filePath);
  fs.writeFileSync(filePath, JSON.stringify(data));
};

const getContestPrecinctIds = (electionData) => {
  const firstContest = electionData?.contests?.[0];
  return Object.keys(firstContest?.precincts || {});
};

const loadSiblingGisPrecinctIds = (repoOutputPath) => {
  const dir = path.dirname(repoOutputPath);
  const gisPath = path.join(dir, 'precincts.gis.json');
  if (!fs.existsSync(gisPath)) return null;

  try {
    const gis = JSON.parse(fs.readFileSync(gisPath, 'utf8'));
    const ids = new Set(
      (gis.features || [])
        .map((feature) => String(feature?.properties?.ConsolidatedPrecinct || '').trim())
        .filter(Boolean)
    );
    return ids.size > 0 ? ids : null;
  } catch (_error) {
    return null;
  }
};

const applyPrecinctPrefix = (electionData, prefix) => {
  for (const contest of electionData?.contests || []) {
    const oldMap = contest.precincts || {};
    const newMap = {};

    for (const [id, entry] of Object.entries(oldMap)) {
      const key = String(id);
      const mappedId = key.startsWith(prefix) ? key : `${prefix}${key}`;
      const labelRaw = entry?.label === undefined || entry?.label === null ? '' : String(entry.label);
      const mappedLabel = labelRaw ? (labelRaw.startsWith(prefix) ? labelRaw : `${prefix}${labelRaw}`) : mappedId;
      newMap[mappedId] = { ...entry, label: mappedLabel };
    }

    contest.precincts = newMap;
  }
};

const maybeAlignPrecinctIdsWithGis = (electionData, repoOutputPath, debug) => {
  const gisIds = loadSiblingGisPrecinctIds(repoOutputPath);
  if (!gisIds) return;

  const ids = getContestPrecinctIds(electionData);
  if (ids.length === 0) return;

  const scoreIdentity = ids.filter((id) => gisIds.has(id)).length;
  const scoreCPrefix = ids.filter((id) => gisIds.has(id.startsWith('C') ? id : `C${id}`)).length;

  if (scoreCPrefix > scoreIdentity) {
    applyPrecinctPrefix(electionData, 'C');
    if (debug) {
      console.log(`Applied precinct prefix 'C' based on GIS overlap (${scoreIdentity} -> ${scoreCPrefix}).`);
    }
  }
};

const discoverVersion = async (baseUrl, debug) => {
  const versionUrl = `${baseUrl}/current_ver.txt`;
  const versionText = await fetchText(versionUrl);
  const version = versionText.trim();

  if (!/^\d+$/.test(version)) {
    throw new Error(`Unexpected current_ver.txt contents: ${version}`);
  }

  if (debug) console.log(`Discovered data version: ${version}`);
  return version;
};

const fetchFirstJson = async (urls, debug) => {
  for (const url of urls) {
    try {
      if (debug) console.log(`Trying ${url}`);
      const data = await fetchJson(url);
      return { data, sourceUrl: url };
    } catch (_error) {
      // Continue to the next known variant.
    }
  }

  throw new Error(`Unable to locate JSON resource from candidates:\n${urls.join('\n')}`);
};

const fetchAllJson = async (baseUrl, version, lang, debug) => {
  const candidates = [
    `${baseUrl}/${version}/json/ALL.json`,
    `${baseUrl}/${version}/json/all.json`,
    `${baseUrl}/${version}/json/${lang}/all.json`
  ];

  return fetchFirstJson(candidates, debug);
};

const fetchSumJson = async (baseUrl, version, lang, debug) => {
  const candidates = [
    `${baseUrl}/${version}/json/sum.json`,
    `${baseUrl}/${version}/json/${lang}/summary.json`
  ];

  return fetchFirstJson(candidates, debug);
};

const fetchElectionSettingsJson = async (baseUrl, version, lang, debug) => {
  const candidates = [
    `${baseUrl}/${version}/json/${lang}/electionsettings.json`,
    `${baseUrl}/${version}/json/electionsettings.json`
  ];

  return fetchFirstJson(candidates, debug);
};

const toNumber = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

const normalizeChoiceLabel = (label, sourceIndex) => {
  const raw = String(label || '').trim();
  const upper = raw.toUpperCase();

  if (upper === 'BONDS-YES') return 'Yes';
  if (upper === 'BONDS-NO') return 'No';

  return raw || `Choice ${sourceIndex + 1}`;
};

const normalizeParty = (party) => {
  const p = String(party || '').trim();
  return p || undefined;
};

const toPartyBucket = (party) => {
  const p = String(party || '').toUpperCase();
  if (p === 'DEM') return 'blue';
  if (p === 'REP') return 'red';
  return null;
};

const toYesNoColor = (label) => {
  const normalized = String(label || '').trim().toUpperCase();
  if (normalized === 'YES') return 'green1';
  if (normalized === 'NO') return 'red1';
  return null;
};

const withPartyColors = (sortedChoices) => {
  let blueCount = 0;
  let redCount = 0;

  return sortedChoices.map((choice, index) => {
    const out = {
      index,
      id: index,
      label: choice.label,
      party: choice.party,
      votes: choice.votes,
      sourceIndex: choice.sourceIndex
    };

    const yesNoColor = toYesNoColor(choice.label);
    if (yesNoColor) {
      out.color = yesNoColor;
      return out;
    }

    const bucket = toPartyBucket(choice.party);
    if (bucket === 'blue') {
      blueCount += 1;
      if (blueCount <= 4) out.color = `blue${blueCount}`;
    } else if (bucket === 'red') {
      redCount += 1;
      if (redCount <= 4) out.color = `red${redCount}`;
    }

    return out;
  });
};

const buildContestLookup = (sumData) => {
  const contests = Array.isArray(sumData?.Contests) ? sumData.Contests : Array.isArray(sumData) ? sumData : [];
  const lookup = new Map();

  for (const contest of contests) {
    const contestId = String(contest?.K ?? '').trim();
    if (!contestId) continue;

    const names = Array.isArray(contest?.CH) ? contest.CH : [];
    const parties = Array.isArray(contest?.P) ? contest.P : [];
    const votes = Array.isArray(contest?.V) ? contest.V : [];
    const voteFor = toNumber(contest?.VF) || 1;

    const sourceChoices = names.map((name, sourceIndex) => ({
      sourceIndex,
      label: normalizeChoiceLabel(name, sourceIndex),
      party: normalizeParty(parties[sourceIndex]),
      votes: toNumber(votes[sourceIndex])
    }));

    const sortedChoices = [...sourceChoices].sort((a, b) => {
      if (b.votes !== a.votes) return b.votes - a.votes;
      return a.label.localeCompare(b.label);
    });

    const sortedChoiceOutput = withPartyColors(sortedChoices);

    lookup.set(contestId, {
      id: contestId,
      label: String(contest?.C || contestId),
      voteFor,
      choices: sortedChoiceOutput
    });
  }

  return lookup;
};

const buildPrecinctEntry = (votesBySourceIndex, sortedChoices, totalHint) => {
  const results = sortedChoices.map((choice) => toNumber(votesBySourceIndex?.[choice.sourceIndex]));
  const total = toNumber(totalHint) || results.reduce((sum, value) => sum + value, 0);
  const maxVote = results.length > 0 ? Math.max(...results) : 0;
  const winner = maxVote > 0
    ? results.flatMap((value, idx) => (value === maxVote ? [idx] : []))
    : [];
  const percentage = results.map((value) => (total > 0 ? Number((value / total).toFixed(4)) : null));

  return { results, total, winner, percentage };
};

const transformToRepositoryElection = (allData, sumData) => {
  const contestLookup = buildContestLookup(sumData);
  const precinctRows = Array.isArray(allData?.Contests) ? allData.Contests : [];
  const outputContests = new Map();

  for (const row of precinctRows) {
    const precinctId = String(row?.A || '').trim();
    if (!precinctId) continue;

    const contestIds = Array.isArray(row?.C) ? row.C : [];
    const voteRows = Array.isArray(row?.V) ? row.V : [];
    const totals = Array.isArray(row?.T) ? row.T : [];

    for (let i = 0; i < contestIds.length; i += 1) {
      const contestId = String(contestIds[i]);
      const contestMeta = contestLookup.get(contestId);
      if (!contestMeta) continue;

      if (!outputContests.has(contestId)) {
        const choices = contestMeta.choices.map((choice) => {
          const out = {
            index: choice.index,
            id: choice.id,
            label: choice.label,
            votes: choice.votes
          };

          if (choice.party) out.party = choice.party;
          if (choice.color) out.color = choice.color;
          return out;
        });

        outputContests.set(contestId, {
          id: contestMeta.id,
          label: contestMeta.label,
          voteFor: contestMeta.voteFor,
          choices,
          precincts: {}
        });
      }

      const precinctEntry = buildPrecinctEntry(voteRows[i], contestMeta.choices, totals[i]);
      outputContests.get(contestId).precincts[precinctId] = {
        label: precinctId,
        total: precinctEntry.total,
        winner: precinctEntry.winner,
        results: precinctEntry.results,
        percentage: precinctEntry.percentage
      };
    }
  }

  const contests = [...outputContests.values()]
    .sort((a, b) => Number(a.id) - Number(b.id))
    .map((contest, index) => ({
      index,
      id: contest.id,
      label: contest.label,
      voteFor: contest.voteFor,
      choices: contest.choices,
      precincts: contest.precincts
    }));

  return { contests };
};

const main = async () => {
  const opts = parseArgs();
  const baseUrl = normalizeUrl(opts.url);
  const electionPath = parseElectionPath(baseUrl);

  if (opts.debug) console.log(`Base URL: ${baseUrl}`);

  const version = await discoverVersion(baseUrl, opts.debug);
  const allResult = await fetchAllJson(baseUrl, version, opts.lang, opts.debug);
  const sumResult = await fetchSumJson(baseUrl, version, opts.lang, opts.debug);
  const settingsResult = await fetchElectionSettingsJson(baseUrl, version, opts.lang, opts.debug);

  const rawBaseDir = path.join(opts.rawDir, electionPath.state, electionPath.county, electionPath.electionId, version);
  writeJson(path.join(rawBaseDir, 'all.json'), allResult.data);
  writeJson(path.join(rawBaseDir, 'sum.json'), sumResult.data);
  writeJson(path.join(rawBaseDir, 'electionsettings.json'), settingsResult.data);

  const electionData = transformToRepositoryElection(allResult.data, sumResult.data);
  maybeAlignPrecinctIdsWithGis(electionData, opts.repoOutput, opts.debug);
  writeJson(opts.repoOutput, electionData);

  console.log(`Downloaded ${allResult.sourceUrl}`);
  console.log(`Downloaded ${sumResult.sourceUrl}`);
  console.log(`Downloaded ${settingsResult.sourceUrl}`);
  console.log(`Wrote raw files to ${rawBaseDir}`);
  console.log(`Wrote transformed election data to ${opts.repoOutput}`);
};

main().catch((error) => {
  console.error(`Fatal error: ${error.message}`);
  process.exitCode = 1;
});
