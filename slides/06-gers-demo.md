---
class: dark
background: "#0f172a"
---
## GERS: Global Entity Reference System

Every Overture feature has a stable ID. Look it up anywhere.

<div data-terminal-player="assets/gers-demo.json"
     data-height="380"
     data-final-hold="10000"
     data-loop="true">
</div>

<noscript>
  <img src="assets/gers-demo.gif" style="width:100%" alt="Overture Maps GERS lookup demo">
</noscript>

Note:
GERS IDs are stable across releases. Look up the registry once to get the exact
parquet file path and bounding box, then fetch only that file — no full-dataset scan.
This slide uses the dark theme — class: dark + background: "#0f172a" — which suits terminal output.
