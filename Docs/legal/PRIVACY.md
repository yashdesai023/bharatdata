<div align="center">
  <img src="../../docs/assets/logo_full.png" alt="BharatData" height="72" />
  <h1>Privacy Policy</h1>
  <em>How BharatData handles data about its users.</em>
</div>

---

> **Summary:** BharatData does not collect personal information, does not require account registration, and does not sell or share any user data with third parties. We use minimal, anonymous analytics to understand how the platform is being used.

---

## 1. Our Core Privacy Principle

**BharatData is designed to be a tool that exposes government data — not a tool that collects your data.** We have made deliberate architectural choices to minimize data collection at every level:

- The API is publicly accessible **without registration or login**
- We do not store the queries you make
- We do not store your IP address beyond the current request window (used only for rate limiting)
- We do not build user profiles

---

## 2. Information We Do NOT Collect

We do not collect, store, or process:

- Your name, email address, or any personally identifiable information
- Your location beyond the country level (inferred from Cloudflare headers, not stored)
- The content of your queries (not logged to persistent storage)
- Browser fingerprints, cookies, or tracking pixels
- Payment information (the service is free)

---

## 3. Information We DO Collect

### 3.1 Rate Limiting Data (Transient)

To enforce our fair-use rate limits (10 req/min, 200 req/day), your IP address is stored **in-memory** in the Cloudflare Worker for the duration of the current request window. This data:

- Is never written to disk or a database
- Is never shared with any third party
- Is automatically purged when the rate limit window expires (maximum 24 hours)
- Cannot be tied to you personally without correlation with your ISP's records

### 3.2 Cloudflare Infrastructure Logs (Transient)

BharatData's API runs on Cloudflare Workers. Cloudflare retains standard request logs (IP address, request path, response code, timestamp) for **up to 72 hours** for operational and security purposes, after which they are automatically deleted. BharatData has no control over Cloudflare's internal logging practices. For details, see [Cloudflare's Privacy Policy](https://www.cloudflare.com/privacypolicy/).

### 3.3 Aggregate Usage Analytics (Anonymized)

We may collect **aggregate, anonymized statistics** such as:

- Total API requests per day (a single number — not broken down by IP)
- Most frequently queried datasets (e.g., "NCRB Crime Statistics is the most-used dataset")
- Error rates and API latency percentiles

These statistics cannot be used to identify individual users.

---

## 4. Data Stored by the Playground

The interactive playground (`bharatdata.org`) is built on Next.js and may use:

- **`localStorage`** (browser): To store your recent query history *on your device only*. This data never leaves your browser and is cleared when you clear your browser storage. BharatData does not have access to this data.
- **Session state**: To preserve your query results during your browser session. This is lost when you close the tab.

No cookies are set by BharatData for tracking, advertising, or analytics purposes.

---

## 5. Third-Party Services

BharatData integrates with the following third-party services:

| Service | Purpose | Privacy Policy |
| :--- | :--- | :--- |
| **Cloudflare Workers** | API hosting and edge compute | [cf.com/privacy](https://www.cloudflare.com/privacypolicy/) |
| **Supabase** | Primary data storage (government datasets only) | [supabase.com/privacy](https://supabase.com/privacy) |
| **Vercel** | Playground hosting | [vercel.com/legal/privacy-policy](https://vercel.com/legal/privacy-policy) |
| **Google (Gemini AI)** | AI narrative generation | [policies.google.com/privacy](https://policies.google.com/privacy) |

> **Note on AI Processing:** When you use the AI Query feature, your query text is sent to Google's Gemini API for processing. BharatData does not log these queries. However, Google's standard API data retention policies apply. We recommend avoiding queries that contain personally identifiable information.

BharatData does not integrate with advertising networks, data brokers, or social media tracking platforms.

---

## 6. Data Security

We take a security-first approach to protect our infrastructure:

- All API traffic is encrypted via TLS 1.2+
- Supabase database access uses Row Level Security (RLS) policies
- API secrets and credentials are stored as environment variables, never in source code
- We follow responsible disclosure for security vulnerabilities (see [../../SECURITY.md](../../SECURITY.md))

Since we do not collect personal data, the risk of a data breach exposing your personal information is structurally minimized.

---

## 7. Data Requests from Authorities

In the event that a legal authority requests data related to a BharatData user:

- We would comply with valid legal orders under Indian law
- We would notify affected users if legally permitted to do so
- **In practice, we have very little data to provide.** We do not maintain user accounts or persistent query logs. All we could potentially disclose is transient rate-limit data (IP address + request count within the past 24 hours), which Cloudflare holds.

---

## 8. Children's Privacy

BharatData is not directed at children under the age of 13. We do not knowingly collect any information from users under 13. If you believe a minor has submitted information through our platform, please contact us and we will take appropriate action.

---

## 9. Changes to This Policy

We will update this Privacy Policy when our data practices change in a meaningful way. Changes will be committed to this file with a clear description of what changed and why. The "Last Updated" date at the bottom of this document will always reflect the most recent revision.

Continued use of the platform after a policy update constitutes acceptance of the revised policy.

---

## 10. Contact

If you have any questions about this Privacy Policy or how your data is handled, please contact:

**BharatData Team**  
`privacy@bharatdata.org`

---

<div align="center">
  <sub>Generated by the BharatData Team &nbsp;|&nbsp; Not affiliated with any government body &nbsp;|&nbsp; Last updated: April 1, 2026</sub>
</div>
