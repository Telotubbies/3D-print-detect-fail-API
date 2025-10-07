// frontend/static/assets/app.js
document.addEventListener("DOMContentLoaded", () => {
  const uploadBtn     = document.getElementById("uploadBtn");
  const fileInput     = document.getElementById("fileInput");
  const genKeyBtn     = document.getElementById("genKeyBtn");
  const apiKeyInput   = document.getElementById("apiKeyInput");
  const clearKeyBtn   = document.getElementById("clearKeyBtn");
  const cardContainer = document.getElementById("cardContainer");
  const replaceUrlEl  = document.getElementById("replaceUrl");   // <input readonly> (optional)
  const copyCurlBtn   = document.getElementById("copyCurlBtn");  // <button> (optional)

  if (!uploadBtn || !fileInput || !genKeyBtn || !apiKeyInput || !clearKeyBtn || !cardContainer) {
    console.error("Missing DOM elements. Check IDs in index.html");
    return;
  }

  // ------------------------
  // Helpers
  // ------------------------
  let isUploading = false; // กันดับเบิลคลิก
  const hasKey = () => !!apiKeyInput.value?.trim();

  // กัน cache แบบไม่ทำให้เกิด `...?v=abc?v=123`
  function withCacheBuster(url) {
    return url.includes("?") ? `${url}&_=${Date.now()}` : `${url}?_=${Date.now()}`;
  }

  function setKey(apiKey, cardId) {
    apiKeyInput.value = apiKey || "";
    if (cardId) apiKeyInput.dataset.cardId = cardId; else delete apiKeyInput.dataset.cardId;
    apiKeyInput.readOnly = true;
    apiKeyInput.title = "Click to copy";

    // อัปเดต Replace URL (โชว์เมื่อมี cardId)
    if (replaceUrlEl) {
      if (cardId) {
        const url = `${location.origin}/cards/${encodeURIComponent(cardId)}/replace`;
        replaceUrlEl.value = url;
        replaceUrlEl.parentElement?.classList.remove("d-none");
      } else {
        replaceUrlEl.value = "";
        replaceUrlEl.parentElement?.classList.add("d-none");
      }
    }

    // เปิด/ปิดปุ่ม Copy cURL ตามการมีคีย์
    if (copyCurlBtn) copyCurlBtn.disabled = !apiKey;
  }

  function clearKey() {
    apiKeyInput.value = "";
    delete apiKeyInput.dataset.cardId;
    apiKeyInput.readOnly = false;
    apiKeyInput.title = "";
    if (replaceUrlEl) {
      replaceUrlEl.value = "";
      replaceUrlEl.parentElement?.classList.add("d-none");
    }
    if (copyCurlBtn) copyCurlBtn.disabled = true;
  }

  // copy key on click
  apiKeyInput.addEventListener("click", async () => {
    if (!apiKeyInput.value) return;
    try { await navigator.clipboard.writeText(apiKeyInput.value); apiKeyInput.select(); } catch {}
  });

  // copy URL on click (optional field)
  if (replaceUrlEl) {
    replaceUrlEl.addEventListener("click", async () => {
      if (!replaceUrlEl.value) return;
      try { await navigator.clipboard.writeText(replaceUrlEl.value); replaceUrlEl.select(); } catch {}
    });
  }

  // ---------- Build cURL ----------
function buildCurlCommand(apiKey, cardId) {
  const fileArg = '"/path/to/file.jpg"';
  const base = location.origin;

  if (cardId) {
    return `curl -X POST "${base}/cards/${encodeURIComponent(cardId)}/replace" -H "x-api-key: ${apiKey}" -F "image=@${fileArg}"`;
  }

  return `curl -X POST "${base}/cards/replace" -H "x-api-key: ${apiKey}" -F "image=@${fileArg}"`;
}


  // ปุ่ม Copy cURL อีกครั้ง (optional)
  if (copyCurlBtn) {
    copyCurlBtn.addEventListener("click", async () => {
      const apiKey = apiKeyInput.value.trim();
      if (!apiKey) return alert("ยังไม่มี API key");
      const cardId = apiKeyInput.dataset.cardId || "";
      const cmd = buildCurlCommand(apiKey, cardId);
      try { await navigator.clipboard.writeText(cmd); alert("✅ คัดลอก cURL แล้ว\n\n" + cmd); }
      catch { alert("คัดลอกไม่สำเร็จ"); }
    });
  }

  // ------------------------
  // Generate key (one-shot)
  // ------------------------
  genKeyBtn.addEventListener("click", async () => {
    genKeyBtn.disabled = true; genKeyBtn.textContent = "Generating...";
    try {
      const res = await fetch("/cards/genkey", {
        method: "POST",
        credentials: "include" // ส่ง cookie session ให้แน่ใจว่าใช้ sid เดิม
      });
      if (!res.ok) throw new Error(`Gen key failed (${res.status})`);
      const data = await res.json(); // {card_id, api_key, expires_at}
      setKey(data.api_key, data.card_id);

      // Auto-copy cURL พร้อม card_id + api_key
      const cmd = buildCurlCommand(data.api_key, data.card_id);
      await navigator.clipboard.writeText(cmd);
      alert("✅ คัดลอกคำสั่ง cURL แล้ว\n\n" + cmd);
    } catch (e) {
      alert(e.message || "Generate key failed"); console.error(e);
    } finally {
      genKeyBtn.disabled = false; genKeyBtn.textContent = "Generate Key";
    }
  });

  // manual clear
  clearKeyBtn.addEventListener("click", clearKey);

  // ------------------------
  // Upload flow
  // ------------------------
  uploadBtn.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;
    if (isUploading) return;
    isUploading = true;

    if (file.size > 20 * 1024 * 1024) {
      alert("File too large! Max 20MB.");
      isUploading = false; fileInput.value = ""; return;
    }

    // show loading
    const loading = document.createElement("div");
    loading.className = "col-md-6 mb-4";
    loading.innerHTML = `<div class="card"><div class="card-body">Uploading & processing...</div></div>`;
    cardContainer.prepend(loading);

    try {
      const fd = new FormData();
      fd.append("image", file);

      let usedReplace = false;
      let res, data;

      // 1) ถ้ามีคีย์ → แทนที่ (ถ้ามี card_id จะใช้ path param)
      if (hasKey()) {
        usedReplace = true;
        const apiKey = apiKeyInput.value.trim();
        const cardId = apiKeyInput.dataset.cardId;

        if (cardId) {
          res = await fetch(`/cards/${encodeURIComponent(cardId)}/replace`, {
            method: "POST",
            headers: { "x-api-key": apiKey },
            body: fd,
            credentials: "include" // สำคัญ: คง sid เดิม
          });
        } else {
          // fallback: ให้ backend map จากคีย์
          res = await fetch(`/cards/replace`, {
            method: "POST",
            headers: { "x-api-key": apiKey },
            body: fd,
            credentials: "include" // สำคัญ: คง sid เดิม
          });
        }

        // ถ้าคีย์ไม่เวิร์ก → ล้างคีย์ + fallback ไปสร้างการ์ดใหม่
        if (res.status === 401) {
          clearKey();
          res = await fetch(`/cards`, { method: "POST", body: fd, credentials: "include" });
          usedReplace = false; // กลายเป็น create
        }
      } else {
        // 2) ไม่มีคีย์ → สร้างใหม่
        res = await fetch(`/cards`, { method: "POST", body: fd, credentials: "include" });
      }

      if (!res.ok) throw new Error(`Upload failed (${res.status})`);
      data = await res.json();

      // แทนที่ loading ด้วยผลลัพธ์
      loading.remove();

      // แสดงผล
      if (usedReplace) {
        // อัปเดตการ์ดเดิมด้วย card_id ที่แบ็กเอนด์ส่งกลับ
        const cardId = data.card_id;
        const existing = document.querySelector(`[data-card-id="${cardId}"]`);
        if (existing) {
          const img = existing.querySelector("img");
          if (img) img.src = withCacheBuster(data.detected_image_url);
          const title = existing.querySelector(".card-title");
          if (title) title.textContent = data.status;
          existing.classList.add("selected");
        } else {
          console.warn("No existing card in DOM; creating a new one.");
          addCard(data);
        }
        // one-shot: ใช้เสร็จล้างคีย์อัตโนมัติ
        clearKey();
      } else {
        // create ปกติ → เพิ่มการ์ดใหม่
        addCard(data);
      }

    } catch (e) {
      console.error(e);
      loading.innerHTML = `
        <div class="card border-danger">
          <div class="card-body text-danger">Error: ${e.message}</div>
        </div>`;
      setTimeout(() => loading.remove(), 4000);
    } finally {
      if (loading.isConnected) loading.remove();
      isUploading = false;
      fileInput.value = ""; // อนุญาตอัปโหลดไฟล์เดิมซ้ำได้
    }
  });
async function ensureImageOk(url) {
  try {
    const resp = await fetch(url, { method: "GET", cache: "no-store" });
    console.log("[ensureImageOk]", url, resp.status);
    return resp.ok;
  } catch (e) {
    console.error("[ensureImageOk] error", url, e);
    return false;
  }
}

  // ------------------------
  // render helper
  // ------------------------
  function addCard(result) {
    const col = document.createElement("div");
    col.className = "col-md-6 mb-4";

    const imgUrl = withCacheBuster(result.detected_image_url);

    col.innerHTML = `
      <div class="card" data-card-id="${result.card_id}">
        <img src="${imgUrl}" class="card-img-top" />
        <div class="card-body">
          <div class="d-flex align-items-baseline gap-2">
            <span class="fw-semibold">status :</span>
            <h5 class="card-title mb-0">${result.status}</h5>
          </div>
        </div>
      </div>
    `;
    cardContainer.prepend(col);
  }
});
