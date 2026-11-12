
const API = "http://127.0.0.1:8000";

let candidates = [];
let internships = [];

const el = (id) => document.getElementById(id);

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[char]));

async function getJSON(path) {
  const response = await fetch(`${API}${path}`);

  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
  }

  return response.json();
}

function showToast(message) {
  const toast = el("toast");

  toast.textContent = message;
  toast.style.display = "block";

  clearTimeout(showToast.timer);

  showToast.timer = setTimeout(() => {
    toast.style.display = "none";
  }, 5000);
}

function showError(message) {
  el("match-rows").innerHTML =
    `<tr><td colspan="5">${escapeHtml(message)}</td></tr>`;

  el("candidate-profile").innerHTML =
    `<p class="muted">${escapeHtml(message)}</p>`;
}


// ===============================
// INITIALIZE DASHBOARD
// ===============================

async function init() {
  try {
    const [summary, candidateData, internshipData] =
      await Promise.all([
        getJSON("/api/admin/summary"),
        getJSON("/api/candidates"),
        getJSON("/api/internships")
      ]);

    candidates = candidateData;
    internships = internshipData;

    el("candidate-count").textContent =
      summary.candidate_count;

    el("internship-count").textContent =
      summary.internship_count;

    el("seat-count").textContent =
      summary.total_seats;

    el("eligible-count").textContent =
      summary.eligible_pairs;

    el("candidate-select").innerHTML = candidates.map(c =>
      `<option value="${c.id}">${escapeHtml(c.name)}</option>`
    ).join("");

    // Avoid duplicate event listeners after refreshing.
    el("candidate-select").onchange = (event) => {
      loadMatches(Number(event.target.value));
    };

    renderInternships();
    renderCandidates();

    if (candidates.length > 0) {
      await loadMatches(candidates[0].id);
    } else {
      el("candidate-select").innerHTML =
        '<option value="">No candidates available</option>';

      el("candidate-profile").innerHTML =
        "<p>Add a candidate to see recommendations.</p>";

      el("match-rows").innerHTML =
        '<tr><td colspan="5">No candidates available.</td></tr>';
    }

  } catch (error) {
    showError(
      `${error.message}. Check whether the backend is running.`
    );
  }
}


// ===============================
// AI MATCHING
// ===============================

async function loadMatches(candidateId) {
  try {
    const candidate = candidates.find(
      c => c.id === candidateId
    );

    if (!candidate) return;

    const matches = await getJSON(
      `/api/candidates/${candidateId}/matches`
    );

    el("candidate-profile").innerHTML = `
      <div class="candidate-avatar">
        ${escapeHtml(
          candidate.name.split(" ")
            .map(n => n[0]).join("").slice(0, 2)
        )}
      </div>

      <div class="candidate-info">
        <strong>${escapeHtml(candidate.name)}</strong>

        <p>
          ${escapeHtml(candidate.qualification)}
          · ${escapeHtml(candidate.preferred_sector)}
          · Prefers ${escapeHtml(candidate.preferred_location)}
        </p>

        <p>
          ${candidate.skills.map(skill =>
            `<span class="skill-tag">${escapeHtml(skill)}</span>`
          ).join(" ")}
        </p>
      </div>

      <span class="cgpa">
        CGPA ${Number(candidate.cgpa).toFixed(1)}
      </span>
    `;

    el("match-rows").innerHTML = matches.length
      ? matches.map(match => `
        <tr>
          <td>
            <div class="role-cell">
              <div class="company-icon">
                ${escapeHtml(match.company.slice(0, 1))}
              </div>

              <div>
                <strong>${escapeHtml(match.role)}</strong>
                <small>
                  ${escapeHtml(match.company)}
                  · ${escapeHtml(match.location)}
                </small>
              </div>
            </div>
          </td>

          <td>
            ${(match.matched_skills.length
              ? match.matched_skills
              : ["No exact skill overlap"]
            ).slice(0, 4).map(skill =>
              `<span class="skill-tag">${escapeHtml(skill)}</span>`
            ).join("")}
          </td>

          <td>
            <div class="score-wrap">
              <div class="score-track">
                <div class="score-fill"
                     style="width:${match.score}%"></div>
              </div>
              <span class="score-num">${match.score}%</span>
            </div>
          </td>

          <td>
            <span class="pill ${match.eligible
              ? "eligible"
              : "ineligible"}">
              ${match.eligible ? "Eligible" : "Not eligible"}
            </span>
          </td>

          <td>
            <button class="detail-btn"
                    data-match="${match.internship_id}">
              Why this match?
            </button>
          </td>
        </tr>
      `).join("")
      : '<tr><td colspan="5">No matching internships found.</td></tr>';

    document.querySelectorAll("[data-match]").forEach(button => {
      button.onclick = () => {
        const match = matches.find(
          item => item.internship_id ===
            Number(button.dataset.match)
        );

        if (match) {
          showToast(
            `${match.role}: ${match.reasons.join(" ")}`
          );
        }
      };
    });

  } catch (error) {
    showError(error.message);
  }
}


