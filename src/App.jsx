import { useState, useEffect } from "react";

import "./App.css";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");



function getHostname(urlString) {

  if (!urlString) return "No website audited yet";

  try {

    return new URL(urlString).hostname;

  } catch {

    return urlString;

  }

}



const initialIssues = [

  {

    id: 1,

    title: "Images missing alternative text",

    description:

      "Some images do not have alternative text for screen-reader users.",

    severity: "Serious",

    wcag: "WCAG 1.1.1",

    element: "<img>",

    recommendation:

      "Add a descriptive alt attribute to meaningful images. Use alt=\"\" for purely decorative images.",

  },

  {

    id: 2,

    title: "Insufficient color contrast",

    description:

      "Some text may not have enough contrast against its background.",

    severity: "Moderate",

    wcag: "WCAG 1.4.3",

    element: "Text elements",

    recommendation:

      "Adjust the foreground and background colors to meet the required contrast ratio.",

  },

  {

    id: 3,

    title: "Form field missing label",

    description:

      "A form control may not have an accessible name.",

    severity: "Serious",

    wcag: "WCAG 4.1.2",

    element: "<input>",

    recommendation:

      "Associate a descriptive <label> with the input, or provide an appropriate accessible name.",

  },

  {

    id: 4,

    title: "Links need descriptive text",

    description:

      "Some links may not clearly communicate their destination.",

    severity: "Minor",

    wcag: "WCAG 2.4.4",

    element: "<a>",

    recommendation:

      "Use meaningful link text that explains the destination or purpose of the link.",

  },

];



const emptySummary = {

  score: null,

  total: 0,

  critical: 0,

  serious: 0,

  moderate: 0,

  minor: 0,

  passed: 0,

};



function Icon({ name, size = 20 }) {

  const paths = {

    dashboard: (

      <>

        <rect x="3" y="3" width="7" height="9" rx="1" />

        <rect x="14" y="3" width="7" height="5" rx="1" />

        <rect x="14" y="12" width="7" height="9" rx="1" />

        <rect x="3" y="16" width="7" height="5" rx="1" />

      </>

    ),

    scan: (

      <>

        <circle cx="10.5" cy="10.5" r="6.5" />

        <path d="m16 16 4.5 4.5M8 10.5l2 2 3.5-4" />

      </>

    ),

    report: (

      <>

        <path d="M7 3h7l5 5v13H7z" />

        <path d="M14 3v5h5M10 13h6M10 17h6" />

      </>

    ),

    about: (

      <>

        <circle cx="12" cy="12" r="9" />

        <path d="M12 11v5M12 8h.01" />

      </>

    ),

    settings: (

      <>

        <circle cx="12" cy="12" r="3" />

        <path d="m19.4 15 .1.1 1.1 1.8-2 3.4-2.1-.5a8 8 0 0 1-2 .9l-.8 2.1h-4l-.8-2.1a8 8 0 0 1-2-.9l-2.1.5-2-3.4 1.1-1.8a8 8 0 0 1 0-2l-1.1-1.8 2-3.4 2.1.5a8 8 0 0 1 2-.9l.8-2.1h4l.8 2.1a8 8 0 0 1 2 .9l2.1-.5 2 3.4-1.1 1.8a8 8 0 0 1-.1 2Z" transform="translate(0 -2) scale(1 .95)" />

      </>

    ),

    globe: (

      <>

        <circle cx="12" cy="12" r="9" />

        <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" />

      </>

    ),

    alert: (

      <>

        <path d="m12 3 10 18H2L12 3Z" />

        <path d="M12 9v5M12 17h.01" />

      </>

    ),

    check: <path d="m5 12 4 4L19 6" />,

    sparkle: (

      <>

        <path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-2-5.8L4 11l6-2.2L12 3Z" />

        <path d="m19 14 1.1 2.9L23 18l-2.9 1.1L19 22l-1.1-2.9L15 18l2.9-1.1L19 14Z" />

      </>

    ),

    download: (

      <>

        <path d="M12 3v12m-5-5 5 5 5-5" />

        <path d="M5 17v4h14v-4" />

      </>

    ),

    arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,

    clock: (

      <>

        <circle cx="12" cy="12" r="9" />

        <path d="M12 7v5l3 2" />

      </>

    ),

    menu: <path d="M4 6h16M4 12h16M4 18h16" />,

  };



  return (

    <svg

      width={size}

      height={size}

      viewBox="0 0 24 24"

      fill="none"

      stroke="currentColor"

      strokeWidth="1.7"

      strokeLinecap="round"

      strokeLinejoin="round"

      aria-hidden="true"

    >

      {paths[name] || paths.dashboard}

    </svg>

  );

}



