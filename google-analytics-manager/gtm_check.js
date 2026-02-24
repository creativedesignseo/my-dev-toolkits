const { AnalyticsAdminServiceClient } = require('@google-analytics/admin');
const fs = require('fs');
process.env.GOOGLE_APPLICATION_CREDENTIALS = 'C:/Users/jonat/workspace/toolkits/google-analytics-manager/credentials.json';
const client = new AnalyticsAdminServiceClient();
async function run() {
    let output = '';
    try {
        const [streams] = await client.listDataStreams({ parent: 'properties/525446591' });
        output += `STREAMS_COUNT: ${streams.length}\n`;
        streams.forEach(s => {
            output += `DISPLAY_NAME: ${s.displayName}\n`;
            if (s.webStreamData) {
                output += `MEASUREMENT_ID: ${s.webStreamData.measurementId}\n`;
            }
        });
    } catch (e) {
        output += `ERROR: ${e.message}\n`;
    }
    fs.writeFileSync('gtm_check_res.txt', output);
}
run();