// ===============================
// CANDIDATE MANAGEMENT
// ===============================

function renderCandidates() {
  const tbody = el("candidate-record-rows");
  if (!tbody) return;

  const isAdmin = Boolean(sessionStorage.getItem("admin_token"));

  tbody.innerHTML = candidates.length
    ? candidates.map(candidate => `
      <tr>
        <td>${escapeHtml(candidate.name)}</td>
        <td>${escapeHtml(candidate.qualification)}</td>
        <td>${candidate.skills.map(escapeHtml).join(", ")}</td>
        <td>${Number(candidate.cgpa).toFixed(2)}</td>
        <td>${escapeHtml(candidate.preferred_location)}</td>
        <td>
          <button type="button" class="detail-btn"
            data-edit-candidate="${candidate.id}">Edit</button>

          <button type="button" class="detail-btn"
            data-delete-candidate="${candidate.id}"
            ${!isAdmin ? "disabled title='Admin login required'" : ""}>
            Delete
          </button>
        </td>
      </tr>
    `).join("")
    : '<tr><td colspan="6">No candidates added yet.</td></tr>';

  tbody.querySelectorAll("[data-edit-candidate]").forEach(button => {
    button.onclick = () => {
      const candidate = candidates.find(
        c => c.id === Number(button.dataset.editCandidate)
      );
      if (candidate) startCandidateEdit(candidate);
    };
  });

  tbody.querySelectorAll("[data-delete-candidate]").forEach(button => {
    button.onclick = () => deleteRecord(
      `/api/candidates/${button.dataset.deleteCandidate}`,
      "candidate"
    );
  });
}


// Load selected candidate into the form.
function startCandidateEdit(candidate) {
  const form = el("candidate-form");

  form.elements["candidate_id"].value = candidate.id;
  form.elements["name"].value = candidate.name;
  form.elements["qualification"].value =
    candidate.qualification;

  form.elements["skills"].value =
    candidate.skills.join(", ");

  form.elements["preferred_sector"].value =
    candidate.preferred_sector;

  form.elements["preferred_location"].value =
    candidate.preferred_location;

  form.elements["cgpa"].value = candidate.cgpa;

  form.elements["experience_months"].value =
    candidate.experience_months;

  el("candidate-form-title").textContent =
    `Edit Candidate #${candidate.id}`;

  form.querySelector('button[type="submit"]').textContent =
    "Save Changes";

  form.scrollIntoView({
    behavior: "smooth",
    block: "center"
  });

  showToast(`Editing ${candidate.name}`);
}


// Reset form to Add Candidate mode.
function resetCandidateForm() {
  const form = el("candidate-form");

  form.reset();

  form.elements["candidate_id"].value = "";

  el("candidate-form-title").textContent =
    "Add Candidate";

  form.querySelector('button[type="submit"]').textContent =
    "Save Candidate";
}


// ===============================
// INTERNSHIP LIST
// ===============================

