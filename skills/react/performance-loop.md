# Performance loop

Measure a page, fix the biggest measured bottleneck, measure again. Repeat until the page is good. The `performance` skill from web-quality-skills is the reference for how to measure and what to fix: read its SKILL.md and its references/MEASUREMENT.md before the first round.

## Before the first round

- Measure a production build served locally (`npm run build` then `npm run start`, or `vite build` then `vite preview`). Never measure the dev server: it is unminified and is not what users get.
- Pick the routes to measure: the landing page plus the one or two pages users spend the most time on. Measure each in the state a user sees, logged in or not.
- Use mobile conditions: a phone viewport, 4x CPU slowdown and Slow 4G. Add desktop when the product is mainly used on desktop.
- Keep the same conditions for every round. Write them down with the first result.

## Each round

1. Measure. Record a reload trace (with Chrome DevTools MCP: `performance_start_trace`). For a number you will decide on, take the median of three runs. If DevTools MCP is not available, use the fallbacks in the `performance` skill's references/MEASUREMENT.md, starting with the Lighthouse CLI.
2. Score. Compare against the targets below and the `performance` skill's budget table. If everything is good, stop.
3. Pick one cause. Take the worst metric and open its insight (`performance_analyze_insight`, for example `LCPBreakdown`, `RenderBlocking` or `ThirdParties`). Pick the single cause the trace points at. Do not fix something the trace does not show.
4. Fix it. The `performance` skill covers loading, images, fonts and caching. For React causes, use the `vercel-react-best-practices` skill:
   - large JavaScript or long parse: dynamic imports, barrel imports, deferred third-party scripts
   - slow LCP behind data: request waterfalls, Suspense boundaries, parallel fetching
   - long tasks after load: re-renders, expensive renders, hydration work
5. Rebuild and measure again under the same conditions. Keep the fix only if the metric improved by more than the run-to-run spread. Revert it otherwise.

## Targets

| Metric | Good | Notes |
|--------|------|-------|
| LCP | <= 2.5 s | Largest Contentful Paint |
| CLS | <= 0.1 | Cumulative Layout Shift |
| TBT | <= 200 ms | Total Blocking Time. A load trace cannot measure INP, so TBT stands in for it in the lab |
| INP | <= 200 ms | Interaction to Next Paint. Check it by tracing the page's main interactions (open a menu, send a message, filter a list) |

The budgets in the `performance` skill (JavaScript under 300 KB compressed, and so on) are starting guardrails. Keep a budget the project already has.

## When to stop

Stop when every target is good on every measured route. Also stop after 10 rounds, or after two rounds in a row that did not improve anything. When you stop before the targets are met, say which metric is still failing and what the trace says causes it.

## Report

Finish with the `performance` skill's evidence table: one row per metric and route, with the conditions, the first and the last value, and the source. Then list the fixes kept and the fixes reverted. Lab results are one machine's numbers. Real-user (field) data will not show the change until it has been deployed for a while.
