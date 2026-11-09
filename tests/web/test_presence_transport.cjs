const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { runInNewContext } = require("node:vm");
const { test } = require("node:test");

const source = readFileSync("easyread/web/js/common/presence.js", "utf8");

function connection(protocol) {
  const opened = [];
  class WebSocket {
    constructor(url) { opened.push(url); }
  }
  runInNewContext(source, {
    location: { protocol, host: "reader.example" },
    WebSocket,
    setTimeout: () => {},
  });
  return opened;
}

test("presence uses ws for HTTP and wss for HTTPS", () => {
  assert.deepEqual(connection("http:"), ["ws://reader.example/api/presence"]);
  assert.deepEqual(connection("https:"), ["wss://reader.example/api/presence"]);
});

test("presence stays disabled for offline file exports", () => {
  assert.deepEqual(connection("file:"), []);
});
