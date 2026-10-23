# BFF portfolio connection proof

An isolated fictional experiment. This is not the student portfolio product and contains no student information.

`state.json` is the bounded public site state. `fixture.py` validates requests and builds static pages with escaped text, safe slugs, a background color and a candidate identity. GitHub Actions tests the source, builds the pages and deploys to GitHub Pages.

The baseline can be deployed by a local operator. That alone does not establish an Eduba connection. A successful connected test requires actual Eduba-originated changes, GitHub commits, successful deployments and matching live content. Repository authorization and student isolation are separate requirements.

No credential belongs in the repository, site state or chat. The request IDs prevent accidental duplicates; they are not authentication. This experiment is not a template or security recommendation for a community rollout.