function App() {

  const [url, setUrl] = useState("");

  const [activePage, setActivePage] = useState("Dashboard");

  const [filter, setFilter] = useState("All");

  const [issues, setIssues] = useState([]);

  const [summary, setSummary] = useState(emptySummary);

  const [scanning, setScanning] = useState(false);

  const [message, setMessage] = useState("");

  const [selectedIssue, setSelectedIssue] = useState(null);

  const [completedIssues, setCompletedIssues] = useState([]);

  const [history, setHistory] = useState([]);



  useEffect(() => {

    fetchHistory();

  }, []);



  async function fetchHistory() {

    try {

      const res = await fetch(`${API_BASE_URL}/api/scans`);

      if (res.ok) {

        const data = await res.json();

        setHistory(data);

      }

    } catch {

      // Backend not yet available

    }

  }



  async function loadPastScan(scanId) {

    try {

      setMessage("Loading scan details...");

      const res = await fetch(`${API_BASE_URL}/api/scans/${scanId}`);

      if (!res.ok) throw new Error("Could not load past scan.");

      const data = await res.json();

      setUrl(data.url);

      setIssues(data.issues || []);

      setSummary(data.summary || emptySummary);

      setSelectedIssue(null);

      setCompletedIssues([]);

      setActivePage("Dashboard");

      setMessage(`Loaded previous audit for ${data.url}`);

    } catch (err) {

      setMessage(err.message || "Failed to load audit");

    }

  }



  const filteredIssues =

    filter === "All"

      ? issues

      : issues.filter((issue) => issue.severity === filter);



  function normalizeUrl(value) {

    let normalized = value.trim();



    if (!/^https?:\/\//i.test(normalized)) {

      normalized = `https://${normalized}`;

    }



    try {

      const parsed = new URL(normalized);



      if (!["http:", "https:"].includes(parsed.protocol)) {

        return null;

      }



      return parsed.href;

    } catch {

      return null;

    }

  }



  async function handleScan(event) {

    event.preventDefault();



    const normalized = normalizeUrl(url);



    if (!normalized) {

      setMessage("Please enter a valid website URL.");

      return;

    }



    setUrl(normalized);

    setMessage("");

    setScanning(true);

    setSelectedIssue(null);

    setCompletedIssues([]);

    setIssues([]);

    setSummary(emptySummary);



    try {

      const response = await fetch(`${API_BASE_URL}/api/audit`, {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify({ url: normalized }),

      });



      if (!response.ok) {

        const errorData = await response.json().catch(() => ({}));

        throw new Error(errorData.detail || `Scan request failed with HTTP ${response.status}`);

      }



      const result = await response.json();

      setIssues(result.issues || []);

      setSummary(result.summary || emptySummary);

      setActivePage("Dashboard");

      setMessage(

        `Audit completed! Found ${result.summary.total} issue(s) on ${result.url}.`

      );

      fetchHistory();

    } catch (error) {

      setMessage(

        error.message || "Unable to run the audit. Please verify the URL and backend server."

      );

    } finally {

      setScanning(false);

    }

  }



  function toggleFixed(issueId) {

    setCompletedIssues((previous) =>

      previous.includes(issueId)

        ? previous.filter((id) => id !== issueId)

        : [...previous, issueId]

    );

  }



  function downloadReport() {

    if (!issues.length) {

      setMessage("Run an audit before downloading a report.");

      return;

    }



    const host = getHostname(url);

    const report = [

      "===========================================================",

      "           ACCESSAI - WEBSITE ACCESSIBILITY AUDIT          ",

      "===========================================================",

      `Generated:        ${new Date().toLocaleString()}`,

      `Website:          ${url}`,

      `Overall Score:    ${summary.score ?? "N/A"}/100`,

      `Total Issues:     ${summary.total}`,

      `  - Critical:     ${summary.critical}`,

      `  - Serious:      ${summary.serious}`,

      `  - Moderate:     ${summary.moderate}`,

      `  - Minor:        ${summary.minor}`,

      `Checks Passed:    ${summary.passed}`,

      "===========================================================",

      "",

      "DETAILED FINDINGS & REMEDIATION RECOMMENDATIONS:",

      "-----------------------------------------------------------",

      ...issues.map(

        (issue, idx) =>

          `[${idx + 1}] ${issue.title.toUpperCase()}\n` +

          `Severity:       ${issue.severity}\n` +

          `WCAG Criterion: ${issue.wcag || "N/A"}\n` +

          `Element:        ${issue.element || "N/A"}\n` +

          (issue.element_html ? `Code Snippet:   ${issue.element_html}\n` : "") +

          `Description:    ${issue.description}\n` +

          `Suggested Fix:  ${issue.recommendation}\n`

      ),

      "===========================================================",

      "Note: Automated accessibility audits cover high-impact WCAG",

      "rules. Combine with manual user testing for full conformance.",

      "===========================================================",

    ].join("\n");



    const blob = new Blob([report], {

      type: "text/plain;charset=utf-8",

    });



    const objectUrl = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = objectUrl;

    link.download = `accessai-audit-${host.replace(/[^a-zA-Z0-9.-]/g, "_")}.txt`;

    link.click();

    URL.revokeObjectURL(objectUrl);

  }



  const navItems = [

    { name: "Dashboard", icon: "dashboard" },

    { name: "New Audit", icon: "scan" },

    { name: "Issues & Fixes", icon: "alert" },

    { name: "Reports", icon: "report" },

    { name: "About Project", icon: "about" },

  ];



  function renderDashboard() {

    return (

      <>

        <div className="welcome-row">

          <div>

            <div className="eyebrow">OVERVIEW</div>

            <h1>Accessibility Dashboard</h1>

            <p className="page-description">

              Find accessibility issues and improve your website experience.

            </p>

          </div>

          <button

            className="primary-button"

            onClick={() => setActivePage("New Audit")}

          >

            <Icon name="scan" size={18} />

            New Audit

          </button>

        </div>



        <section className="url-panel">

          <div className="url-heading">

            <div className="url-icon">

              <Icon name="globe" size={21} />

            </div>

            <div>

              <h2>Analyze your website</h2>

              <p>Enter a URL to check its accessibility.</p>

            </div>

          </div>



          <form className="url-form" onSubmit={handleScan}>

            <div className="input-wrapper">

              <Icon name="globe" size={18} />

              <input

                aria-label="Website URL"

                type="text"

                placeholder="https://example.com"

                value={url}

                onChange={(event) => setUrl(event.target.value)}

              />

            </div>

            <button className="primary-button" disabled={scanning}>

              {scanning ? (

                <>

                  <span className="spinner" />

                  Scanning...

                </>

              ) : (

                <>

                  <Icon name="scan" size={18} />

                  Analyze Website

                </>

              )}

            </button>

          </form>



          <div className="sample-urls-row">

            <span className="sample-url-label">Quick sample:</span>

            <button

              type="button"

              className="sample-url-btn"

              onClick={() => setUrl("https://example.com")}

            >

              example.com

            </button>

            <button

              type="button"

              className="sample-url-btn"

              onClick={() => setUrl("https://wikipedia.org")}

            >

              wikipedia.org

            </button>

            <button

              type="button"

              className="sample-url-btn"

              onClick={() => {

                setUrl("https://demo-site.example.com");

                setIssues(initialIssues);

                setSummary({

                  score: 76,

                  total: 12,

                  critical: 2,

                  serious: 4,

                  moderate: 4,

                  minor: 2,

                  passed: 38,

                });

                setMessage("Sample demonstration findings loaded.");

              }}

            >

              Load Sample Demo

            </button>

          </div>



          {message && (

            <p className="status-message" role="status">

              {message}

            </p>

          )}

        </section>



        <section className="stats-grid" aria-label="Audit summary">

          <StatCard

            icon="gauge"

            label="Accessibility Score"

            value={summary.score === null ? "—" : `${summary.score}/100`}

            note={

              summary.score === null

                ? "Awaiting audit"

                : summary.score >= 90

                ? "High conformance"

                : summary.score >= 70

                ? "Needs improvement"

                : "Critical remediation needed"

            }

            tone="purple"

          />

          <StatCard

            icon="alert"

            label="Issues Detected"

            value={summary.total}

            note="Detected findings"

            tone="red"

          />

          <StatCard

            icon="alert"

            label="Serious Issues"

            value={summary.serious + summary.critical}

            note="Critical + serious"

            tone="orange"

          />

          <StatCard

            icon="check"

            label="Checks Passed"

            value={summary.passed}

            note="Automated checks"

            tone="green"

          />

        </section>



        <section className="content-grid">

          <div className="panel severity-panel">

            <div className="panel-heading">

              <div>

                <h2>Issues by severity</h2>

                <p>Prioritize the most important findings.</p>

              </div>

              <span className="subtle-icon">

                <Icon name="dashboard" />

              </span>

            </div>



            <div className="severity-chart">

              {[

                {

                  label: "Critical",

                  count: summary.critical,

                  color: "#dc2626",

                },

                {

                  label: "Serious",

                  count: summary.serious,

                  color: "#ea580c",

                },

                {

                  label: "Moderate",

                  count: summary.moderate,

                  color: "#d97706",

                },

                {

                  label: "Minor",

                  count: summary.minor,

                  color: "#2563eb",

                },

              ].map((item) => (

                <div className="severity-item" key={item.label}>

                  <div className="severity-meta">

                    <span>{item.label}</span>

                    <strong>{item.count}</strong>

                  </div>

                  <div

                    className="progress-track"

                    role="img"

                    aria-label={`${item.label}: ${item.count} issues`}

                  >

                    <div

                      className="progress-fill"

                      style={{

                        width:

                          summary.total > 0

                            ? `${(item.count / summary.total) * 100}%`

                            : "0%",

                        backgroundColor: item.color,

                      }}

                    />

                  </div>

                </div>

              ))}

            </div>

          </div>



          <div className="panel score-panel">

            <div className="panel-heading">

              <div>

                <h2>Accessibility health</h2>

                <p>Overall audit summary.</p>

              </div>

            </div>

            <div className="score-circle">

              <div className="score-inner">

                <strong>

                  {summary.score === null ? "—" : summary.score}

                </strong>

                <span>out of 100</span>

              </div>

            </div>

            <div className="score-caption">

              {summary.score === null

                ? "Run an audit to see your score."

                : summary.score >= 90

                ? "Good accessibility rating"

                : "Room for improvement"}

            </div>

            <p className="score-disclaimer">

              {summary.score === null

                ? "This is an automated score based on WCAG checks."

                : `Audited ${getHostname(url)} against WCAG 2.1 rules.`}

            </p>

          </div>

        </section>



        <IssuesPanel

          issues={issues.slice(0, 4)}

          completedIssues={completedIssues}

          onSelect={setSelectedIssue}

          onToggleFixed={toggleFixed}

          onViewAll={() => setActivePage("Issues & Fixes")}

        />



        <RecommendationPanel

          issue={issues.find((item) => !completedIssues.includes(item.id))}

        />



        <HistoryPanel

          history={history}

          onLoadScan={loadPastScan}

          onRefresh={fetchHistory}

        />

      </>

    );

  }



  function renderNewAudit() {

    return (

      <section className="page-section">

        <PageHeading

          eyebrow="SCANNER"

          title="New Website Audit"

          description="Start an accessibility check on a website."

        />

        <div className="panel form-panel">

          <div className="large-feature-icon">

            <Icon name="scan" size={28} />

          </div>

          <h2>Scan a website</h2>

          <p className="muted">

            Enter a public website URL to begin the audit workflow.

          </p>

          <form className="audit-form" onSubmit={handleScan}>

            <label htmlFor="audit-url">Website URL</label>

            <input

              id="audit-url"

              type="text"

              placeholder="https://example.com"

              value={url}

              onChange={(event) => setUrl(event.target.value)}

              required

            />

            <button className="primary-button" disabled={scanning}>

              <Icon name="scan" />

              {scanning ? "Scanning..." : "Start Accessibility Audit"}

            </button>

          </form>



          <div className="sample-urls-row">

            <span className="sample-url-label">Quick sample:</span>

            <button

              type="button"

              className="sample-url-btn"

              onClick={() => setUrl("https://example.com")}

            >

              example.com

            </button>

            <button

              type="button"

              className="sample-url-btn"

              onClick={() => setUrl("https://wikipedia.org")}

            >

              wikipedia.org

            </button>

          </div>



          {message && (

            <p className="status-message" role="status">

              {message}

            </p>

          )}

          <div className="audit-info">

            <strong>Audit checks</strong>

            <span>Images and alternative text</span>

            <span>Text contrast and readability</span>

            <span>Form labels and accessible names</span>

            <span>Common WCAG accessibility rules</span>

          </div>

        </div>

      </section>

    );

  }



  function renderIssues() {

    return (

      <section className="page-section">

        <PageHeading

          eyebrow="FINDINGS"

          title="Issues & Fixes"

          description="Review detected problems and their suggested corrections."

        />



        <div className="filter-row" aria-label="Filter issues by severity">

          {["All", "Critical", "Serious", "Moderate", "Minor"].map(

            (severity) => (

              <button

                key={severity}

                className={`filter-chip ${filter === severity ? "active" : ""}`}

                onClick={() => setFilter(severity)}

                aria-pressed={filter === severity}

              >

                {severity}

              </button>

            )

          )}

        </div>



        <IssuesPanel

          issues={filteredIssues}

          completedIssues={completedIssues}

          onSelect={setSelectedIssue}

          onToggleFixed={toggleFixed}

        />



        {selectedIssue && (

          <div className="panel detail-panel">

            <div className="detail-header">

              <div>

                <span className="eyebrow">ISSUE DETAILS</span>

                <h2>{selectedIssue.title}</h2>

              </div>

              <button

                className="icon-button"

                onClick={() => setSelectedIssue(null)}

                aria-label="Close issue details"

              >

                ×

              </button>

            </div>

            <p>{selectedIssue.description}</p>

            <div className="detail-meta">

              <span>

                <strong>Severity:</strong> {selectedIssue.severity}

              </span>

              <span>

                <strong>Criterion:</strong> {selectedIssue.wcag}

              </span>

              <span>

                <strong>Element:</strong> {selectedIssue.element}

              </span>

            </div>

            {selectedIssue.element_html && (

              <div className="code-snippet-box">

                <div className="code-snippet-title">Detected HTML Snippet</div>

                <pre className="code-snippet-pre">{selectedIssue.element_html}</pre>

              </div>

            )}

            <div className="ai-box">

              <div className="ai-title">

                <Icon name="sparkle" />

                Suggested fix

              </div>

              <p>{selectedIssue.recommendation}</p>

            </div>

            <p className="muted small">

              Verify the suggested correction against the actual markup before

              applying it.

            </p>

          </div>

        )}

      </section>

    );

  }



  function renderReports() {

    return (

      <section className="page-section">

        <PageHeading

          eyebrow="EXPORT"

          title="Audit Reports"

          description="Download a summary of your current audit."

        />

        <div className="panel report-panel">

          <div className="report-file-icon">

            <Icon name="report" size={28} />

          </div>

          <div className="report-content">

            <h2>{getHostname(url)}</h2>

            <p>

              {issues.length

                ? `${summary.total} findings · Score ${summary.score}/100`

                : "Run an audit to generate a report."}

            </p>

          </div>

          <button

            className="primary-button"

            onClick={downloadReport}

            disabled={!issues.length}

          >

            <Icon name="download" size={18} />

            Download Report

          </button>

        </div>

        <p className="muted small">

          The export includes complete audit findings, WCAG references, code snippets, and AI suggested fixes.

        </p>



        <HistoryPanel

          history={history}

          onLoadScan={loadPastScan}

          onRefresh={fetchHistory}

        />

      </section>

    );

  }



  function renderAbout() {

    return (

      <section className="page-section">

        <PageHeading

          eyebrow="PROJECT INFORMATION"

          title="About AccessAI"

          description="AI-assisted website accessibility auditing."

        />

        <div className="panel about-panel">

          <div className="large-feature-icon">

            <Icon name="sparkle" size={28} />

          </div>

          <h2>Project objective</h2>

          <p>

            AccessAI aims to help developers identify common website

            accessibility problems, understand why they matter, and discover

            possible ways to fix them.

          </p>

          <h3>Technology stack</h3>

          <div className="technology-list">

            {["React", "Vite", "FastAPI", "Python", "MySQL", "SQLAlchemy", "BeautifulSoup", "WCAG 2.1"].map((technology) => (

              <span className="technology-chip" key={technology}>

                {technology}

              </span>

            ))}

          </div>

          <div className="ai-box">

            <div className="ai-title">

              <Icon name="alert" />

              Project limitation

            </div>

            <p>

              Automated testing identifies many common accessibility issues,

              but it cannot establish full WCAG conformance. Manual testing

              is also necessary.

            </p>

          </div>

        </div>

      </section>

    );

  }



  return (

    <div className="app-shell">

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-icon">

            <Icon name="dashboard" size={23} />

          </div>

          <div className="brand-text">

            <strong>AccessAI</strong>

            <span>Accessibility Auditor</span>

          </div>

        </div>



        <div className="nav-label">WORKSPACE</div>

        <nav className="sidebar-nav" aria-label="Main navigation">

          {navItems.map((item) => (

            <button

              key={item.name}

              className={`nav-item ${

                activePage === item.name ? "active" : ""

              }`}

              onClick={() => {

                setActivePage(item.name);

                setMessage("");

                setSelectedIssue(null);

              }}

              aria-current={activePage === item.name ? "page" : undefined}

            >

              <Icon name={item.icon} size={19} />

              <span>{item.name}</span>

              {item.name === "Issues & Fixes" && issues.length > 0 && (

                <span className="nav-count">{issues.length}</span>

              )}

            </button>

          ))}

        </nav>



        <div className="sidebar-bottom">

          <div className="project-status">

            <div className="status-dot" />

            <div>

              <strong>Mini Project</strong>

              <span>React Dashboard</span>

            </div>

          </div>

          <p>Making the web more accessible.</p>

        </div>

      </aside>



      <div className="main-column">

        <header className="topbar">

          <div className="breadcrumb">

            <span>AccessAI</span>

            <Icon name="arrow" size={14} />

            <strong>{activePage}</strong>

          </div>

          <div className="topbar-right">

            <span className="demo-badge">DEMO VERSION</span>

            <div className="avatar" aria-label="Project user">

              A

            </div>

          </div>

        </header>



        <main className="main-content">

          {activePage === "Dashboard" && renderDashboard()}

          {activePage === "New Audit" && renderNewAudit()}

          {activePage === "Issues & Fixes" && renderIssues()}

          {activePage === "Reports" && renderReports()}

          {activePage === "About Project" && renderAbout()}

        </main>



        <footer className="footer">

          <span>AccessAI · AI Website Accessibility Auditor</span>

          <span>Automated checks are not a compliance certification.</span>

        </footer>

      </div>

    </div>

  );

}



