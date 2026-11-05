const communicationServerUrl = 'http://127.0.0.1:8765';
const communicationServerWsUrl = communicationServerUrl.replace(/^http/, 'ws');

export const environment = {
  communicationServerUrl,
  // Python backend market-data endpoint; the backend must implement this contract.
  marketDataWsUrl: `${communicationServerWsUrl}/ws`,
  // POST { "action": "start" | "stop" } to control replay.
  replayControlUrl: `${communicationServerUrl}/api/replay`,
  // GET to download the generated reports ZIP.
  reportExportUrl: `${communicationServerUrl}/api/export`,
};
