<div align="center">
  <img src="../../Docs/assets/logo_full.png" alt="BharatData" height="72" />
  <h1>Terms of Use</h1>
  <em>Plain-language usage rights for the BharatData platform and API.</em>
</div>

---

> **Summary:** BharatData is an open-access platform. You are free to use the data for personal, educational, journalistic, and commercial research purposes. You may not use our infrastructure to build competing scraping services, redistribute data falsely attributed to yourself, or deliberately overload our systems.

---

## 1. Acceptance of Terms

By accessing the BharatData API (`api.bharatdata.dev`), web playground (`bharatdata.dev`), TypeScript SDK (`@bharatdata/typescript-sdk`), or Python SDK (`bharatdata`), you agree to these Terms of Use. If you are accessing on behalf of an organization, you represent that you have authority to bind that organization.

These Terms were last updated on **April 1, 2026**.

---

## 2. Who We Are

BharatData is an independent, open-source initiative. We are not a company, government body, or commercial data broker. Our mission is to lower the barrier to accessing verified Indian public statistics.

We are **not affiliated with** the Government of India, the National Crime Records Bureau (NCRB), the Reserve Bank of India (RBI), the Census of India, or any other government entity whose data we redistribute.

---

## 3. What the Platform Provides

BharatData provides:

- **Normalized access** to publicly available government statistics
- **An API layer** for programmatic data retrieval
- **An AI analysis layer** that summarizes and interprets data
- **Developer SDKs** for integration into third-party applications

We do **not** provide:
- Real-time government data (all data reflects the most recent published reports)
- Personal data, sensitive citizen information, or individually identifiable records
- Legal, medical, financial, or investment advice based on the data we serve

---

## 4. Permitted Uses

You **may** use BharatData for:

| Use Case | Permitted |
| :--- | :--- |
| Personal research and education | ✅ Yes |
| Journalistic investigation and reporting | ✅ Yes |
| Academic research and publication | ✅ Yes |
| Building open-source tools that extend BharatData | ✅ Yes |
| Commercial products that consume BharatData as a data source | ✅ Yes |
| Government policy analysis and planning | ✅ Yes |
| AI/ML model training using the normalized datasets | ✅ Yes |

---

## 5. Prohibited Uses

You **may not** use BharatData to:

| Prohibited Activity | Reason |
| :--- | :--- |
| Build a competing "wrapper" API that re-sells BharatData data without attribution | Violates attribution requirements |
| Claim you collected, generated, or own the underlying government data | Data belongs to GOI |
| Deliberately exceed rate limits through proxies or distributed systems | Infrastructure abuse |
| Serve data in ways that misrepresent, distort, or falsify the original government statistics | Data integrity violation |
| Use AI-generated narratives as news articles without human editorial review | Responsible AI use |
| Access data for the purpose of monitoring, targeting, or profiling individual citizens | Privacy violation |

---

## 6. Rate Limits and Fair Use

To ensure platform availability for all users, we apply the following limits per IP address:

- **10 requests per minute**
- **200 requests per day**

These limits are enforced automatically. Repeatedly circumventing them may result in your IP being blocked indefinitely.

If you are building a high-volume application (e.g., a research pipeline processing millions of records), please contact us to discuss bulk access options: `data@bharatdata.dev`.

---

## 7. Data Accuracy and Disclaimer

BharatData normalizes and serves government data without modification to the underlying statistics. However:

- **We are not responsible for errors in original government publications.** If a government report contains an incorrect figure, our data will reflect that figure.
- **Data may be delayed.** We update datasets following the publication of new government reports, which may take days to weeks after a report becomes publicly available.
- **AI-generated narratives are summaries, not legal advice.** The AI Analysis feature provides interpretive summaries that may contain errors. Always verify critical findings against the original source.

BharatData data should **not** be used as the sole basis for legal proceedings, investment decisions, or public health interventions without independent verification.

---

## 8. Attribution Requirement

When publishing research, journalism, or products that use BharatData, you must attribute both:

1. **The original government source**: e.g., _"Source: National Crime Records Bureau, Ministry of Home Affairs, Government of India"_
2. **The BharatData platform**: e.g., _"Data accessed via BharatData (bharatdata.dev)"_

See [ATTRIBUTION.md](ATTRIBUTION.md) for official citation formats for each dataset.

---

## 9. API Keys and Future Authentication

The BharatData API is currently publicly accessible without authentication. We reserve the right to introduce API key authentication in the future to:

- Enable higher rate limits for registered developers
- Provide usage analytics to dataset contributors
- Enforce more granular terms for commercial API access

We will provide at least 30 days notice before making any breaking changes to the authentication model.

---

## 10. Intellectual Property

- The BharatData **software code** is licensed under the MIT License. See [../../LICENSE](../../LICENSE).
- The BharatData **brand and logo** are trademarks of the BharatData Team and may not be used without explicit written permission.
- The underlying **government data** belongs to the respective government bodies and is subject to their open data policies.
- **AI-generated narratives** produced by the platform are not independently copyrightable and are provided as-is.

---

## 11. Changes to These Terms

We may update these Terms to reflect platform changes. We will notify users via:

- A commit to this file with a clear changelog entry
- An announcement in the GitHub Discussions section

Continued use of the platform after changes constitutes acceptance of the revised Terms.

---

## 12. Contact

For any questions about these Terms, contact: `legal@bharatdata.dev`

---

<div align="center">
  <sub>Generated by the BharatData Team &nbsp;|&nbsp; Not affiliated with any government body &nbsp;|&nbsp; Last updated: April 1, 2026</sub>
</div>