function StatCard({ icon, label, value, note, tone }) {

  return (

    <div className="stat-card">

      <div className={`stat-icon ${tone}`}>

        <Icon name={icon} size={21} />

      </div>

      <div className="stat-label">{label}</div>

      <div className="stat-value">{value}</div>

      <div className="stat-note">{note}</div>

    </div>

  );

}



function PageHeading({ eyebrow, title, description }) {

  return (

    <div className="welcome-row page-heading">

      <div>

        <div className="eyebrow">{eyebrow}</div>

        <h1>{title}</h1>

        <p className="page-description">{description}</p>

      </div>

    </div>

  );

}



function IssuesPanel({

  issues,

  completedIssues,

  onSelect,

  onToggleFixed,

  onViewAll,

}) {

  return (

    <section className="panel issues-panel">

      <div className="panel-heading">

        <div>

          <h2>Detected issues</h2>

          <p>Review findings and suggested corrections.</p>

        </div>

        {onViewAll && (

          <button className="text-button" onClick={onViewAll}>

            View all <Icon name="arrow" size={15} />

          </button>

        )}

      </div>



      {issues.length === 0 ? (

        <div className="empty-state">

          <Icon name="scan" size={30} />

          <strong>No findings to display</strong>

          <p>Run a demo audit to populate this list.</p>

        </div>

      ) : (

        <div className="issue-list">

          {issues.map((issue) => {

            const isCompleted = completedIssues.includes(issue.id);



            return (

              <div

                className={`issue-row ${isCompleted ? "issue-completed" : ""}`}

                key={issue.id}

              >

                <div className={`issue-severity-icon ${issue.severity.toLowerCase()}`}>

                  <Icon

                    name={isCompleted ? "check" : "alert"}

                    size={19}

                  />

                </div>

                <button

                  className="issue-main"

                  onClick={() => onSelect(issue)}

                  aria-label={`View details: ${issue.title}`}

                >

                  <strong>{issue.title}</strong>

                  <span>

                    {issue.wcag} <span className="dot-separator">·</span>{" "}

                    {issue.element}

                  </span>

                </button>

                <span

                  className={`severity-badge ${issue.severity.toLowerCase()}`}

                >

                  {issue.severity}

                </span>

                <button

                  className={`resolve-button ${isCompleted ? "resolved" : ""}`}

                  onClick={() => onToggleFixed(issue.id)}

                  aria-pressed={isCompleted}

                >

                  {isCompleted ? "Reviewed" : "Mark reviewed"}

                </button>

              </div>

            );

          })}

        </div>

      )}

    </section>

  );

}



