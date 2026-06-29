const axios = require('axios').create({
    httpsAgent: new (require('https').Agent)({ rejectUnauthorized: false })
  });
const fs = require('fs');
const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');

const getTransferLimit = async () => {
    const requesturl = `${argv.url}?f=json`
    if(argv.debug) console.log(`Fetching maxRecordCountfrom ${requesturl}`);
    const response = await axios.get(requesturl);
    if(argv.debug) console.log(`maxRecordCount: ${response.data.maxRecordCount}`);
    return response.data.maxRecordCount;
}

const getObjectCount = async () => {
    const requesturl = `${argv.url}/query?where=1=1&returnCountOnly=true&f=geojson`
    if(argv.debug) console.log(`Fetching object count from ${requesturl}`);
    const response = await axios.get(requesturl);
    if(argv.debug) console.log(`Object count: ${response.data.properties.count}`);
    return response.data.properties.count;
}

const fetch_data_from_endpoint = async (start, end) => {
    const requesturl = `${argv.url}/query?where=OBJECTID>=${start} AND OBJECTID<${end}&outFields=*&f=geojson`;
    if(argv.debug) console.log(`Fetching data from ${requesturl}`);
    const response = await axios.get(requesturl);
    if(argv.debug) console.log(`Fetched data from ${start} to ${end}`);
    return response.data;
}

const combine_features = (data1, data2) => {
    return [...data1.features, ...data2.features];
}

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
    const rangeSize = await getTransferLimit();
    const count = await getObjectCount();
    let start = 0;
    let end = start + rangeSize + 1;
    if(argv.debug) console.log(`Range size: ${rangeSize}`);
    if(argv.debug) console.log(`Total count: ${count}`);
    if(argv.debug) console.log(`Start: ${start}, End: ${end}`);

    let totalLoaded = 0;

    while (start < count) {
        const data = await fetch_data_from_endpoint(start, end);
        totalLoaded += data.features.length;
        if(argv.debug) console.log(`Loaded ${data.features.length} features. Total loaded: ${totalLoaded} / ${count}`)
        combinedData.features = combine_features(combinedData, data);
        start = end;
        end = start + rangeSize;
    }

    outputFileName = argv.output || 'scrape.json';
    fs.writeFileSync(outputFileName, JSON.stringify(combinedData));
    if(argv.debug) console.log(`Data written to ${outputFileName}`);
}

main();