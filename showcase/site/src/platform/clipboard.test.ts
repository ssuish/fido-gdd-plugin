import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { copyText, type ClipboardWriter } from "./clipboard.ts";

describe("copyText", () => {
  it("reports unavailable when the Clipboard API is missing", async () => {
    assert.equal(await copyText("command", undefined), "unavailable");
  });

  it("reports success after the writer resolves", async () => {
    let copied = "";
    const clipboard: ClipboardWriter = {
      writeText: async (text) => {
        copied = text;
      },
    };

    assert.equal(await copyText("command", clipboard), "ok");
    assert.equal(copied, "command");
  });

  it("reports an error when the writer rejects", async () => {
    const clipboard: ClipboardWriter = {
      writeText: async () => {
        throw new Error("permission denied");
      },
    };

    assert.equal(await copyText("command", clipboard), "error");
  });
});
