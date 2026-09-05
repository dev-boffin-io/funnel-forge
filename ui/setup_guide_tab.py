"""
Setup Guide tab.

A color-highlighted, in-app walkthrough of the Tailscale website/Admin
Console setup (installing Tailscale, enabling MagicDNS + HTTPS certs, and
granting Funnel access via ACLs) so the whole one-time setup is visible
without leaving the app. Headings, code/JSON snippets, and warnings are
each colored differently so the important bits stand out at a glance.
"""

from PyQt6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

GUIDE_HTML = """
<style>
body { color: #e6e6e6; font-size: 14px; line-height: 1.5; }
h1 { color: #58a6ff; font-size: 20px; }
h2 { color: #58a6ff; font-size: 16px; margin-top: 22px; }
.step-num {
    display: inline-block; background-color: #2563EB; color: white;
    border-radius: 10px; padding: 1px 9px; font-weight: bold; margin-right: 6px;
}
.code {
    background-color: #1e1e2e; color: #7ee787; font-family: monospace;
    padding: 8px 10px; display: block; white-space: pre; margin: 8px 0;
    border-radius: 4px;
}
.json-key { color: #79c0ff; }
.json-str { color: #a5d6ff; }
.warn {
    background-color: #3a2f14; border-left: 4px solid #d97706; color: #fcd34d;
    padding: 8px 10px; margin: 10px 0; border-radius: 4px;
}
.note {
    background-color: #14313a; border-left: 4px solid #0891B2; color: #93e2f0;
    padding: 8px 10px; margin: 10px 0; border-radius: 4px;
}
a { color: #58a6ff; }
</style>

<h1>Tailscale Website Setup Guide</h1>
<p>Everything you need to configure once on the Tailscale side before the
Funnel tab will work.</p>

<h2><span class="step-num">1</span>Install Tailscale</h2>
<p>If Tailscale isn't installed in your Linux/PRoot environment yet, run:</p>
<span class="code">curl -fsSL https://tailscale.com/install.sh | sh</span>
<p>Or use the <b>Install Tailscale</b> button on the Tailscale tab.</p>

<h2><span class="step-num">2</span>Log in to the Admin Console</h2>
<p>Go to the <a href="https://login.tailscale.com/admin">Tailscale Admin
Console</a> and log in with your Google/GitHub account.</p>

<h2><span class="step-num">3</span>Enable DNS &amp; HTTPS</h2>
<ul>
<li>Open the <b>DNS</b> tab.</li>
<li>Enable <b>MagicDNS</b>.</li>
<li>Scroll down and enable <b>HTTPS Certificates</b> - required for Funnel.</li>
<li>Optionally click <b>Rename tailnet</b> for a simpler domain name
(e.g. <i>sumit-net.ts.net</i>).</li>
</ul>

<h2><span class="step-num">4</span>Grant Funnel permission (ACLs)</h2>
<p>Open the <b>Access Controls</b> tab - you'll see a JSON editor.</p>
<ol>
<li>Scroll to the very bottom. You'll see a closing brace <b>}</b> - the
end of the whole file.</li>
<li>Click right before that final <b>}</b> (end of the line above it).</li>
<li>Press <b>Enter</b> for a new blank line.</li>
<li>Paste this exactly:</li>
</ol>
<span class="code">"<span class="json-key">nodeAttrs</span>": [
    {
        "<span class="json-key">target</span>": [<span class="json-str">"autogroup:member"</span>],
        "<span class="json-key">attr</span>":   [<span class="json-str">"funnel"</span>]
    }
],</span>
<p>Click <b>Save</b> below.</p>

<div class="warn">
⚠️ JSON needs a comma after every item except the very last one. If Save
errors with "trailing comma" or "unexpected token", check that the line
just above your pasted block ends with a comma, and that the very last
line in the file has no extra trailing comma.
</div>

<h2><span class="step-num">5</span>Start your local server</h2>
<p>Your web server needs to be running before you funnel it, e.g. Flask
on port 5000:</p>
<span class="code">python app.py</span>

<h2><span class="step-num">6</span>Disable key expiry</h2>
<p>By default, a device's Tailscale key expires after a while (180 days),
which would silently disconnect the Funnel. For a device that runs the
Funnel long-term, turn that off:</p>
<ol>
<li>Open the Tailscale admin console: <b>Machines</b>.</li>
<li>For the device running the Funnel, open the three-dot menu on the
right.</li>
<li>Select <b>Disable key expiry</b>.</li>
</ol>

<div class="note">
✅ Once steps 1-6 are done, head to the <b>Funnel</b> tab, set your
Hostname/Port, and press <b>Start Funnel</b>.
</div>
"""


class SetupGuideTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(GUIDE_HTML)
        layout.addWidget(browser)
