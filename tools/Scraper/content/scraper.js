(() => {
  if (window.__ARCUS_SCRAPER_LOADED__) return;
  window.__ARCUS_SCRAPER_LOADED__ = true;

  const {
    CONFIG,
    ORDER_FILTERS,
    state,
    syncScraperState,
    getRowSnapshots,
    findRowBySnapshot,
    scrollMainContainerToLoadMore,
    clickLikeUser,
    findOpenDialog,
    isAlertDialog,
    acknowledgeAlertRowsIfPresent,
    closeAlertDialogIfPresent,
    waitForDetailPaneText,
    closeDetailPaneIfPresent,
    waitForSelectorVisible,
    waitForWorkbenchReady,
    sleep,
  } = window.ArcusShared;

  // ── PDPA cleansing ────────────────────────────────────────────────────────
  // Patterns for identifiers that must be redacted under Thai PDPA
  const HN_RE        = /\b\d{2}-\d{2}-\d{6}\b/g;
  const ENC_RE       = /\b[IO]\d{2}-\d{2}-\d{6}\b/g;
  const ORDER_ID_RE  = /\b[OI]\d{10}\b/g;
  // DOB appears after MALE/FEMALE gender word in summary
  const DOB_GENDER_RE = /(MALE|FEMALE)\s+\d{2}-\d{2}-\d{4}/g;
  // Thai patient title + name words (Thai Unicode block ฀-๿)
  const THAI_NAME_RE = /(ด\.ช\.|ด\.ญ\.|นาย|นางสาว|น\.ส\.|นาง|นพ\.|พญ\.|ทพ\.|ทพญ\.|ภก\.|ภญ\.)\s*[฀-๿]+(?:\s+[฀-๿]+)*/g;
  // English patient title + UPPERCASE name (stops before MALE/FEMALE/digits)
  const ENG_NAME_RE  = /(MR\.|MRS\.|MISS|MS\.)\s+[A-Z][A-Z\s\-\.]+?(?=\s+(?:MALE|FEMALE|\d{2}-\d{2}))/g;

  function cleanseSummary(text) {
    if (!text) return text;
    return text
      .replace(THAI_NAME_RE, (_, title) => title + " [NAME]")
      .replace(ENG_NAME_RE,  (_, title) => title + " [NAME]")
      .replace(HN_RE,        "[HN]")
      .replace(ENC_RE,       "[ENC]")
      .replace(ORDER_ID_RE,  "[ORDER]")
      .replace(DOB_GENDER_RE, (_, gender) => gender + " [DOB]");
  }

  function cleanseDetail(text) {
    if (!text) return text;
    // Strip the personal header block ("Details …" up to the first vital sign "WT :").
    // This removes: name, HN, gender word, exact DOB, encounter ID, doctor name, payer info.
    let s = text.replace(/^Details[\s\S]*?(?=WT\s*:)/, "[PATIENT INFO REDACTED] ");
    // Redact any order/encounter IDs remaining in medication / Order Details section
    s = s.replace(ENC_RE, "[ENC]").replace(ORDER_ID_RE, "[ORDER]");
    return s;
  }

  // ── Content tagging ──────────────────────────────────────────────────────
  function tagItem(detail, summary) {
    const tags = [];
    const d = detail || "";
    if (d.length < 50) {
      tags.push("incomplete");
    } else {
      if (/\[PATIENT INFO REDACTED\]/i.test(d)) tags.push("patient_info");
      if (/\bWT\s*:\s*[\d.]+/.test(d)) tags.push("vitals");
      if (/No Known Drug Allerg/i.test(d)) tags.push("nkda");
      else if (/Allergy\b/i.test(d)) tags.push("allergy");
      else if (/⚠️/.test(d)) tags.push("allergy_unknown");
      if (/Primary Diagnosis|Comorbidity/i.test(d)) tags.push("dx");
      const rxCount = (d.match(/\d{10,}/g) || []).length;
      if (rxCount > 0) tags.push("rx:" + rxCount);
    }
    return tags;
  }

  function cleanseItem(item) {
    return {
      ID:      item.ID,
      ROWTYPE: item.ROWTYPE,
      SUMMARY: cleanseSummary(item.SUMMARY),
      DETAIL:  cleanseDetail(item.DETAIL),
      TAGS:    item.TAGS || [],
    };
  }

  // ── Date utilities ────────────────────────────────────────────────────────
  function parseDDMMYYYY(str) {
    const parts = String(str || "").split("-");
    if (parts.length !== 3) return null;
    const [d, m, y] = parts.map(Number);
    if (!d || !m || !y) return null;
    return new Date(y, m - 1, d);
  }

  function dateToDDMMYYYY(d) {
    return [
      String(d.getDate()).padStart(2, "0"),
      String(d.getMonth() + 1).padStart(2, "0"),
      String(d.getFullYear()),
    ].join("-");
  }

  function dateToYYYYMMDD(d) {
    return (
      String(d.getFullYear()) +
      String(d.getMonth() + 1).padStart(2, "0") +
      String(d.getDate()).padStart(2, "0")
    );
  }

  function addDays(d, n) {
    const r = new Date(d);
    r.setDate(r.getDate() + n);
    return r;
  }

  function countDays(startDate, endDate) {
    let count = 0;
    let d = new Date(startDate);
    while (d <= endDate) { count++; d = addDays(d, 1); }
    return count;
  }

  // ── AngularJS-aware date input setter ─────────────────────────────────────
  async function setAngularDateInput(selector, value) {
    const el = document.querySelector(selector);
    if (!el) return false;
    try {
      if (typeof angular !== "undefined") {
        const $el = angular.element(el);
        const ngModel = $el.controller("ngModel");
        const scope = $el.scope();
        if (ngModel && scope) {
          ngModel.$setViewValue(value);
          ngModel.$commitViewValue();
          scope.$apply();
          await sleep(150);
          return true;
        }
      }
    } catch (_) {}
    const nativeSet = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    if (nativeSet) nativeSet.call(el, value); else el.value = value;
    ["input", "change", "blur"].forEach((t) => el.dispatchEvent(new Event(t, { bubbles: true })));
    await sleep(200);
    return true;
  }

  // ── Date range progress storage ───────────────────────────────────────────
  const DATE_RANGE_PROGRESS_KEY = "arcusDateRangeProgress";

  function loadDateRangeProgress() {
    return new Promise((resolve) => {
      try {
        chrome.storage?.local?.get(DATE_RANGE_PROGRESS_KEY, (data) =>
          resolve(data?.[DATE_RANGE_PROGRESS_KEY] || null)
        );
      } catch (_) { resolve(null); }
    });
  }

  function saveDateRangeProgress(startStr, endStr, completedDates) {
    return new Promise((resolve) => {
      try {
        chrome.storage?.local?.set({
          [DATE_RANGE_PROGRESS_KEY]: {
            startDate: startStr,
            endDate: endStr,
            completedDates: Array.from(completedDates),
            updatedAt: Date.now(),
          },
        }, resolve);
      } catch (_) { resolve(); }
    });
  }

  function clearDateRangeProgress() {
    return new Promise((resolve) => {
      try { chrome.storage?.local?.remove(DATE_RANGE_PROGRESS_KEY, resolve); }
      catch (_) { resolve(); }
    });
  }

  // ── Current date context for file naming ──────────────────────────────────
  // Set to "YYYYMMDD" during date-range scraping, null otherwise
  let currentScrapeDate = null;

  // ── Milestone save ────────────────────────────────────────────────────────
  function saveMilestone(data, label) {
    try {
      const toSave = state.scraper.pdpa ? data.map(cleanseItem) : data;
      const suffix = state.scraper.pdpa ? "_pdpa" : "";
      const json = JSON.stringify(toSave, null, 2);
      const blob = new Blob([json], { type: "application/json" });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      const filename = currentScrapeDate
        ? `${currentScrapeDate}_${toSave.length}${suffix}.json`
        : `arcus_scrape_${label}${suffix}_${Date.now()}.json`;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      panel().pushLog("info", `Saved ${toSave.length} rows → ${filename}`, "Scraper • save");
    } catch (err) {
      panel().pushLog("fail", `Save failed: ${err?.message || "unknown"}`, "Scraper • save");
    }
  }

  // Helper: always route panel calls to the scraper-specific panel
  function panel() {
    return window.ArcusScraperPanel || {
      setStatus: () => {},
      pushLog:   () => {},
      renderStats: () => {},
      updateButtonState: () => {},
      setDateProgress: () => {},
    };
  }

  // ── Row highlight ─────────────────────────────────────────────────────────
  function clearHighlight() {
    document.querySelectorAll(".arcus-row-highlight").forEach((el) =>
      el.classList.remove("arcus-row-highlight")
    );
  }

  function highlightRow(el) {
    clearHighlight();
    if (el) el.classList.add("arcus-row-highlight");
  }

  // ── Single-row scrape ─────────────────────────────────────────────────────
  async function scrapeSingleRow(snapshot, index, total) {
    const row = findRowBySnapshot(snapshot);
    if (!row) return { ok: false, reason: "row not found" };

    highlightRow(row);
    await clickLikeUser(row);
    await sleep(CONFIG.settleAfterRowClickMs);

    const meta = `Scraper • row ${index + 1}/${total}`;
    if (findOpenDialog() && isAlertDialog()) {
      await acknowledgeAlertRowsIfPresent(meta);
      await closeAlertDialogIfPresent(meta);
      await sleep(500);
    }

    const paneText = (await waitForDetailPaneText()) || "";
    if (!paneText) panel().pushLog("info", "No detail pane text captured", meta);

    // Do NOT close the pane here — the next row click overwrites it automatically,
    // saving ~650ms per row. The finally block closes it after the last row.
    return {
      ok: true,
      item: { ID: String(index + 1), ROWTYPE: snapshot.rowType, SUMMARY: snapshot.text, DETAIL: paneText, TAGS: tagItem(paneText, snapshot.text) },
    };
  }

  // ── Scrape all visible rows for one date (called by runDateRangeScraper) ───
  async function scrapeDateRows(dateLabel) {
    const dateData = [];
    const seenKeys = new Set();
    let processedIndex = 0;
    let emptyScrollAttempts = 0;

    while (!state.scraperStopRequested) {
      const snapshots = getRowSnapshots();
      const nextSnapshot = snapshots.find((s) => !seenKeys.has(s.key || s.text));

      if (!nextSnapshot) {
        if (emptyScrollAttempts >= CONFIG.maxEmptyScrollAttempts) break;
        emptyScrollAttempts++;
        panel().setStatus(
          `Scraping ${dateLabel}\n${dateData.length} rows captured\nLoading more… ${emptyScrollAttempts}/${CONFIG.maxEmptyScrollAttempts}`
        );
        await scrollMainContainerToLoadMore();
        await sleep(CONFIG.loopDelayMs);
        continue;
      }

      emptyScrollAttempts = 0;
      seenKeys.add(nextSnapshot.key || nextSnapshot.text);
      processedIndex++;

      panel().setStatus(
        `Scraping ${dateLabel}\nRow ${processedIndex}: ${window.ArcusShared.shortText(nextSnapshot.text, 60)}`
      );

      const result = await scrapeSingleRow(nextSnapshot, processedIndex - 1, processedIndex);
      state.stats.processed++;

      if (result.ok) {
        state.stats.success++;
        dateData.push(result.item);
        panel().pushLog("success", `[${nextSnapshot.rowType}] ${window.ArcusShared.shortText(nextSnapshot.text)}`, "Date Scraper");

        const every = CONFIG.milestoneSaveEvery || 50;
        if (dateData.length % every === 0) {
          saveMilestone(dateData, `milestone_${dateData.length}`);
        }
      } else {
        state.stats.fail++;
        panel().pushLog(
          "fail",
          `[${nextSnapshot.rowType}] ${window.ArcusShared.shortText(nextSnapshot.text)}`,
          `Date Scraper • ${result.reason}`
        );
      }

      panel().renderStats();
      syncScraperState();
      await scrollMainContainerToLoadMore();
      await sleep(CONFIG.loopDelayMs);
    }

    // Save final rows for this date (only if not stopped mid-date)
    if (dateData.length > 0 && !state.scraperStopRequested) {
      saveMilestone(dateData, `final_${dateData.length}`);
    }

    return state.scraperStopRequested ? null : dateData;
  }

  // ── Date range scraper ────────────────────────────────────────────────────
  async function runDateRangeScraper({ startDateStr, endDateStr, pdpa = true, resume = false } = {}) {
    if (!window.ArcusShared.isWorkbenchPage()) {
      panel().setStatus("Error: not on workbench page.");
      return;
    }
    if (state.isRunning || state.scraper.state === "running") {
      panel().setStatus("Another task is already running.");
      return;
    }

    const startDate = parseDDMMYYYY(startDateStr);
    const endDate   = parseDDMMYYYY(endDateStr);
    if (!startDate || !endDate || startDate > endDate) {
      panel().setStatus("Invalid date range. Use DD-MM-YYYY format.");
      return;
    }

    const totalDays = countDays(startDate, endDate);
    let completedDates = new Set();

    if (resume) {
      const saved = await loadDateRangeProgress();
      if (saved && saved.startDate === startDateStr && saved.endDate === endDateStr) {
        completedDates = new Set(saved.completedDates || []);
        panel().pushLog("info", `Resuming: ${completedDates.size}/${totalDays} dates already done`, "Date Scraper");
      }
    } else {
      await clearDateRangeProgress();
    }

    state.scraper.pdpa         = pdpa;
    state.scraper.state        = "running";
    state.scraper.data         = [];
    state.scraper.reason       = "";
    state.scraper.progressText = `0/${totalDays} dates`;
    state.scraperStopRequested = false;
    state.isRunning            = true;
    state.stats = { processed: 0, success: 0, fail: 0 };
    syncScraperState();
    panel().renderStats();
    panel().updateButtonState();

    const pdpaNote = pdpa ? " • PDPA ON" : " • PDPA OFF";
    panel().setStatus(`Date range scraper\n${startDateStr} → ${endDateStr}${pdpaNote}`);
    panel().pushLog(
      "info",
      `Start: ${startDateStr} → ${endDateStr}. ${completedDates.size} done, ${totalDays} total.${pdpaNote}`,
      "Date Scraper"
    );

    let currentDate = new Date(startDate);

    try {
      while (currentDate <= endDate) {
        if (state.scraperStopRequested) break;

        const dateInputStr = dateToDDMMYYYY(currentDate);
        const dateFileStr  = dateToYYYYMMDD(currentDate);
        const daysDone     = completedDates.size;

        panel().setDateProgress(`${daysDone}/${totalDays} days  •  Now: ${dateInputStr}`);

        if (completedDates.has(dateFileStr)) {
          currentDate = addDays(currentDate, 1);
          continue;
        }

        panel().setStatus(`Date range scraper\nSetting date: ${dateInputStr}\n${daysDone}/${totalDays} days done`);
        panel().pushLog("info", `Setting date: ${dateInputStr}`, "Date Scraper");

        await setAngularDateInput("#inputElementId4", dateInputStr);
        await setAngularDateInput("#inputElementId5", dateInputStr);
        await sleep(400);

        const searchBtn = await waitForSelectorVisible("#searchdispense", 8000);
        if (!searchBtn) {
          panel().pushLog("fail", `Search button not found for ${dateInputStr}`, "Date Scraper");
          currentDate = addDays(currentDate, 1);
          continue;
        }

        await clickLikeUser(searchBtn);
        await sleep(1500);
        await waitForWorkbenchReady();

        currentScrapeDate = dateFileStr;
        const dateData = await scrapeDateRows(dateInputStr);
        currentScrapeDate = null;

        if (dateData !== null) {
          completedDates.add(dateFileStr);
          await saveDateRangeProgress(startDateStr, endDateStr, completedDates);
          panel().pushLog(
            "info",
            `Date ${dateInputStr}: ${dateData.length} rows saved. ${completedDates.size}/${totalDays} dates done.`,
            "Date Scraper"
          );
        }

        state.scraper.progressText = `${completedDates.size}/${totalDays} dates`;
        syncScraperState();
        currentDate = addDays(currentDate, 1);
        await sleep(CONFIG.loopDelayMs);
      }

      if (state.scraperStopRequested) {
        state.scraper.state  = "stopped";
        state.scraper.reason = "Stopped by user.";
        panel().setStatus(`Date scraper stopped.\n${completedDates.size}/${totalDays} dates done.`);
        panel().pushLog("info", `Stopped by user. ${completedDates.size}/${totalDays} dates done.`, "Date Scraper");
      } else {
        state.scraper.state        = "done";
        state.scraper.progressText = `${completedDates.size}/${totalDays} dates done`;
        panel().setStatus(`Date scraper done.\n${completedDates.size}/${totalDays} dates completed.`);
        panel().pushLog("info", `Completed. ${completedDates.size}/${totalDays} dates done.`, "Date Scraper");
        await clearDateRangeProgress();
      }
    } catch (error) {
      currentScrapeDate = null;
      state.scraper.state  = "error";
      state.scraper.reason = error?.message || "Unknown error";
      syncScraperState();
      panel().setStatus(`Date scraper error:\n${state.scraper.reason}`);
      panel().pushLog("fail", state.scraper.reason, "Date Scraper • error");
    } finally {
      state.isRunning            = false;
      state.scraperStopRequested = false;
      currentScrapeDate          = null;
      clearHighlight();
      syncScraperState();
      panel().updateButtonState();
      panel().setDateProgress(`Done: ${completedDates.size}/${totalDays} days`);
    }
  }

  // ── Main scraper loop ─────────────────────────────────────────────────────
  async function runSharedScraper({ pdpa = true } = {}) {
    if (!window.ArcusShared.isWorkbenchPage()) {
      state.scraper.state  = "error";
      state.scraper.reason = "Scraper works only on the Arcus dispense workbench route.";
      syncScraperState();
      panel().setStatus("Error: wrong page.");
      return;
    }

    if (state.isRunning || state.scraper.state === "running") {
      panel().setStatus("Another task is already running.");
      return;
    }

    let snapshots = getRowSnapshots();
    if (!snapshots.length) {
      state.scraper.state  = "error";
      state.scraper.reason = `No order rows found for ${ORDER_FILTERS[state.settings.rowFilter]}.`;
      syncScraperState();
      panel().setStatus(`No rows found.`);
      panel().pushLog("fail", "No order rows found", "Scraper");
      return;
    }

    // Initialise run
    state.scraper.pdpa         = pdpa;
    state.scraper.state        = "running";
    state.scraper.data         = [];
    state.scraper.reason       = "";
    state.scraper.progressText = `0/${snapshots.length}`;
    state.scraperStopRequested = false;
    state.stats = { processed: 0, success: 0, fail: 0, skipped: 0 };
    syncScraperState();
    panel().renderStats();
    panel().updateButtonState();

    const pdpaNote = pdpa ? " • PDPA cleanse ON" : " • PDPA cleanse OFF";
    panel().setStatus(`Scraper started\nFilter: ${ORDER_FILTERS[state.settings.rowFilter]}${pdpaNote}\n${snapshots.length} rows visible`);
    panel().pushLog("info", `Start. ${snapshots.length} rows visible.${pdpaNote}`, "Scraper");

    const seenKeys = new Set();
    let processedIndex = 0;
    let emptyScrollAttempts = 0;

    try {
      while (!state.scraperStopRequested) {
        snapshots = getRowSnapshots();
        const nextSnapshot = snapshots.find((s) => !seenKeys.has(s.key || s.text));

        if (!nextSnapshot) {
          if (emptyScrollAttempts >= CONFIG.maxEmptyScrollAttempts) break;
          emptyScrollAttempts += 1;
          state.scraper.progressText = `${state.scraper.data.length} captured • loading more ${emptyScrollAttempts}/${CONFIG.maxEmptyScrollAttempts}`;
          syncScraperState();
          panel().setStatus(`Scraper\n${state.scraper.data.length} captured\nLooking for more… ${emptyScrollAttempts}/${CONFIG.maxEmptyScrollAttempts}`);
          await scrollMainContainerToLoadMore();
          await sleep(CONFIG.loopDelayMs);
          continue;
        }

        emptyScrollAttempts = 0;
        seenKeys.add(nextSnapshot.key || nextSnapshot.text);
        processedIndex += 1;
        state.scraper.progressText = `${processedIndex} processed • ${state.scraper.data.length} captured`;
        syncScraperState();
        panel().setStatus(`Scraper\n${ORDER_FILTERS[state.settings.rowFilter]}\nRow ${processedIndex}: ${window.ArcusShared.shortText(nextSnapshot.text, 80)}\nCaptured: ${state.scraper.data.length}`);

        const result = await scrapeSingleRow(nextSnapshot, processedIndex - 1, processedIndex);
        state.stats.processed += 1;

        if (result.ok) {
          state.stats.success += 1;
          state.scraper.data.push(result.item);
          const tagStr = result.item.TAGS.join(" | ") || "—";
          panel().pushLog("success", `[${nextSnapshot.rowType}] ${window.ArcusShared.shortText(nextSnapshot.text)} [${tagStr}]`, "Scraper");
          panel().renderStats();

          const every = CONFIG.milestoneSaveEvery || 50;
          if (state.scraper.data.length % every === 0) {
            saveMilestone(state.scraper.data, `milestone_${state.scraper.data.length}`);
          }
        } else {
          state.stats.fail += 1;
          panel().pushLog("fail", `[${nextSnapshot.rowType}] ${window.ArcusShared.shortText(nextSnapshot.text)}`, `Scraper • ${result.reason}`);
        }

        panel().renderStats();
        syncScraperState();

        // Only scroll when the unseen queue is running low — avoids ~1800ms penalty on every row
        const unseenCount = snapshots.filter((s) => !seenKeys.has(s.key || s.text)).length;
        if (unseenCount < (CONFIG.scrollTriggerThreshold || 3)) {
          await scrollMainContainerToLoadMore();
        }
        await sleep(CONFIG.loopDelayMs);
      }

      // ── Normal end ────────────────────────────────────────────────────────
      if (state.scraperStopRequested) {
        state.scraper.state  = "stopped";
        state.scraper.reason = "Stopped by user.";
        syncScraperState();
        panel().pushLog("info", "Stopped by user", "Scraper");
        panel().setStatus(`Scraper stopped.\n${state.scraper.data.length} captured.`);
      } else {
        state.scraper.state        = "done";
        state.scraper.progressText = `${state.scraper.data.length} captured`;
        syncScraperState();
        panel().setStatus(`Scraper done.\n${state.scraper.data.length} captured.`);
        panel().pushLog("info", `Completed – ${state.scraper.data.length} captured`, "Scraper");
      }

      // Final save (covers both stopped and done)
      if (state.scraper.data.length > 0) {
        const finalLabel = state.scraperStopRequested ? "stopped" : "final";
        saveMilestone(state.scraper.data, `${finalLabel}_${state.scraper.data.length}`);
      }

    } catch (error) {
      // ── Error: save immediately before anything else ───────────────────────
      if (state.scraper.data.length > 0) {
        saveMilestone(state.scraper.data, `error_${state.scraper.data.length}`);
      }
      state.scraper.state  = "error";
      state.scraper.reason = error?.message || "Unknown error";
      syncScraperState();
      panel().setStatus(`Scraper error:\n${state.scraper.reason}`);
      panel().pushLog("fail", state.scraper.reason, "Scraper • error");

    } finally {
      state.scraperStopRequested = false;
      clearHighlight();
      await closeDetailPaneIfPresent();   // close pane once at the very end
      panel().updateButtonState();
    }
  }

  window.ArcusScraper = { runSharedScraper, runDateRangeScraper, saveMilestone, cleanseItem };
})();
