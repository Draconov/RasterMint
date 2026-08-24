# Feature Research and Integration Policy

RasterMint can learn from public tools, papers, documentation, hardware references, and creative workflows without copying third-party implementation code or UI assets.

This document defines the preferred research process for new algorithms, effects, presets, and workflow ideas.

## Research goals

External research should answer four questions:

1. **What user problem does the feature solve?**
2. **What behavior is technically essential?**
3. **Can it fit RasterMint's shared processing pipeline?**
4. **Can it be implemented independently and distributed under RasterMint's licensing model?**

A feature should not be added solely because another application has it.

## Preferred sources

Use primary or technically reliable sources where possible:

- academic papers and algorithm descriptions;
- official hardware/programming documentation;
- official project documentation/API references;
- format specifications;
- permissively documented mathematical descriptions;
- public examples used only to understand expected behavior.

Community posts and videos can be useful for discovery, but important implementation claims should be checked against stronger sources.

## Independent implementation

Research the **idea and behavior**, then implement it using RasterMint's own architecture and code style.

Do not copy:

- third-party source code without compatible rights;
- proprietary presets/data dumps;
- application artwork/icons;
- UI layouts pixel-for-pixel;
- copyrighted documentation text.

If a feature requires third-party code or data, verify its license and document the dependency/attribution requirements before integration.

## Evaluation checklist

Before implementing a researched feature:

- [ ] define the desired behavior in RasterMint terms;
- [ ] identify whether it belongs in core, data, QML, or packaging;
- [ ] verify licensing/attribution constraints;
- [ ] check whether an existing RasterMint feature already covers the same use case;
- [ ] estimate preview/export performance impact;
- [ ] decide how it serializes in settings/presets;
- [ ] decide whether it applies to stills, animation, video, and batch;
- [ ] define at least one focused behavioral test;
- [ ] document approximations where exact behavior is not feasible.

## Hardware research

Historical graphics hardware often has context-dependent behavior. Avoid presenting one palette, resolution, or display conversion as universally correct when software modes, region standards, analog displays, or per-game choices differ.

Use [`HARDWARE_PROFILES.md`](HARDWARE_PROFILES.md) to distinguish creative Visual behavior from supported Strict image-space constraints.

## Online services

Prefer documented APIs over scraping. Remote integrations should be isolated from processing logic so the application remains useful offline when a service is unavailable.

Lospec integration follows this rule by using the documented per-palette JSON endpoint and converting the response into RasterMint's normal palette model.

## Recording research

Long-lived implementation facts belong in developer documentation or code comments near the relevant contract. Temporary links/experiments should not accumulate in production documentation after a feature is understood and implemented.