function renderInternships() {
  const isAdmin = Boolean(sessionStorage.getItem("admin_token"));

  el("internship-list").innerHTML = internships.map(item => `
    <article class="internship-card">
      <div class="internship-top">
        <div>
          <h3>${escapeHtml(item.role)}</h3>
          <span class="company">${escapeHtml(item.company)}</span>
        </div>
        <span class="pill">${item.seats} seats</span>
      </div>

      <div class="internship-meta">
        <span class="meta-chip">${escapeHtml(item.sector)}</span>
        <span class="meta-chip">${escapeHtml(item.location)}</span>
        <span class="meta-chip">
          Min CGPA ${Number(item.min_cgpa).toFixed(1)}
        </span>
      </div>

      <p class="skills">
        Required: ${item.required_skills.map(escapeHtml).join(" · ")}
      </p>

      <button type="button" class="detail-btn"
        data-delete-internship="${item.id}"
        ${!isAdmin ? "disabled title='Admin login required'" : ""}>
        Delete Internship
      </button>
    </article>
  `).join("");

  document.querySelectorAll("[data-delete-internship]").forEach(button => {
    button.onclick = () => deleteRecord(
      `/api/internships/${button.dataset.deleteInternship}`,
      "internship"
    );
  });
}


// ===============================
// ADD / UPDATE CANDIDATE
// AND ADD INTERNSHIP
// ===============================

async function submitRecord(
  event,
  endpoint,
  form,
  isCandidate
) {
  event.preventDefault();

  const button = form.querySelector(
    'button[type="submit"]'
  );

  button.disabled = true;
  button.textContent = "Saving...";

  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  const candidateId = isCandidate
    ? data.candidate_id
    : "";

  delete data.candidate_id;

  if (isCandidate) {
    data.skills = data.skills
      .split(",")
      .map(s => s.trim())
      .filter(Boolean);

    data.cgpa = Number(data.cgpa);

    data.experience_months =
      Number(data.experience_months);

  } else {
    data.required_skills = data.required_skills
      .split(",")
      .map(s => s.trim())
      .filter(Boolean);

    data.min_cgpa = Number(data.min_cgpa);
    data.seats = Number(data.seats);
  }

  try {
    const isEditingCandidate =
      isCandidate && Boolean(candidateId);

    const requestUrl = isEditingCandidate
      ? `${API}/api/candidates/${candidateId}`
      : `${API}${endpoint}`;

    const response = await fetch(requestUrl, {
      method: isEditingCandidate ? "PUT" : "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(
        result.detail
          ? JSON.stringify(result.detail)
          : "Could not save record"
      );
    }

    if (isCandidate) {
      showToast(
        isEditingCandidate
          ? "Candidate updated successfully!"
          : "Candidate saved successfully!"
      );

      resetCandidateForm();

    } else {
      showToast("Internship saved successfully!");
      form.reset();
    }

    await init();

  } catch (error) {
    showToast(`Error: ${error.message}`);

  } finally {
    button.disabled = false;

    if (isCandidate) {
      button.textContent =
        form.elements["candidate_id"].value
          ? "Save Changes"
          : "Save Candidate";
    } else {
      button.textContent = "Save Internship";
    }
  }
}


// Form event listeners.
el("candidate-form").addEventListener(
  "submit",
  event => submitRecord(
    event,
    "/api/candidates",
    el("candidate-form"),
    true
  )
);

el("internship-form").addEventListener(
  "submit",
  event => submitRecord(
    event,
    "/api/internships",
    el("internship-form"),
    false
  )
);


// ===============================
// AUTOMATIC ALLOCATION
// ===============================

