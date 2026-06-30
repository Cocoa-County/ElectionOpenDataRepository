const fs = require('fs');
const path = require('path');
const readline = require('readline');
const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');
const { chromium } = require('playwright');

const argv = yargs(hideBin(process.argv))
  .option('debug', {
    alias: 'd',
    type: 'boolean',
    description: 'Debug mode'
  })
  .option('url', {
    alias: 'u',
    type: 'string',
    description: 'Feature service URL',
    demandOption: true
  })
  .option('output', {
    alias: 'o',
    type: 'string',
    description: 'Output file name'
  })
  .option('headless', {
    type: 'boolean',
    default: false,
    description: 'Run browser in headless mode (often blocked by WAF)'
  })
  .option('profileDir', {
    type: 'string',
    description: 'Persistent Chrome profile directory for cookies/session reuse'
  })
  .option('manual', {
    type: 'boolean',
    default: true,
    description: 'Allow manual Cloudflare challenge solve in browser before scraping'
  })
  .argv;

const getBaseUrl = () => argv.url.replace(/\/+$/, '');

const pauseForEnter = async (message) => {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  await new Promise((resolve) => rl.question(`${message}\nPress Enter to continue... `, () => resolve()));
  rl.close();
};

const summarizeBody = (text) => String(text || '').slice(0, 400);

const isCloudflareChallenge = (status, contentType, bodyPreview) => {
  if (status !== 403) return false;
  if (!String(contentType || '').toLowerCase().includes('text/html')) return false;

  const haystack = String(bodyPreview || '').toLowerCase();
  return haystack.includes('cloudflare') || haystack.includes('attention required');
};

const browserRequest = async (page, url, params = {}) => {
  const response = await page.evaluate(async ({ url, params }) => {
    const fullUrl = new URL(url);
    for (const [key, value] of Object.entries(params || {})) {
      fullUrl.searchParams.set(key, String(value));
    }

    const res = await fetch(fullUrl.toString(), {
      method: 'GET',
      credentials: 'include'
    });

    const text = await res.text();
    let data = null;
    try {
      data = JSON.parse(text);
    } catch (_error) {
      data = null;
    }

    return {
      ok: res.ok,
      status: res.status,
      statusText: res.statusText,
      contentType: res.headers.get('content-type') || '',
      data,
      bodyPreview: text.slice(0, 400)
    };
  }, { url, params });

  if (!response.ok) {
    const err = new Error(`HTTP ${response.status} ${response.statusText}`.trim());
    err.http = response;
    throw err;
  }

  return response.data;
};

const fetchJsonWithChallengeHandling = async (page, requestUrl, params, label) => {
  try {
    return await browserRequest(page, requestUrl, params);
  } catch (error) {
    const http = error.http || {};
    const contentType = http.contentType || '(unknown)';
    const bodyPreview = summarizeBody(http.bodyPreview);

    if (argv.debug) {
      if (http.status) {
        console.error(`${label} failed: HTTP ${http.status} ${http.statusText || ''}`.trim());
        console.error(`content-type: ${contentType}`);
        console.error(`response preview: ${bodyPreview}`);
      } else {
        console.error(`${label} failed: ${error.message}`);
      }
    }

    if (!argv.manual || !isCloudflareChallenge(http.status, contentType, bodyPreview)) {
      throw error;
    }

    console.log('Cloudflare challenge detected. Complete challenge in opened browser window.');
    await page.bringToFront();
    await pauseForEnter('After challenge is solved and the page is accessible, continue.');

    return browserRequest(page, requestUrl, params);
  }
};

const appendUniqueFeatures = (targetCollection, sourceData, idField, seenIds) => {
  let added = 0;
  const sourceFeatures = sourceData?.features || [];

  for (const feature of sourceFeatures) {
    const idValue = feature?.properties?.[idField] ?? feature?.id;

    if (idValue === undefined || idValue === null) {
      targetCollection.features.push(feature);
      added += 1;
      continue;
    }

    if (!seenIds.has(idValue)) {
      seenIds.add(idValue);
      targetCollection.features.push(feature);
      added += 1;
    }
  }

  return added;
};

const chunk = (arr, size) => {
  const chunks = [];
  for (let i = 0; i < arr.length; i += size) {
    chunks.push(arr.slice(i, i + size));
  }
  return chunks;
};

