export async function getRepos() {
  const res = await fetch("http://localhost:8000/api/repos/list", { credentials: "include" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    const message = text || res.statusText || "Failed to fetch repos";
    // Throw structured error so caller can respond to status (e.g., 401 -> redirect to login)
    throw { status: res.status, message };
  }
  return res.json();
}

export async function getFiles(owner, repo, path = "") {
  const url = `http://localhost:8000/api/repos/${owner}/${repo}/contents?path=${path}`;
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    const message = text || res.statusText || "Failed to fetch files";
    throw { status: res.status, message };
  }
  return res.json();
}

export async function startReview(selectedFiles) {
  const res = await fetch("http://localhost:8000/api/reviews/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ files: selectedFiles })
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    const message = text || res.statusText || "Review failed";
    throw { status: res.status, message };
  }
  return res.json();
}

export async function publishReviewToPR(owner, repo, pullNumber, suggestions) {
  const res = await fetch("http://localhost:8000/api/reviews/publish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      owner,
      repo,
      pull_number: pullNumber,
      suggestions,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    const message = text || res.statusText || "Failed to publish review";
    throw { status: res.status, message };
  }
  return res.json();
}
