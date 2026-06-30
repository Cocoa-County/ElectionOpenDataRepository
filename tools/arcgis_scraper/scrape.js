const https = require('https');
const axios = require('axios').create({
  httpsAgent: new https.Agent({ rejectUnauthorized: false }),
  headers: {
    // Some ArcGIS endpoints sit behind WAF rules that reject non-browser clients.
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    Accept: 'application/json, text/plain, */*',
    Referer: 'https://www.arcgis.com/',
    Origin: 'https://www.arcgis.com'
  }
});
const fs = require('fs');
const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');

const getBaseUrl = () => argv.url.replace(/\/+$/, '');

const parseHeaderEntries = (headerEntries) => {
  const parsed = {};

  for (const entry of headerEntries || []) {
    const separatorIndex = entry.indexOf(':');
    if (separatorIndex <= 0) {
      if (argv.debug) console.warn(`Skipping invalid --header value: ${entry}`);
      continue;
    }

    const key = entry.slice(0, separatorIndex).trim();
    const value = entry.slice(separatorIndex + 1).trim();
    if (!key || !value) {
      if (argv.debug) console.warn(`Skipping invalid --header value: ${entry}`);
      continue;
    }

    parsed[key] = value;
  }

  return parsed;
};

const configureRequestHeaders = () => {
  const extraHeaders = parseHeaderEntries(argv.header);
  if (argv.cookie) {
    extraHeaders.Cookie = argv.cookie;
  }

  Object.assign(axios.defaults.headers.common, extraHeaders);

  if (argv.debug && Object.keys(extraHeaders).length > 0) {
    console.log(`Applied ${Object.keys(extraHeaders).length} custom request header(s).`);
  }
};

const summarizeResponseBody = (data) => {
  if (data === undefined || data === null) return '(empty)';
  if (typeof data === 'string') return data.slice(0, 400);

  try {
    return JSON.stringify(data).slice(0, 400);
  } catch (_error) {
    return '(unserializable response body)';
  }
};

const isCloudflareChallenge = (status, contentType, bodyPreview) => {
  if (status !== 403) return false;
  if (!String(contentType).toLowerCase().includes('text/html')) return false;

  const haystack = String(bodyPreview).toLowerCase();
  return haystack.includes('cloudflare') || haystack.includes('attention required');
};

const logHttpError = (error, label) => {
  if (!argv.debug) return;

  const status = error?.response?.status;
  const statusText = error?.response?.statusText || '';
  const contentType = error?.response?.headers?.['content-type'] || '(unknown)';
  const bodyPreview = summarizeResponseBody(error?.response?.data);

  if (status) {
    console.error(`${label} failed: HTTP ${status} ${statusText}`.trim());
    console.error(`content-type: ${contentType}`);
    console.error(`response preview: ${bodyPreview}`);

    if (isCloudflareChallenge(status, contentType, bodyPreview)) {
      console.error('Detected Cloudflare challenge. This endpoint is blocking non-browser HTTP clients.');
      console.error('Try a fresh browser session cookie with --cookie, or fetch the data from an interactive browser workflow.');
    }
  } else {
    console.error(`${label} failed: ${error.message}`);
  }
};

const getServiceMetadata = async () => {
  const requesturl = `${getBaseUrl()}?f=json`;
  if (argv.debug) console.log(`Fetching service metadata from ${requesturl}`);
  let response;
  try {
    response = await axios.get(requesturl);
  } catch (error) {
    logHttpError(error, 'Service metadata request');
    throw error;
  }
  const maxRecordCount = response.data?.maxRecordCount || 1000;
  const objectIdField = response.data?.objectIdField || 'OBJECTID';
  if (argv.debug) {
    console.log(`maxRecordCount: ${maxRecordCount}`);
    console.log(`objectIdField: ${objectIdField}`);
  }
  return { maxRecordCount, objectIdField };
};

const getObjectCount = async () => {
  const requesturl = `${getBaseUrl()}/query?where=1=1&returnCountOnly=true&f=json`;
  if (argv.debug) console.log(`Fetching object count from ${requesturl}`);
  let response;
  try {
    response = await axios.get(requesturl);
  } catch (error) {
    logHttpError(error, 'Object count request');
    throw error;
  }
  const count = response.data?.count ?? response.data?.properties?.count ?? 0;
  if (argv.debug) console.log(`Object count: ${count}`);
  return count;
};

