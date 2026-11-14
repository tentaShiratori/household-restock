(() => {
  const statusEl = document.getElementById("status");
  const errorEl = document.getElementById("error");
  const itemsBody = document.getElementById("items-body");
  const restockBody = document.getElementById("restock-body");
  const reloadBtn = document.getElementById("reload");

  let busy = false;

  function setBusy(next) {
    busy = next;
    reloadBtn.disabled = next;
    document.querySelectorAll("button[data-action]").forEach((btn) => {
      if (next) btn.disabled = true;
    });
  }

  function showError(message) {
    errorEl.hidden = !message;
    errorEl.textContent = message || "";
  }

  function setStatus(message) {
    statusEl.textContent = message || "";
  }

  function isNonNegativeIntString(raw) {
    if (typeof raw !== "string" && typeof raw !== "number") return false;
    const text = String(raw).trim();
    return text !== "" && /^\d+$/.test(text);
  }

  async function api(method, path, body) {
    const options = { method, headers: {} };
    if (body !== undefined) {
      options.headers["content-type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    const res = await fetch(path, options);
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("応答が JSON ではありません");
    }
    const blob = JSON.stringify(data).toLowerCase();
    if (
      blob.includes("tasktoken") ||
      blob.includes("approval_shared_secret") ||
      blob.includes("x-approval-secret") ||
      blob.includes("secret-token-")
    ) {
      throw new Error("応答に秘密らしき値があります（中継不具合）");
    }
    return { res, data };
  }

  function reasonMessage(reason) {
    switch (reason) {
      case "not_awaiting_approval":
      case "already_terminal":
      case "conflict":
        return "承認待ちではないか、競合しています";
      case "token_inactive":
        return "期限切れ、またはトークンが無効です";
      case "not_integer":
      case "negative":
        return "在庫は 0 以上の整数にしてください";
      case "not_found":
        return "対象が見つかりません";
      case "not_shipping_wait":
        return "配送待ちではありません";
      default:
        return reason || "失敗しました";
    }
  }

  function renderItems(items) {
    itemsBody.replaceChildren();
    for (const item of items) {
      const tr = document.createElement("tr");
      tr.dataset.itemId = item.itemId;

      const idTd = document.createElement("td");
      idTd.textContent = item.itemId;

      const thTd = document.createElement("td");
      thTd.textContent = String(item.threshold);

      const stockTd = document.createElement("td");
      const input = document.createElement("input");
      input.type = "number";
      input.min = "0";
      input.step = "1";
      input.value = String(item.stock);
      input.setAttribute("aria-label", `${item.itemId} の在庫`);
      stockTd.appendChild(input);

      const modeTd = document.createElement("td");
      const mode = document.createElement("select");
      mode.setAttribute("aria-label", `${item.itemId} の注文失敗モード`);
      for (const value of ["succeed", "transient_once", "permanent"]) {
        const opt = document.createElement("option");
        opt.value = value;
        opt.textContent = value;
        if ((item.orderFailureMode || "succeed") === value) opt.selected = true;
        mode.appendChild(opt);
      }
      mode.addEventListener("change", () => onSaveMode(item.itemId, mode.value));
      modeTd.appendChild(mode);

      const actionTd = document.createElement("td");
      const save = document.createElement("button");
      save.type = "button";
      save.textContent = "更新";
      save.dataset.action = "save";
      save.addEventListener("click", () => onSaveStock(item.itemId, input));
      actionTd.appendChild(save);

      tr.append(idTd, thTd, stockTd, modeTd, actionTd);
      itemsBody.appendChild(tr);
    }
  }

  function renderRestocks(rows) {
    restockBody.replaceChildren();
    for (const row of rows) {
      const tr = document.createElement("tr");
      tr.dataset.streamEventId = row.streamEventId;

      const itemTd = document.createElement("td");
      itemTd.textContent = row.itemId;
      const eventTd = document.createElement("td");
      eventTd.textContent = row.streamEventId;
      const statusTd = document.createElement("td");
      const label = row.label || row.status;
      statusTd.textContent = label;
      statusTd.dataset.status = row.status;
      statusTd.dataset.label = label;
      statusTd.setAttribute("data-testid", `status-${row.status}`);

      const actionTd = document.createElement("td");
      const awaiting = row.status === "AWAITING_APPROVAL";
      const shipping = row.status === "SHIPPING_WAIT";

      const approve = document.createElement("button");
      approve.type = "button";
      approve.textContent = "承認";
      approve.dataset.action = "approve";
      approve.disabled = !awaiting;
      approve.addEventListener("click", () =>
        onDecision(row.itemId, row.streamEventId, "approve"),
      );

      const reject = document.createElement("button");
      reject.type = "button";
      reject.textContent = "却下";
      reject.dataset.action = "reject";
      reject.disabled = !awaiting;
      reject.addEventListener("click", () =>
        onDecision(row.itemId, row.streamEventId, "reject"),
      );

      const advance = document.createElement("button");
      advance.type = "button";
      advance.textContent = "到着確認へ";
      advance.dataset.action = "advance";
      advance.disabled = !shipping;
      advance.addEventListener("click", () =>
        onAdvance(row.itemId, row.streamEventId),
      );

      actionTd.append(approve, reject, advance);
      tr.append(itemTd, eventTd, statusTd, actionTd);
      restockBody.appendChild(tr);
    }
  }

  function reapplyActionButtons() {
    document.querySelectorAll("#restock-body tr").forEach((tr) => {
      const status = tr.querySelector("[data-status]")?.getAttribute("data-status");
      const awaiting = status === "AWAITING_APPROVAL";
      const shipping = status === "SHIPPING_WAIT";
      tr.querySelectorAll("button[data-action='approve'], button[data-action='reject']").forEach(
        (btn) => {
          btn.disabled = !awaiting;
        },
      );
      tr.querySelectorAll("button[data-action='advance']").forEach((btn) => {
        btn.disabled = !shipping;
      });
    });
  }

  async function reload() {
    showError("");
    setStatus("読込中…");
    setBusy(true);
    try {
      const [itemsRes, restockRes] = await Promise.all([
        api("GET", "/api/items"),
        api("GET", "/api/restock-requests"),
      ]);
      if (!itemsRes.res.ok || !restockRes.res.ok) {
        throw new Error("一覧の取得に失敗しました");
      }
      renderItems(itemsRes.data.items || []);
      renderRestocks(restockRes.data.restockRequests || []);
      setStatus("最新を表示しています");
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
      setStatus("");
    } finally {
      setBusy(false);
      reapplyActionButtons();
    }
  }

  async function onSaveStock(itemId, input) {
    showError("");
    const raw = input.value;
    if (!isNonNegativeIntString(raw)) {
      showError("在庫は 0 以上の整数にしてください");
      return;
    }
    setBusy(true);
    setStatus("送信中…");
    try {
      const { res, data } = await api("PUT", `/api/items/${encodeURIComponent(itemId)}/stock`, {
        stock: Number(raw),
      });
      if (!res.ok) {
        showError(reasonMessage(data.reason));
        setStatus("");
        return;
      }
      setStatus("在庫を更新しました");
      await reload();
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  async function onSaveMode(itemId, mode) {
    showError("");
    setBusy(true);
    setStatus("送信中…");
    try {
      const { res, data } = await api(
        "PUT",
        `/api/items/${encodeURIComponent(itemId)}/order-failure-mode`,
        { mode },
      );
      if (!res.ok) {
        showError(reasonMessage(data.reason));
        setStatus("");
        return;
      }
      setStatus("注文失敗モードを更新しました");
      await reload();
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  async function onDecision(itemId, streamEventId, decision) {
    showError("");
    setBusy(true);
    setStatus("送信中…");
    try {
      const path = `/api/items/${encodeURIComponent(itemId)}/restock-requests/${encodeURIComponent(streamEventId)}/decision`;
      const { res, data } = await api("POST", path, { decision });
      if (!res.ok) {
        showError(reasonMessage(data.reason));
        setStatus("");
        await reload();
        return;
      }
      setStatus(decision === "approve" ? "承認しました" : "却下しました");
      await reload();
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  async function onAdvance(itemId, streamEventId) {
    showError("");
    setBusy(true);
    setStatus("送信中…");
    try {
      const path = `/api/items/${encodeURIComponent(itemId)}/restock-requests/${encodeURIComponent(streamEventId)}/advance-delivery`;
      const { res, data } = await api("POST", path, {});
      if (!res.ok) {
        showError(reasonMessage(data.reason));
        setStatus("");
        await reload();
        return;
      }
      setStatus("到着確認へ進めました");
      await reload();
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err));
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  reloadBtn.addEventListener("click", () => {
    reload();
  });

  reload();
})();
