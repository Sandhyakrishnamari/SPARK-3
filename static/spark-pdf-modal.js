/**
 * SPARK INTERACTIVE PDF EXPORT MODAL & VIEWER MODULE
 */

const SparkPDFModal = (function () {
    let modalCreated = false;
    let currentStudentId = null; // null means current logged in student
    let downloadEndpoint = "/student/record/download";

    let state = {
        theme: "navy",
        interactive_checklist: true,
        fillable_notes: true,
        clickable_links: true,
        sections: [
            "profile",
            "academics",
            "test_scores",
            "milestones",
            "universities",
            "activities",
            "essays",
            "deadlines",
            "prerequisites",
            "readiness_checklist"
        ]
    };

    function initModalHTML() {
        if (document.getElementById("sparkPdfModalBackdrop")) return;

        const html = `
        <div class="spark-pdf-backdrop" id="sparkPdfModalBackdrop">
            <div class="spark-pdf-modal">
                <!-- Header -->
                <div class="spark-pdf-header">
                    <div class="spark-pdf-header-title">
                        <div class="spark-pdf-header-icon">📄</div>
                        <div>
                            <h2>SPARK Interactive PDF Builder</h2>
                            <p>Customize & export a high-performance vector PDF report</p>
                        </div>
                    </div>
                    <button class="spark-pdf-close" onclick="SparkPDFModal.close()" title="Close">&times;</button>
                </div>

                <!-- Body -->
                <div class="spark-pdf-body">
                    <!-- Left Column: Customization -->
                    <div>
                        <!-- Theme -->
                        <div class="spark-pdf-section-label">🎨 Report Theme</div>
                        <div class="spark-pdf-themes">
                            <div class="spark-pdf-theme-card selected" data-theme="navy" onclick="SparkPDFModal.selectTheme('navy')">
                                <div class="spark-pdf-theme-colors">
                                    <span class="spark-pdf-dot" style="background:#0B3475"></span>
                                    <span class="spark-pdf-dot" style="background:#FF9B1A"></span>
                                    <span class="spark-pdf-dot" style="background:#E8C978"></span>
                                </div>
                                <div class="spark-pdf-theme-name">Classic Navy</div>
                            </div>
                            <div class="spark-pdf-theme-card" data-theme="emerald" onclick="SparkPDFModal.selectTheme('emerald')">
                                <div class="spark-pdf-theme-colors">
                                    <span class="spark-pdf-dot" style="background:#065F46"></span>
                                    <span class="spark-pdf-dot" style="background:#10B981"></span>
                                    <span class="spark-pdf-dot" style="background:#A7F3D0"></span>
                                </div>
                                <div class="spark-pdf-theme-name">Emerald</div>
                            </div>
                            <div class="spark-pdf-theme-card" data-theme="sunset" onclick="SparkPDFModal.selectTheme('sunset')">
                                <div class="spark-pdf-theme-colors">
                                    <span class="spark-pdf-dot" style="background:#7C2D12"></span>
                                    <span class="spark-pdf-dot" style="background:#F97316"></span>
                                    <span class="spark-pdf-dot" style="background:#FDE68A"></span>
                                </div>
                                <div class="spark-pdf-theme-name">Sunset Gold</div>
                            </div>
                        </div>

                        <!-- Interactivity Toggles -->
                        <div class="spark-pdf-section-label">⚡ PDF Interactivity Options</div>
                        <div class="spark-pdf-features">
                            <div class="spark-pdf-toggle-item active" id="toggleChecklist" onclick="SparkPDFModal.toggleFeature('interactive_checklist')">
                                <div class="spark-pdf-toggle-info">
                                    <span class="spark-pdf-toggle-icon">☑️</span>
                                    <div>
                                        <div class="spark-pdf-toggle-title">Fillable PDF Checkboxes</div>
                                        <div class="spark-pdf-toggle-desc">AcroForm checkboxes checkable right inside Acrobat/Chrome PDF</div>
                                    </div>
                                </div>
                                <div class="spark-pdf-switch"></div>
                            </div>

                            <div class="spark-pdf-toggle-item active" id="toggleNotes" onclick="SparkPDFModal.toggleFeature('fillable_notes')">
                                <div class="spark-pdf-toggle-info">
                                    <span class="spark-pdf-toggle-icon">💬</span>
                                    <div>
                                        <div class="spark-pdf-toggle-title">Interactive Counselor Notes Box</div>
                                        <div class="spark-pdf-toggle-desc">Fillable text field inside PDF for reflections & next steps</div>
                                    </div>
                                </div>
                                <div class="spark-pdf-switch"></div>
                            </div>

                            <div class="spark-pdf-toggle-item active" id="toggleLinks" onclick="SparkPDFModal.toggleFeature('clickable_links')">
                                <div class="spark-pdf-toggle-info">
                                    <span class="spark-pdf-toggle-icon">🔗</span>
                                    <div>
                                        <div class="spark-pdf-toggle-title">Clickable Hyperlinks & Navigation</div>
                                        <div class="spark-pdf-toggle-desc">Direct email links, SPARK portal links & university URLs</div>
                                    </div>
                                </div>
                                <div class="spark-pdf-switch"></div>
                            </div>
                        </div>

                        <!-- Included Sections -->
                        <div class="spark-pdf-section-label">📑 Select Report Content</div>
                        <div class="spark-pdf-sections-grid">
                            <label class="spark-pdf-chip checked">
                                <input type="checkbox" checked value="profile" onchange="SparkPDFModal.updateSections()"> 👤 Profile & KPIs
                            </label>
                            <label class="spark-pdf-chip checked">
                                <input type="checkbox" checked value="academics" onchange="SparkPDFModal.updateSections()"> 📚 Coursework & Marks
                            </label>
                            <label class="spark-pdf-chip checked">
                                <input type="checkbox" checked value="test_scores" onchange="SparkPDFModal.updateSections()"> 🎯 Test Scores
                            </label>
                            <label class="spark-pdf-chip checked">
                                <input type="checkbox" checked value="universities" onchange="SparkPDFModal.updateSections()"> 🏛️ Target Colleges
                            </label>
                            <label class="spark-pdf-chip checked">
                                <input type="checkbox" checked value="activities" onchange="SparkPDFModal.updateSections()"> 🏆 Activities & Impact
                            </label>
                            <label class="spark-pdf-chip checked">
                                <input type="checkbox" checked value="readiness_checklist" onchange="SparkPDFModal.updateSections()"> ✅ Readiness Checklist
                            </label>
                        </div>
                    </div>

                    <!-- Right Column: Live Status & Preview Card -->
                    <div class="spark-pdf-preview-card">
                        <div>
                            <div class="spark-pdf-preview-header">
                                <span class="spark-pdf-preview-title">PDF Document Preview</span>
                                <span class="spark-pdf-badge" id="sparkPdfThemeBadge">Navy Theme</span>
                            </div>

                            <div class="spark-pdf-preview-list">
                                <div class="spark-pdf-preview-item">
                                    <span>Format:</span> <strong>Vector Standard PDF 1.4</strong>
                                </div>
                                <div class="spark-pdf-preview-item">
                                    <span>Interactivity:</span> <strong id="sparkPdfInteractivityBadge">Active (AcroForms & Links)</strong>
                                </div>
                                <div class="spark-pdf-preview-item">
                                    <span>Content Sections:</span> <strong id="sparkPdfSectionCount">6 Sections Included</strong>
                                </div>
                                <div class="spark-pdf-preview-item">
                                    <span>Navigation:</span> <strong>PDF Outline Bookmarks Included</strong>
                                </div>
                            </div>
                        </div>

                        <!-- Progress Bar Container -->
                        <div class="spark-pdf-progress-container">
                            <div class="spark-pdf-progress-text">
                                <span id="sparkPdfProgressStep">Ready to compile</span>
                                <span id="sparkPdfProgressPercent">0%</span>
                            </div>
                            <div class="spark-pdf-progress-bar">
                                <div class="spark-pdf-progress-fill" id="sparkPdfProgressFill"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div class="spark-pdf-footer">
                    <button class="spark-pdf-btn spark-pdf-btn-secondary" onclick="SparkPDFModal.preview()">
                        👁️ Live Preview PDF
                    </button>

                    <div style="display:flex;gap:10px;">
                        <button class="spark-pdf-btn spark-pdf-btn-secondary" onclick="SparkPDFModal.close()">
                            Cancel
                        </button>
                        <button class="spark-pdf-btn spark-pdf-btn-primary spark-pdf-pulse" id="sparkPdfDownloadBtn" onclick="SparkPDFModal.startDownload()">
                            ⚡ Download Interactive PDF
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Inline PDF Viewer Modal -->
        <div class="spark-pdf-viewer-backdrop" id="sparkPdfViewerBackdrop">
            <div class="spark-pdf-viewer-bar">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-size:20px;">📄</span>
                    <strong style="font-size:15px;" id="sparkPdfViewerTitle">SPARK Interactive PDF Live Preview</strong>
                </div>
                <div style="display:flex;gap:10px;align-items:center;">
                    <button class="spark-pdf-btn spark-pdf-btn-primary" onclick="SparkPDFModal.startDownload()" style="padding:8px 16px;font-size:12px;">
                        ⬇️ Save File
                    </button>
                    <button class="spark-pdf-close" onclick="SparkPDFModal.closeViewer()">&times;</button>
                </div>
            </div>
            <iframe class="spark-pdf-viewer-iframe" id="sparkPdfViewerIframe" src="about:blank"></iframe>
        </div>
        `;

        document.body.insertAdjacentHTML("beforeend", html);
        modalCreated = true;
    }

    function buildQueryString(extraParams = {}) {
        const params = new URLSearchParams();
        params.append("theme", state.theme);
        params.append("interactive_checklist", state.interactive_checklist ? "1" : "0");
        params.append("fillable_notes", state.fillable_notes ? "1" : "0");
        params.append("clickable_links", state.clickable_links ? "1" : "0");
        if (state.sections && state.sections.length > 0) {
            params.append("sections", state.sections.join(","));
        }
        for (const [k, v] of Object.entries(extraParams)) {
            params.append(k, v);
        }
        return params.toString();
    }

    function getEndpoint(extraParams = {}) {
        const qs = buildQueryString(extraParams);
        return `${downloadEndpoint}?${qs}`;
    }

    function updatePreviewBadges() {
        const themeBadge = document.getElementById("sparkPdfThemeBadge");
        if (themeBadge) {
            const names = { navy: "Navy Theme", emerald: "Emerald Theme", sunset: "Sunset Gold" };
            themeBadge.innerText = names[state.theme] || "Navy Theme";
        }

        const interactivityBadge = document.getElementById("sparkPdfInteractivityBadge");
        if (interactivityBadge) {
            const activeFeatures = [];
            if (state.interactive_checklist) activeFeatures.push("Checkboxes");
            if (state.fillable_notes) activeFeatures.push("Notes Box");
            if (state.clickable_links) activeFeatures.push("Links");
            interactivityBadge.innerText = activeFeatures.length > 0 ? `Active (${activeFeatures.join(", ")})` : "Standard PDF";
        }

        const sectionCountBadge = document.getElementById("sparkPdfSectionCount");
        if (sectionCountBadge) {
            sectionCountBadge.innerText = `${state.sections.length} Sections Selected`;
        }
    }

    return {
        open: function (studentId = null, counselorUrl = null) {
            initModalHTML();
            if (counselorUrl) {
                downloadEndpoint = counselorUrl;
            } else if (studentId) {
                downloadEndpoint = `/counselor/student/${studentId}/record/download`;
            } else {
                downloadEndpoint = "/student/record/download";
            }
            currentStudentId = studentId;

            updatePreviewBadges();

            const fill = document.getElementById("sparkPdfProgressFill");
            const text = document.getElementById("sparkPdfProgressStep");
            const percent = document.getElementById("sparkPdfProgressPercent");
            if (fill) fill.style.width = "0%";
            if (text) text.innerText = "Ready to compile";
            if (percent) percent.innerText = "0%";

            document.getElementById("sparkPdfModalBackdrop").classList.add("active");
        },

        close: function () {
            const backdrop = document.getElementById("sparkPdfModalBackdrop");
            if (backdrop) backdrop.classList.remove("active");
        },

        selectTheme: function (themeName) {
            state.theme = themeName;
            document.querySelectorAll(".spark-pdf-theme-card").forEach(card => {
                card.classList.toggle("selected", card.dataset.theme === themeName);
            });
            updatePreviewBadges();
        },

        toggleFeature: function (featureName) {
            state[featureName] = !state[featureName];
            const toggleElemMap = {
                interactive_checklist: "toggleChecklist",
                fillable_notes: "toggleNotes",
                clickable_links: "toggleLinks"
            };
            const elem = document.getElementById(toggleElemMap[featureName]);
            if (elem) {
                elem.classList.toggle("active", state[featureName]);
            }
            updatePreviewBadges();
        },

        updateSections: function () {
            const checkboxes = document.querySelectorAll(".spark-pdf-sections-grid input[type='checkbox']");
            state.sections = [];
            checkboxes.forEach(cb => {
                const chip = cb.closest(".spark-pdf-chip");
                if (cb.checked) {
                    state.sections.push(cb.value);
                    if (chip) chip.classList.add("checked");
                } else {
                    if (chip) chip.classList.remove("checked");
                }
            });
            updatePreviewBadges();
        },

        startDownload: function () {
            const fill = document.getElementById("sparkPdfProgressFill");
            const text = document.getElementById("sparkPdfProgressStep");
            const percent = document.getElementById("sparkPdfProgressPercent");
            const btn = document.getElementById("sparkPdfDownloadBtn");

            btn.disabled = true;
            btn.innerHTML = `⌛ Compiling PDF...`;

            const steps = [
                { p: 20, label: "Fetching student database metrics..." },
                { p: 55, label: "Generating vector layout & AcroForms..." },
                { p: 85, label: "Embedding links, bookmarks & headers..." },
                { p: 100, label: "PDF Ready! Downloading file..." }
            ];

            let idx = 0;
            const interval = setInterval(() => {
                if (idx < steps.length) {
                    fill.style.width = steps[idx].p + "%";
                    text.innerText = steps[idx].label;
                    percent.innerText = steps[idx].p + "%";
                    idx++;
                } else {
                    clearInterval(interval);
                    // Trigger download
                    const targetUrl = getEndpoint();
                    window.location.href = targetUrl;

                    setTimeout(() => {
                        btn.disabled = false;
                        btn.innerHTML = `⚡ Download Interactive PDF`;
                        text.innerText = "Download complete!";
                        SparkPDFModal.close();
                    }, 1200);
                }
            }, 300);
        },

        preview: function () {
            const url = getEndpoint({ preview: "1" });
            const iframe = document.getElementById("sparkPdfViewerIframe");
            if (iframe) {
                iframe.src = url;
            }
            document.getElementById("sparkPdfViewerBackdrop").classList.add("active");
        },

        closeViewer: function () {
            const backdrop = document.getElementById("sparkPdfViewerBackdrop");
            if (backdrop) backdrop.classList.remove("active");
            const iframe = document.getElementById("sparkPdfViewerIframe");
            if (iframe) iframe.src = "about:blank";
        }
    };
})();

// Auto-wire existing download buttons across pages on DOM content loaded
document.addEventListener("DOMContentLoaded", function () {
    // Intercept .report-button or download report calls
    document.querySelectorAll(".report-button, [data-spark-pdf]").forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const studentId = this.dataset.studentId || null;
            const counselorUrl = this.dataset.counselorUrl || null;
            SparkPDFModal.open(studentId, counselorUrl);
        });
    });
});
