const axios = require('axios').create({
    httpsAgent: new (require('https').Agent)({ rejectUnauthorized: false })
  });
const fs = require('fs');
const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');

const getBaseUrl = () => argv.url.replace(/\/+$/, '');

const getServiceMetadata = async () => {
  const requesturl = `${getBaseUrl()}?f=json`;
  if (argv.debug) console.log(`Fetching service metadata from ${requesturl}`);
  const response = await axios.get(requesturl);
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
    const response = await axios.get(requesturl);
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
  const response = await axios.get(`${getBaseUrl()}/query`, { params: queryParams });
    return response.data;
};

const getObjectIds = async () => {
  const queryParams = {
    where: '1=1',
    returnIdsOnly: true,
    f: 'json'
  };
  if (argv.debug) console.log('Fetching object IDs for fallback pagination');
  const response = await axios.get(`${getBaseUrl()}/query`, { params: queryParams });
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
    const response = await axios.post(`${getBaseUrl()}/query`, new URLSearchParams(queryParams).toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    return response.data;
  }

  const response = await axios.get(`${getBaseUrl()}/query`, { params: queryParams });
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
  .argv;

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

main();