const fetchDataByOffset = async (offset, pageSize, idField) => {
  const queryParams = {
    where: '1=1',
    outFields: '*',
    orderByFields: `${idField} ASC`,
    resultOffset: offset,
    resultRecordCount: pageSize,
    f: 'geojson'
  };
  if (argv.debug) console.log(`Fetching data by offset=${offset} pageSize=${pageSize}`);
  let response;
  try {
    response = await axios.get(`${getBaseUrl()}/query`, { params: queryParams });
  } catch (error) {
    logHttpError(error, `Offset query request (offset=${offset})`);
    throw error;
  }
    return response.data;
};

const getObjectIds = async () => {
  const queryParams = {
    where: '1=1',
    returnIdsOnly: true,
    f: 'json'
  };
  if (argv.debug) console.log('Fetching object IDs for fallback pagination');
  let response;
  try {
    response = await axios.get(`${getBaseUrl()}/query`, { params: queryParams });
  } catch (error) {
    logHttpError(error, 'Object ID request');
    throw error;
  }
  const objectIds = response.data?.objectIds || [];
  const objectIdFieldName = response.data?.objectIdFieldName || 'OBJECTID';
  return { objectIds, objectIdFieldName };
};

const fetchDataByIds = async (idField, ids) => {
  const whereClause = `${idField} IN (${ids.join(',')})`;
  const queryParams = {
    where: whereClause,
    outFields: '*',
    f: 'geojson'
  };

  // Use POST for larger batches to avoid URL length issues.
  if (whereClause.length > 1500) {
    let response;
    try {
      response = await axios.post(`${getBaseUrl()}/query`, new URLSearchParams(queryParams).toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
    } catch (error) {
      logHttpError(error, 'Fallback POST chunk request');
      throw error;
    }
    return response.data;
  }

  let response;
  try {
    response = await axios.get(`${getBaseUrl()}/query`, { params: queryParams });
  } catch (error) {
    logHttpError(error, 'Fallback GET chunk request');
    throw error;
  }
  return response.data;
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
  .option('header', {
    type: 'array',
    description: 'Additional request header in "Name: Value" format (repeatable)'
  })
  .option('cookie', {
    type: 'string',
    description: 'Cookie header value to include in requests'
  })
  .argv;

configureRequestHeaders();

const main = async () => {
    let combinedData = { type: "FeatureCollection", features: [] };
  const metadata = await getServiceMetadata();
    const count = await getObjectCount();
  const idField = metadata.objectIdField;
  const pageSize = Math.max(1, metadata.maxRecordCount);
  if (argv.debug) {
    console.log(`Using id field: ${idField}`);
    console.log(`Page size: ${pageSize}`);
    console.log(`Total count: ${count}`);
  }

  const seenIds = new Set();
    let totalLoaded = 0;
  let offset = 0;
  let usedFallback = false;

  try {
    while (offset < count) {
      const data = await fetchDataByOffset(offset, pageSize, idField);
      const fetchedCount = data?.features?.length || 0;

      if (fetchedCount === 0) {
        break;
      }

      const added = appendUniqueFeatures(combinedData, data, idField, seenIds);
      totalLoaded += added;

      if (argv.debug) {
        console.log(
          `Offset ${offset}: fetched ${fetchedCount}, added ${added}, total unique loaded: ${totalLoaded} / ${count}`
        );
      }

      if (fetchedCount < pageSize) {
        break;
      }

      offset += pageSize;
    }

    // If we did not reach expected count, force fallback to returnIdsOnly strategy.
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

    const idsResponse = await getObjectIds();
    const fallbackIdField = idsResponse.objectIdFieldName || idField;
    const idChunks = chunk(idsResponse.objectIds, 200);

    for (const idChunk of idChunks) {
      const data = await fetchDataByIds(fallbackIdField, idChunk);
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
  if (argv.debug) console.log(`Data written to ${outputFileName}`);
};

main().catch((error) => {
  logHttpError(error, 'Scrape');
  console.error(`Fatal error: ${error.message}`);
  process.exitCode = 1;
});