function RecommendationPanel({ issue }) {

  return (

    <section className="recommendation-panel">

      <div className="recommendation-icon">

        <Icon name="sparkle" size={23} />

      </div>

      <div className="recommendation-copy">

        <div className="recommendation-heading">AI-powered recommendation</div>

        <p>

          {issue

            ? issue.recommendation

            : "Run an audit and review findings to get accessibility recommendations."}

        </p>

        <span>

          Suggested guidance · Review before applying

        </span>

      </div>

    </section>

  );

}



function HistoryPanel({ history, onLoadScan, onRefresh }) {

  return (

    <section className="panel" style={{ marginTop: "24px" }}>

      <div className="panel-heading">

        <div>

          <h2>Audit history (Database)</h2>

          <p>Past accessibility audits stored in MySQL.</p>

        </div>

        {onRefresh && (

          <button className="text-button" onClick={onRefresh}>

            Refresh

          </button>

        )}

      </div>



      {!history || history.length === 0 ? (

        <div className="empty-state">

          <Icon name="clock" size={26} />

          <strong>No previous audits in database</strong>

          <p>Analyze a website URL above to perform a live scan and save findings.</p>

        </div>

      ) : (

        <div className="issue-list">

          {history.map((scan) => {

            const scoreNum =

              scan.accessibility_score !== null

                ? Math.round(scan.accessibility_score)

                : null;

            const badgeClass =

              scoreNum !== null

                ? scoreNum >= 85

                  ? "minor"

                  : scoreNum >= 60

                  ? "moderate"

                  : "critical"

                : "moderate";



            return (

              <div className="issue-row" key={scan.scan_id}>

                <div className="issue-severity-icon moderate">

                  <Icon name="globe" size={18} />

                </div>

                <div className="issue-main" style={{ textAlign: "left" }}>

                  <strong>{scan.website_url || scan.website_name}</strong>

                  <span>

                    {scan.created_at} <span className="dot-separator">·</span>{" "}

                    {scan.total_issues} issues detected ({scan.critical_issues} critical,{" "}

                    {scan.serious_issues} serious)

                  </span>

                </div>

                <span className={`severity-badge ${badgeClass}`}>

                  {scoreNum !== null ? `${scoreNum}/100` : "Pending"}

                </span>

                <button

                  className="resolve-button"

                  onClick={() => onLoadScan(scan.scan_id)}

                >

                  Load Audit

                </button>

              </div>

            );

          })}

        </div>

      )}

    </section>

  );

}



export default App;