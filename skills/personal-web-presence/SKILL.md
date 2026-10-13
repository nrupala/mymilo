---
name: personal-web-presence
description: Run a personal brand web estate - canonical identity hub, spoke redirects, structured data, consistent bio.
version: 1
triggers: personal brand, personal website, bio, name search, online presence
category: Everyday life
blurb: Run a personal web estate — one canonical hub, consistent facts and spokes that point to it.
archetype: knowledge
example: Clean up my online presence so my name shows one consistent story.
---

# Personal Web Presence

The internet's default answer to "who is this person?" is noise. A personal estate should answer with one canonical, verifiable hub — and every spoke domain pointing at it with consistent facts.

## When to use
- Building or operating personal/brand domains (primary hub + variant spokes).
- Cleaning up name search results or inconsistent bios across the web.
- Publishing credentials, projects, or "what I'm building" statements.

## Method
1. **Hub & spokes**: pick one primary domain as the identity hub; variant domains 301 to it (or to purpose pages); consistent `<title>`/description across spokes. Keep the redirect map in version control.
2. **Identity facts**: one canonical bio — name spelling, credentials (e.g. P.Eng.), role line, location granularity — reused everywhere byte-for-byte; JSON-LD `Person` with `sameAs` to profiles; OpenGraph cards per page.
3. **Content with standards**: projects built / writing / speaking — each claim verifiable, dated, and linked; no borrowed prestige, no inflated titles.
4. **Name SEO**: own the first page for your name; disambiguate against similar names; link profiles reciprocally; ensure `rel=me` where supported.
5. **Cadence**: quarterly refresh of bio/projects; published archive of prior versions (change is normal; inconsistency is the failure).
6. **Contact & email**: stable contact path, alias strategy, forms over raw email, spam controls.
7. **Measurement**: periodic name-search check, referrer review; ignore vanity metrics; watch for impersonation and typosquats.

## Quality gates
- [ ] One canonical hub; all spoke redirects tested.
- [ ] JSON-LD validates; OG cards render on major platforms.
- [ ] Bio consistent across hub, profiles, and signatures; claims verifiable.
- [ ] Contact path works and is spam-resistant.
- [ ] Prior versions archived publicly.

## Red lines
- No unverifiable claims — especially credentials, clients, or affiliations.
- No impersonation-confusable profiles left unfixed; family privacy boundaries respected.
- Never let a brand domain lapse (see domain-portfolio-ops).

## Related
`seo` · `domain-portfolio-ops` · `html-craft` · `technical-writing` · `audience-contracts`.
