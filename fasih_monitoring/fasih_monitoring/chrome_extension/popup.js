
const btn = document.getElementById("collect");
const msg = document.getElementById("msg");

btn.addEventListener("click", async () => {
  msg.textContent = "Membaca tabel pada tab aktif...";
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    if (!tab || !tab.id || !/^https:\/\/fasih-sm\.bps\.go\.id\//i.test(tab.url || "")) {
      throw new Error("Buka halaman FASIH-SM terlebih dahulu.");
    }

    const results = await chrome.scripting.executeScript({
      target: {tabId: tab.id},
      func: () => {
        const clean = s => (s || "").replace(/\s+/g, " ").trim();
        const tables = [...document.querySelectorAll("table")];
        let extracted = [];

        for (const table of tables) {
          const headers = [...table.querySelectorAll("thead tr:last-child th")].map(x => clean(x.innerText));
          const rows = [...table.querySelectorAll("tbody tr")].map(tr =>
            [...tr.querySelectorAll("td")].map(td => clean(td.innerText))
          ).filter(r => r.some(Boolean));
          if (headers.length && rows.length) {
            extracted.push({headers, rows, source: "html-table"});
          }
        }

        if (!extracted.length) {
          const grids = [...document.querySelectorAll('[role="grid"], [role="table"]')];
          for (const grid of grids) {
            const headers = [...grid.querySelectorAll('[role="columnheader"]')].map(x => clean(x.innerText));
            const rows = [...grid.querySelectorAll('[role="row"]')].map(row =>
              [...row.querySelectorAll('[role="gridcell"], [role="cell"]')].map(x => clean(x.innerText))
            ).filter(r => r.length && r.some(Boolean));
            if (headers.length && rows.length) extracted.push({headers, rows, source: "aria-grid"});
          }
        }

        const bodyText = document.body.innerText || "";
        const openMatch = bodyText.match(/OPEN\s+(\d+)/i) || bodyText.match(/(\d+)\s+OPEN/i);
        const title = document.title || "";
        return {
          url: location.href,
          title,
          captured_at: new Date().toISOString(),
          open_count_on_page: openMatch ? Number(openMatch[1]) : null,
          page_text_has_open_filter: /\bOPEN\b/i.test(bodyText),
          tables: extracted
        };
      }
    });

    const data = results?.[0]?.result;
    if (!data || !data.tables?.length) {
      throw new Error("Tabel tidak ditemukan. Pastikan halaman Data dan tabel OPEN sudah tampil. Jika FASIH memakai grid khusus, diperlukan penyesuaian selector berdasarkan inspeksi halaman.");
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    await chrome.downloads.download({
      url,
      filename: `fasih_open_page_${stamp}.json`,
      saveAs: true
    });
    msg.textContent = `Berhasil membaca ${data.tables.reduce((n,t)=>n+t.rows.length,0)} baris dari ${data.tables.length} tabel. File JSON diunduh. Untuk halaman berikutnya, pindah halaman di FASIH-SM lalu klik lagi.`;
  } catch (e) {
    msg.textContent = "Gagal: " + (e?.message || String(e));
  }
});