el("run-allocation").addEventListener(
  "click",
  async () => {
    const button = el("run-allocation");
    const output = el("allocation-results");

    button.disabled = true;
    button.textContent = "Allocating...";

    try {
      const response = await fetch(
        `${API}/api/allocate`,
        { method: "POST" }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(JSON.stringify(data));
      }

      output.innerHTML = `
        <h3>Allocation Results</h3>

        <p>Total candidates: ${data.total_candidates}</p>
        <p>Allocated: ${data.allocated_candidates}</p>
        <p>Unallocated: ${data.unallocated_candidates}</p>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Internship</th>
                <th>Company</th>
                <th>Score</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              ${data.allocations.map(item => `
                <tr>
                  <td>${escapeHtml(item.candidate_name)}</td>
                  <td>${escapeHtml(item.role)}</td>
                  <td>${escapeHtml(item.company)}</td>
                  <td>${item.score}%</td>
                  <td>${escapeHtml(item.status)}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>

        <p class="muted">${escapeHtml(data.note)}</p>
      `;

      await loadAllocationHistory();

      showToast("Automatic allocation completed!");

    } catch (error) {
      output.textContent =
        `Allocation failed: ${error.message}`;

    } finally {
      button.disabled = false;
      button.textContent = "Run Automatic Allocation";
    }
  }
);


// ===============================
// SAVED ALLOCATION HISTORY
// ===============================

async function loadAllocationHistory() {
  const tbody = el("history-rows");

  tbody.innerHTML =
    '<tr><td colspan="5">Loading...</td></tr>';

  try {
    const rows = await getJSON("/api/allocations");

    tbody.innerHTML = rows.length
      ? rows.map(item => `
        <tr>
          <td>${escapeHtml(item.candidate_name)}</td>
          <td>${escapeHtml(item.role)}</td>
          <td>${escapeHtml(item.company)}</td>
          <td>${Number(item.score).toFixed(2)}%</td>
          <td>${escapeHtml(item.status)}</td>
        </tr>
      `).join("")
      : '<tr><td colspan="5">No saved allocations yet.</td></tr>';

  } catch (error) {
    tbody.innerHTML =
      `<tr><td colspan="5">${escapeHtml(error.message)}</td></tr>`;
  }
}

el("load-history").addEventListener(
  "click",
  loadAllocationHistory
);


// Start dashboard.
init();
loadAllocationHistory();

// =====================================
// ADMIN LOGIN / LOGOUT
// =====================================

function updateAdminUI() {
  const loggedIn = Boolean(
    sessionStorage.getItem("admin_token")
  );

  el("admin-status").textContent =
    loggedIn ? "Admin Logged In" : "Guest Mode";

  el("admin-login-btn").hidden = loggedIn;
  el("admin-logout-btn").hidden = !loggedIn;

  renderCandidates();
  renderInternships();
}

el("admin-login-btn").addEventListener("click", async () => {
  const username = prompt("Enter admin username:");
  if (!username) return;

  const password = prompt("Enter admin password:");
  if (!password) return;

  try {
    const response = await fetch(`${API}/api/admin/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Login failed");
    }

    sessionStorage.setItem("admin_token", data.access_token);

    updateAdminUI();
    showToast("Admin login successful!");

  } catch (error) {
    showToast(`Login error: ${error.message}`);
  }
});

el("admin-logout-btn").addEventListener("click", () => {
  sessionStorage.removeItem("admin_token");
  updateAdminUI();
  showToast("Admin logged out.");
});


// =====================================
// ADMIN-ONLY DELETE
// =====================================

async function deleteRecord(endpoint, type) {
  const token = sessionStorage.getItem("admin_token");

  if (!token) {
    showToast("Please login as admin first.");
    return;
  }

  if (!confirm(`Are you sure you want to delete this ${type}?`)) {
    return;
  }

  try {
    const response = await fetch(`${API}${endpoint}`, {
      method: "DELETE",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });

    const data = await response.json();

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        sessionStorage.removeItem("admin_token");
        updateAdminUI();
      }

      throw new Error(data.detail || "Delete failed");
    }

    showToast(`${type} deleted successfully!`);
    await init();
    await loadAllocationHistory();

  } catch (error) {
    showToast(`Error: ${error.message}`);
  }
}


// Update login status when page loads.
updateAdminUI();