const launchBrowserContext = async () => {
  const profileDir = argv.profileDir || path.join(__dirname, '.browser-profile');
  if (!fs.existsSync(profileDir)) fs.mkdirSync(profileDir, { recursive: true });

  return chromium.launchPersistentContext(profileDir, {
    channel: 'chrome',
    headless: argv.headless,
    viewport: { width: 1360, height: 900 }
  });
};

const main = async () => {
  const baseUrl = getBaseUrl();
  const context = await launchBrowserContext();
  const page = context.pages()[0] || await context.newPage();

  try {
    await page.goto(`${baseUrl}?f=json`, { waitUntil: 'domcontentloaded' });

    const metadata = await fetchJsonWithChallengeHandling(page, baseUrl, { f: 'json' }, 'Service metadata request');
    const maxRecordCount = metadata?.maxRecordCount || 1000;
    const idField = metadata?.objectIdField || 'OBJECTID';

    const countResponse = await fetchJsonWithChallengeHandling(
      page,
      `${baseUrl}/query`,
      { where: '1=1', returnCountOnly: 'true', f: 'json' },
      'Object count request'
    );

    const count = countResponse?.count ?? countResponse?.properties?.count ?? 0;
    const pageSize = Math.max(1, maxRecordCount);

    if (argv.debug) {
      console.log(`maxRecordCount: ${maxRecordCount}`);
      console.log(`objectIdField: ${idField}`);
      console.log(`Object count: ${count}`);
    }

    let combinedData = { type: 'FeatureCollection', features: [] };
    const seenIds = new Set();
    let totalLoaded = 0;
    let offset = 0;
    let usedFallback = false;

    try {
      while (offset < count) {
        const data = await fetchJsonWithChallengeHandling(
          page,
          `${baseUrl}/query`,
          {
            where: '1=1',
            outFields: '*',
            orderByFields: `${idField} ASC`,
            resultOffset: offset,
            resultRecordCount: pageSize,
            f: 'geojson'
          },
          `Offset query request (offset=${offset})`
        );

        const fetchedCount = data?.features?.length || 0;
        if (fetchedCount === 0) break;

        const added = appendUniqueFeatures(combinedData, data, idField, seenIds);
        totalLoaded += added;

        if (argv.debug) {
          console.log(`Offset ${offset}: fetched ${fetchedCount}, added ${added}, total unique loaded: ${totalLoaded} / ${count}`);
        }

        if (fetchedCount < pageSize) break;
        offset += pageSize;
      }

      if (totalLoaded < count) {
        throw new Error(`Offset pagination incomplete (${totalLoaded}/${count})`);
      }
    } catch (error) {
      usedFallback = true;
      if (argv.debug) {
        console.log(`Offset pagination failed or incomplete: ${error.message}`);
        console.log('Falling back to returnIdsOnly + ID chunk queries');
      }

      combinedData = { type: 'FeatureCollection', features: [] };
      seenIds.clear();
      totalLoaded = 0;

      const idsResponse = await fetchJsonWithChallengeHandling(
        page,
        `${baseUrl}/query`,
        { where: '1=1', returnIdsOnly: 'true', f: 'json' },
        'Object ID request'
      );

      const objectIds = idsResponse?.objectIds || [];
      const fallbackIdField = idsResponse?.objectIdFieldName || idField;

      for (const idChunk of chunk(objectIds, 200)) {
        const whereClause = `${fallbackIdField} IN (${idChunk.join(',')})`;
        const data = await fetchJsonWithChallengeHandling(
          page,
          `${baseUrl}/query`,
          { where: whereClause, outFields: '*', f: 'geojson' },
          'Fallback chunk request'
        );

        const fetchedCount = data?.features?.length || 0;
        const added = appendUniqueFeatures(combinedData, data, fallbackIdField, seenIds);
        totalLoaded += added;

        if (argv.debug) {
          console.log(`Fallback chunk fetched ${fetchedCount}, added ${added}, total unique loaded: ${totalLoaded}`);
        }
      }
    }

    if (argv.debug) {
      console.log(`Final unique features loaded: ${combinedData.features.length} / expected ${count}`);
      console.log(`Fallback used: ${usedFallback}`);
    }

    const outputFileName = argv.output || 'scrape.json';
    fs.writeFileSync(outputFileName, JSON.stringify(combinedData));
    console.log(`Data written to ${outputFileName}`);
  } finally {
    if (argv.headless) {
      await context.close();
    } else {
      console.log('Browser session kept open for reuse. Close it manually when finished.');
    }
  }
};

main().catch((error) => {
  console.error(`Fatal error: ${error.message}`);
  process.exitCode = 1;
});
