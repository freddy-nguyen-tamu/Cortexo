# Snowflake policy

"Snowflake support is intentionally disabled in Cortexo's permanent all-free deployment. Cortexo includes an optional portability adapter and Snowflake SQL benchmark fixtures, but Snowflake is not required because its official free access is a time-limited trial rather than a permanent free tier."

Cortexo's permanent public deployment therefore depends only on:

- MongoDB Atlas Free (primary operational store)
- optional Neon PostgreSQL Free (normalized evaluation analytics)
- optional Redis-compatible free cache
- Cloudflare Pages + Render free web tiers

Anything that is trial-only (Snowflake, and to some degree enterprise SQL
Server/Oracle/Db2 beyond their local fixtures) is represented as a research
fixture/adapter, never as a deployment dependency.