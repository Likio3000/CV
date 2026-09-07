import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  normalizeEntries,
  selectEntries,
  safeRepositoryUrl,
  dateOnly,
  formatDate,
} from "../work-log-model.mjs";

const repoUrl = "https://github.com/Likio3000/Alpha_Evolve";
const entry = {
  date: "2026-03-08",
  repoUrl,
  title: "A change",
  commitHash: "f49ec50",
};

test("real archive preserves every selected entry and paginates without mutation", () => {
  const context = { window: {} };
  vm.runInNewContext(
    fs.readFileSync(new URL("../work-log-data.js", import.meta.url), "utf8"),
    context,
  );
  const source = context.window.WORK_LOG_DATA.entries;
  const before = JSON.stringify(source);
  const entries = normalizeEntries(source);
  assert.equal(entries.length, source.length);
  assert.equal(selectEntries(entries).visible.length, 12);
  assert.equal(selectEntries(entries).hasMore, true);
  assert.equal(selectEntries(entries, "all", 100).hasMore, false);
  const typing = selectEntries(entries, "typing-quest", 100);
  assert.ok(typing.total > 0);
  assert.ok(typing.visible.every((item) => item.slug === "typing-quest"));
  assert.equal(JSON.stringify(source), before);
  assert.ok(entries.every((item, i) => !i || entries[i - 1].date >= item.date));
});

test("repository links are limited to the publication selection", () => {
  const allowed = JSON.parse(
    fs.readFileSync(new URL("../public-projects.json", import.meta.url)),
  ).repositories;
  for (const url of allowed) assert.equal(safeRepositoryUrl(url), url);
  for (const url of [
    "javascript:alert(1)",
    repoUrl + "/commit/f49ec50",
    repoUrl + "?x=1",
    "https://github.com/Likio3000/private-project",
    "https://github.com.evil.test/Likio3000/Alpha_Evolve",
  ])
    assert.equal(safeRepositoryUrl(url), null);
  assert.equal(
    normalizeEntries([
      { ...entry, repoUrl: "https://github.com/Likio3000/private-project" },
    ]).length,
    0,
  );
});

test("invalid dates are omitted and source calendar dates survive timezone offsets", () => {
  for (const value of ["2026-02-30", "2026-13-01", "invalid", null])
    assert.equal(dateOnly(value), null);
  assert.equal(dateOnly("2026-03-08T23:30:00-11:00"), "2026-03-08");
  assert.equal(formatDate("2026-03-08T23:30:00-11:00"), "8 Mar 2026");
  assert.deepEqual(
    normalizeEntries([{ ...entry, date: "2026-02-30" }, null]),
    [],
  );
});

test("commit links and line counts degrade safely when data is malformed", () => {
  assert.equal(normalizeEntries([entry])[0].link, repoUrl + "/commit/f49ec50");
  const malformed = normalizeEntries([
    {
      ...entry,
      commitHash: "../settings",
      lineStats: { added: -1, deleted: "3" },
      workedOn: [null, "Verified inputs"],
    },
  ])[0];
  assert.equal(malformed.link, repoUrl);
  assert.equal(malformed.lineStats, null);
  assert.deepEqual(malformed.workedOn, ["Verified inputs"]);
  assert.deepEqual(selectEntries([], "all"), {
    visible: [],
    total: 0,
    hasMore: false,
  });
});
